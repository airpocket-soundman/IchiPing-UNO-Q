"""Generate review SVGs from actual EasyEDA Gerber silkscreen output.

Run with gerbonara installed. These previews are not manufacturing releases.
"""
import base64
import json
import zipfile
from pathlib import Path
from gerbonara import GerberFile
from pcb_local_audit import OUT, ROOT, api

for name, uid, revision in [('uno', '484a25750631f0fe', 'B'), ('audio', '86c9249a00f4733c', 'D')]:
    tab = api(f'return await eda.dmt_EditorControl.openDocument({json.dumps(uid)});')
    api(f'return await eda.dmt_EditorControl.activateDocument({json.dumps(tab)});')
    assert api('return await eda.dmt_SelectControl.getCurrentDocumentInfo();')['uuid'] == uid
    encoded = api('const b=await eda.pcb_ManufactureData.getGerberFile();const a=new Uint8Array(await b.arrayBuffer());let s="";for(let i=0;i<a.length;i+=10000)s+=String.fromCharCode(...a.slice(i,i+10000));return btoa(s);')
    archive = OUT / f'{name}-REV-{revision}-silk-review.zip'
    archive.write_bytes(base64.b64decode(encoded))
    with zipfile.ZipFile(archive) as z:
        for side, filename in [('top','Gerber_TopSilkscreenLayer.GTO'), ('bottom','Gerber_BottomSilkscreenLayer.GBO')]:
            layer = GerberFile.from_string(z.read(filename).decode())
            svg = layer.to_svg(margin=1, fg='#f8d766', bg='#15372f')
            target = ROOT / 'board' / 'previews' / f'{name}-rev-{revision.lower()}-{side}-silk.svg'
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(str(svg), encoding='utf-8')
            print(target.name, len(layer.objects), flush=True)
