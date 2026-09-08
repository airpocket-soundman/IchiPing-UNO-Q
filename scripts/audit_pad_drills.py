"""Audit live component drill settings without changing the design."""
import json
import time
import zipfile
import re
from pcb_local_audit import api, OUT

BOARDS = {'uno': '484a25750631f0fe', 'audio': '86c9249a00f4733c'}

def snapshot(board):
    uid = BOARDS[board]
    tab = api('return await eda.dmt_EditorControl.openDocument('+json.dumps(uid)+');')
    api('return await eda.dmt_EditorControl.activateDocument('+json.dumps(tab)+');')
    time.sleep(.3)
    assert api('return await eda.dmt_SelectControl.getCurrentDocumentInfo();')['uuid'] == uid
    data = api('const out=[];for(const c of await eda.pcb_PrimitiveComponent.getAll()){out.push({component:c,pads:await eda.pcb_PrimitiveComponent.getAllPinsByPrimitiveId(c.primitiveId)});}return out;')
    path = OUT / (board+'-drill-audit-before.json')
    if not path.exists():
        path.write_text(json.dumps(data, indent=2), encoding='utf-8')
    for item in data:
        c = item['component']
        holes = sorted({str(p.get('hole')) for p in item['pads']})
        print(board, c['designator'], c.get('name'), len(item['pads']), holes, 'layers', sorted({p['layer'] for p in item['pads']}), 'plated', sorted({p['metallization'] for p in item['pads']}), flush=True)
    return data

def export_drills(board, data):
    result = api('const f=await eda.pcb_ManufactureData.getGerberFile('+json.dumps(board+'-drill-check')+');if(!f)throw new Error("No Gerber");return {name:f.name,bytes:Array.from(new Uint8Array(await f.arrayBuffer()))};')
    path = OUT / (board+'-drill-check.zip')
    path.write_bytes(bytes(result['bytes']))
    with zipfile.ZipFile(path) as z:
        hits = []
        for name in z.namelist():
            if name.upper().endswith('.DRL'):
                content = z.read(name).decode()
                if name != 'Drill_PTH_Through.DRL':
                    continue
                assert 'METRIC' in content
                tools = {m[1]: float(m[2]) for m in re.finditer(r'^T(\d+)C([\d.]+)', content, re.M)}
                tool = None
                for line in content.splitlines():
                    if re.fullmatch(r'T\d+', line):
                        tool = line[1:]
                    m = re.fullmatch(r'X(-?[\d.]+)Y(-?[\d.]+)', line)
                    if m:
                        hits.append((float(m[1]), float(m[2]), tools[tool]))
    verified, failures = [], []
    for item in data:
        for p in item['pads']:
            # This client returns component hole dimensions in source units
            # (0.01 inch), but pad coordinates in mil. Validate against DRL.
            expected = (p['x']*.0254, p['y']*.0254, p['hole'][1]*.254)
            # Component API positions are rounded; permit 2 micrometres on XY.
            matches = [h for h in hits if abs(expected[0]-h[0])<.002
                       and abs(expected[1]-h[1])<.002 and abs(expected[2]-h[2])<.0001]
            row = {'ref': item['component']['designator'], 'pin':p['padNumber'],
                   'x_mm':expected[0], 'y_mm':expected[1], 'drill_mm':round(expected[2],3),
                   'plated':p['metallization'], 'drill_matches':len(matches)}
            (verified if matches and p['metallization'] else failures).append(row)
    result = {'board':board,'verified':verified,'failures':failures,
              'drc':api('return await eda.pcb_Drc.check(true,false,true);')}
    (OUT/(board+'-drill-verification.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(board, 'verified',len(verified),'failures',len(failures),'DRC',result['drc'],flush=True)
    return result

if __name__ == '__main__':
    for board in BOARDS:
        data = snapshot(board)
        export_drills(board, data)
