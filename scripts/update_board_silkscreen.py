"""Restore local footprint silkscreen; retain assembly/courtyard and all copper.

Requires an active EasyEDA gateway and the reviewed pre-change snapshots.
"""
import json
import sys
from pcb_local_audit import OUT, api


def restore_footprints():
    fps = {}
    for board in ('uno', 'audio'):
        data = json.loads((OUT / f'{board}-silk-before.json').read_text(encoding='utf-8'))
        for component in data['components']:
            fp = component['footprint']
            fps[fp['uuid']] = fp
    for uid, fp in fps.items():
        tab = api(f'return await eda.lib_Footprint.openInEditor({json.dumps(uid)},{json.dumps(fp["libraryUuid"])});')
        api(f'return await eda.dmt_EditorControl.activateDocument({json.dumps(tab)});')
        doc = api('return await eda.dmt_SelectControl.getCurrentDocumentInfo();')
        assert doc['uuid'] == uid and doc['documentType'] == 4, doc
        result = api('const EPCB_LayerId={CUSTOM_1:71,TOP_SILKSCREEN:3}; const all=await eda.pcb_PrimitivePolyline.getAll(); let n=0; for(const p of all){if(p.layer===EPCB_LayerId.CUSTOM_1){const a=p.toAsync();a.setState_Layer(EPCB_LayerId.TOP_SILKSCREEN);a.setState_LineWidth(Math.max(p.lineWidth,6));await a.done();n++;}} if(!await eda.pcb_Document.save())throw new Error("Save failed");return n;')
        print(uid, result, flush=True)


def enlarge_text():
    for board, uid, rev in [('uno', '484a25750631f0fe', 'B'), ('audio', '86c9249a00f4733c', 'D')]:
        tab = api(f'return await eda.dmt_EditorControl.openDocument({json.dumps(uid)});')
        api(f'return await eda.dmt_EditorControl.activateDocument({json.dumps(tab)});')
        assert api('return await eda.dmt_SelectControl.getCurrentDocumentInfo();')['uuid'] == uid
        data = json.loads((OUT / f'{board}-silk-before.json').read_text(encoding='utf-8'))
        for s in data['strings']:
            if s['layer'] not in (3, 4):
                continue
            p = dict(fontSize=max(s['fontSize'], 50), lineWidth=7)
            if s['text'].startswith('REV '):
                p['text'] = f'REV {rev}  2026-09-08'
                p['fontSize'] = 60
                if board == 'audio':
                    p.update(x=675, y=-2045, rotation=0)
            if board == 'audio':
                changes = {
                    'b7fe60db6053f10b': dict(x=55,y=-350,fontSize=55),
                    '5765f5b45f8ca32f': dict(x=45,y=-1300,fontSize=45),
                    'f8588fa3db42551a': dict(text='SD GND VIN(5V)',fontSize=50),
                    '5bd6c0824a045121': dict(text='LRC BCLK DIN GAIN',fontSize=50),
                    '6fd0e331a086c2e6': dict(text='GND 1V8 SD CLK WS LR',fontSize=50),
                    '633a2718b91483e7': dict(text='1',x=132.2047,y=-25),
                    'afd55af1711963e9': dict(text='1',x=732.2047,y=-25),
                    'b114019cd186e4bb': dict(text='OPEN',x=415,y=-920),
                    '7e3dd002f7e2cb26': dict(x=390,y=-320,fontSize=45),
                    'cad1c65ddf0583a7': dict(x=390,y=-1560,fontSize=45),
                    '2fc65a559a44675f': dict(x=640,y=-350,rotation=90),
                }
                p.update(changes.get(s['primitiveId'], {}))
            assert api(f'return await eda.pcb_PrimitiveString.modify({json.dumps(s["primitiveId"])},{json.dumps(p)});')
        for a in data['attributes']:
            if a['valueVisible'] and a['layer'] in (3, 4):
                p = dict(fontSize=50, lineWidth=7)
                assert api(f'return await eda.pcb_PrimitiveAttribute.modify({json.dumps(a["primitiveId"])},{json.dumps(p)});')
        x, y = (6100, -2190) if board == 'uno' else (970, -2025)
        title = f'REV {rev}'
        existing = api('return await eda.pcb_PrimitiveString.getAll();')
        if not any(s['text'] == title and s['layer'] == 3 for s in existing):
            api(f'const EPCB_LayerId={{TOP_SILKSCREEN:3}};const EPCB_PrimitiveStringAlignMode={{CENTER:5}};return await eda.pcb_PrimitiveString.create(EPCB_LayerId.TOP_SILKSCREEN,{x},{y},{json.dumps(title)},"default",60,8,EPCB_PrimitiveStringAlignMode.CENTER,0,false,0,false,false);')
        assert api('return await eda.pcb_Document.save();')
        print(board, 'text saved', flush=True)


if __name__ == '__main__':
    if '--text' in sys.argv:
        enlarge_text()
    else:
        restore_footprints()
