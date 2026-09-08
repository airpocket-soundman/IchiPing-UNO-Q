"""Label actual jumper functions without changing electrical connectivity."""
import json
from pcb_local_audit import api, OUT

uid = '86c9249a00f4733c'
tab = api(f'return await eda.dmt_EditorControl.openDocument({json.dumps(uid)});')
api(f'return await eda.dmt_EditorControl.activateDocument({json.dumps(tab)});')
assert api('return await eda.dmt_SelectControl.getCurrentDocumentInfo();')['uuid'] == uid
old = api('return await eda.pcb_PrimitiveString.getAll();')
changes = {
    '7e3dd002f7e2cb26': dict(text='OPEN=9dB', x=310, y=-445, rotation=90),
    'b114019cd186e4bb': dict(text='OPEN=ON', x=310, y=-795, rotation=90),
    'cad1c65ddf0583a7': dict(text='SHORT=L', x=470, y=-1950, rotation=0),
}
for s in old:
    p = changes.get(s['primitiveId'])
    if p:
        p.update(fontSize=45, lineWidth=7)
        assert api(f'return await eda.pcb_PrimitiveString.modify({json.dumps(s["primitiveId"])},{json.dumps(p)});')
for text, x, y, rotation in [('SHORT=12dB',480,-445,90), ('SHORT=MUTE',610,-795,90), ('OPEN=UNDEF',470,-2025,0)]:
    if not any(s['text'] == text for s in old):
        assert api(f'const EPCB_LayerId={{TOP_SILKSCREEN:3}};const EPCB_PrimitiveStringAlignMode={{CENTER:5}};return await eda.pcb_PrimitiveString.create(EPCB_LayerId.TOP_SILKSCREEN,{x},{y},{json.dumps(text)},"default",45,7,EPCB_PrimitiveStringAlignMode.CENTER,{rotation},false,0,false,false);')
assert api('return await eda.pcb_Document.save();')
print('Jumper function labels saved; electrical design unchanged.')
