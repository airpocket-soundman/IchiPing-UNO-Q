"""Read back and correct layer assignment against reviewed footprint snapshots."""
import json
from pcb_local_audit import api, OUT

project = 'e558d47ba7a68f9cb860c2af6ff59bb0a761038db98c6646d137672b17869014'
for path in sorted(OUT.glob('silk-fp-*.json')):
    uid = path.stem.removeprefix('silk-fp-')
    before = json.loads(path.read_text(encoding='utf-8'))
    tab = api(f'return await eda.lib_Footprint.openInEditor({json.dumps(uid)},{json.dumps(project)});')
    api(f'return await eda.dmt_EditorControl.activateDocument({json.dumps(tab)});')
    assert api('return await eda.dmt_SelectControl.getCurrentDocumentInfo();')['uuid'] == uid
    expected = {p['primitiveId']: {'layer': 3 if p['layer'] == 71 else p['layer'], 'width': max(p['lineWidth'],6) if p['layer']==71 else p['lineWidth']} for p in before['polys']}
    js = 'const expected='+json.dumps(expected)+';const EPCB_LayerId={TOP_ASSEMBLY:9};let changed=[];for(const p of await eda.pcb_PrimitivePolyline.getAll()){const e=expected[p.primitiveId]||{layer:EPCB_LayerId.TOP_ASSEMBLY,width:p.lineWidth};if(p.layer!==e.layer||Math.abs(p.lineWidth-e.width)>0.0001){const a=p.toAsync();a.setState_Layer(e.layer);a.setState_LineWidth(e.width);await a.done();changed.push(p.primitiveId);}}if(!await eda.pcb_Document.save())throw new Error("Save failed");return changed;'
    print(uid, api(js), flush=True)
