"""Create an A4 comparison PDF from high-resolution live EasyEDA canvas tiles.

No circuit graphics are redrawn. The fixed-scale overlapping screenshots are
clipped into page coordinates, avoiding stale objects in EasyEDA's PDF exporter.
"""
import json
import sys
import time
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.cache/pcb-repair-20260908'

def capture(board):
    from pcb_local_audit import api
    from schematic_readability import activate
    doc=activate(board)
    tab=json.dumps(doc['tabId'])
    tiles=[]
    b=api(f'return await eda.dmt_EditorControl.zoomTo(585,412.5,200,{tab});')
    cols=math.ceil(1170/((b['right']-b['left'])*.85))
    rows=math.ceil(825/(2*(b['top']-412.5)*.85))
    cw,ch=1170/cols,825/rows
    for row in range(rows):
        for col in range(cols):
            cx,cy=cw*(col+.5),ch*(row+.5)
            bounds=api(f'return await eda.dmt_EditorControl.zoomTo({cx},{cy},200,{tab});')
            time.sleep(.15)
            raw=api(f'const b=await eda.dmt_EditorControl.getCurrentRenderedAreaImage({tab});return Array.from(new Uint8Array(await b.arrayBuffer()));')
            path=OUT/f'{board}-tile-{row}-{col}.png'
            path.write_bytes(bytes(raw))
            tiles.append(dict(path=str(path),left=bounds['left'],right=bounds['right'],
                top=bounds['top'],bottom=2*cy-bounds['top'],col=col,row=row,cw=cw,ch=ch))
        print(board,'captured row',row+1,flush=True)
    (OUT/f'{board}-tiles.json').write_text(json.dumps(tiles,indent=2),encoding='utf-8')
    api(f'return await eda.dmt_EditorControl.zoomToAllPrimitives({tab});')

def render(board):
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    tiles=json.loads((OUT/f'{board}-tiles.json').read_text(encoding='utf-8'))
    target=ROOT/'output/pdf'/f'{board}-schematic-after.pdf'
    c=canvas.Canvas(str(target),pagesize=(848.88,600.48))
    c.setTitle(f'{board.upper()} shield - revised schematic (live EasyEDA display)')
    c.setSubject('Live EasyEDA canvas capture; same A4 scale as before PDF. Grid is editor background.')
    scale=.72;pad=3.24
    for t in tiles:
        c.saveState()
        p=c.beginPath();p.rect(pad+t['col']*t['cw']*scale,pad+t['row']*t['ch']*scale,t['cw']*scale,t['ch']*scale)
        c.clipPath(p,stroke=0,fill=0)
        c.drawImage(ImageReader(t['path']),pad+t['left']*scale,pad+t['bottom']*scale,
                    width=(t['right']-t['left'])*scale,height=(t['top']-t['bottom'])*scale)
        c.restoreState()
    c.showPage();c.save()
    print(target)

if __name__=='__main__':
    (capture if sys.argv[2]=='capture' else render)(sys.argv[1])
