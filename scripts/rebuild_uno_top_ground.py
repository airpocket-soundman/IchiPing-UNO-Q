"""Rebuild the existing UNO top GND pour without changing routing."""
import json
from datetime import datetime
from pcb_local_audit import api, OUT

uid = '484a25750631f0fe'
assert api('return await eda.dmt_SelectControl.getCurrentDocumentInfo();')['uuid'] == uid
stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
source = api('return await eda.sys_FileManager.getDocumentSource();')
(OUT / (stamp+'-uno-before-top-ground.txt')).write_text(source,encoding='utf-8')
result = api('const p=(await eda.pcb_PrimitivePour.getAll()).find(p=>p.primitiveId==="7aa14781b271cc0e");if(!p||p.net!=="GND")throw new Error("Pour mismatch");const c=await p.rebuildCopperRegion();if(!c)throw new Error("No copper generated");return {pour:p,copper:c};')
(OUT / (stamp+'-uno-top-ground.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
print('Copper rebuilt', flush=True)
print('DRC',api('return await eda.pcb_Drc.check(true,true,true);'),flush=True)
print('Saved',api('return await eda.pcb_Document.save();'),flush=True)
api('return await eda.pcb_Document.zoomToBoardOutline();')
image = api('const b=await eda.dmt_EditorControl.getCurrentRenderedAreaImage();return Array.from(new Uint8Array(await b.arrayBuffer()));')
(OUT/'uno-top-ground-current.png').write_bytes(bytes(image))
