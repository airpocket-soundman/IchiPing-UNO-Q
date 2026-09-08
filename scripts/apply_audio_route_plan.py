"""Apply an already-reviewed route plan only to the known audio PCB."""
import json
from pcb_local_audit import api, OUT

DOC = '86c9249a00f4733c'
guard = 'if((await eda.dmt_SelectControl.getCurrentDocumentInfo()).uuid!=='+json.dumps(DOC)+')throw Error("Wrong document");'
plan = json.loads((OUT/'audio-route-plan.json').read_text(encoding='utf-8'))
original = json.loads((OUT/'audio-route-input.json').read_text(encoding='utf-8'))
old_vias = {v['primitiveId'] for v in original['vias']}
snapshot = api(guard+'return {lines:await eda.pcb_PrimitiveLine.getAll(),vias:await eda.pcb_PrimitiveVia.getAll()};')
(OUT/'route-before-apply.json').write_text(json.dumps(snapshot),encoding='utf-8')
lines = [x['primitiveId'] for x in snapshot['lines'] if x['layer'] in (1,2)]
vias = [x['primitiveId'] for x in snapshot['vias'] if x['primitiveId'] not in old_vias]
assert len(lines) > 0 and len(vias) <= 10
print(api(guard+'return await eda.pcb_PrimitiveLine.delete('+json.dumps(lines)+');'))
if vias:
    print(api(guard+'return await eda.pcb_PrimitiveVia.delete('+json.dumps(vias)+');'))
for i in range(0,len(plan['lines']),80):
    batch=plan['lines'][i:i+80]
    code=guard+'const EPCB_LayerId={TOP:1,BOTTOM:2};const batch='+json.dumps(batch)+';let n=0;for(const p of batch){const layer=p.layer===1?EPCB_LayerId.TOP:EPCB_LayerId.BOTTOM;const r=await eda.pcb_PrimitiveLine.create(p.net,layer,...p.a,...p.b,p.width,false);if(!r)throw Error("Line failed");n++;}return n;'
    print(i,api(code),flush=True)
for v in plan['vias']:
    print(api(guard+'return !!(await eda.pcb_PrimitiveVia.create('+json.dumps(v['net'])+f",{v['x']},{v['y']},12,24,undefined,null,"+'{topSolderMask:-12,bottomSolderMask:-12},false));'))
print(api(guard+'for(const p of await eda.pcb_PrimitivePour.getAll())await p.rebuildCopperRegion();return await eda.pcb_Document.save();'))
r=api(guard+'return await eda.pcb_Drc.check(true,false,true);')
(OUT/'audio-final-route-drc.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print(r)
