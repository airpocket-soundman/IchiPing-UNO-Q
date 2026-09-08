"""Preserve and improve the existing linked EasyEDA schematics, not their circuits."""
import json
import sys
import math
import time
from pcb_local_audit import api, OUT, ROOT, records

PAGES = {'audio': '4b6aafcf375345b9', 'uno': 'cff2555ab025a4cb'}

def activate(board):
    uid = PAGES[board]
    api(f'const t=await eda.dmt_EditorControl.openDocument({json.dumps(uid)}); await eda.dmt_EditorControl.activateDocument(t); return true;')
    time.sleep(0.5)
    doc = api('return await eda.dmt_SelectControl.getCurrentDocumentInfo();')
    if doc.get('uuid') != uid:
        raise RuntimeError(doc)
    return doc

def snapshot(board):
    doc = activate(board)
    target = OUT / f'{board}-readability-source-before.txt'
    if not target.exists():
        target.write_text(api('return await eda.sys_FileManager.getDocumentSource();'), encoding='utf-8')
    data = api('const components=await eda.sch_PrimitiveComponent.getAll(); const pins={}; for(const c of components) pins[c.primitiveId]=await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(c.primitiveId); return {components,pins,attributes:await eda.sch_PrimitiveAttribute.getAll(),wires:await eda.sch_PrimitiveWire.getAll(),netlist:await (await eda.sch_ManufactureData.getNetlistFile()).text()};')
    data['doc'] = doc
    target = OUT / f'{board}-readability-baseline.json'
    if not target.exists():
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(doc)
    print('Attributes sample', json.dumps(data['attributes'][:5], ensure_ascii=False))
    print('Preserved', target)

def connectivity(raw):
    data = json.loads(raw)
    return {uid: {'props': {k: c['props'].get(k) for k in ('Designator', 'Device', 'Footprint', 'Name')},
                  'pins': {n: p.get('net') for n, p in c['pinInfoMap'].items()}}
            for uid, c in data['components'].items()}

def clean_duplicate_labels(board):
    activate(board)
    baseline = json.loads((OUT / f'{board}-readability-baseline.json').read_text(encoding='utf-8'))
    assert (ROOT / 'output/pdf' / f'{board}-schematic-before.pdf').exists()
    nets = {w['net'] for w in baseline['wires']}
    texts = api('return await eda.sch_PrimitiveText.getAll();')
    duplicates = [t['primitiveId'] for t in texts if t['content'] in nets]
    if duplicates:
        result = api(f'return await eda.sch_PrimitiveText.delete({json.dumps(duplicates)});')
        if not result:
            raise RuntimeError('Text removal failed')
    after = api('return await (await eda.sch_ManufactureData.getNetlistFile()).text();')
    if connectivity(baseline['netlist']) != connectivity(after):
        raise RuntimeError('Connectivity mismatch; stop without saving')
    if not api('return await eda.sch_Document.save();'):
        raise RuntimeError('Save failed')
    print(f'{board}: removed {len(duplicates)} redundant text labels; connectivity unchanged; saved.')

def layout_audio():
    board = 'audio'
    activate(board)
    baseline = json.loads((OUT / f'{board}-readability-baseline.json').read_text(encoding='utf-8'))
    assert (ROOT / 'output/pdf/audio-schematic-before.pdf').exists()
    positions = {
        'J14': (190, 620, 0), 'J15': (460, 620, 0),
        'J_MIC': (1020, 650, 0), 'JP_LR': (840, 570, 0),
        'C3': (730, 650, 270), 'J_AMP_SIG': (1020, 260, 0),
        'JP_GAIN': (820, 220, 0), 'J_AMP_PWR': (1000, 450, 0),
        'JP_MUTE': (800, 480, 0), 'R_SD': (700, 550, 90),
        'C1': (780, 330, 270), 'C2': (880, 330, 270),
    }
    components = {c['designator']: c for c in baseline['components'] if c.get('designator')}
    for name, (x, y, rotation) in positions.items():
        result = api(f'return await eda.sch_PrimitiveComponent.modify({json.dumps(components[name]["primitiveId"])}, {json.dumps(dict(x=x,y=y,rotation=rotation))});')
        if not result:
            raise RuntimeError('Move failed: ' + name)
    pins = {}
    for name, c in components.items():
        pins[name] = {p['pinNumber']: p for p in api(f'return await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId({json.dumps(c["primitiveId"])});')}
    (OUT / 'audio-readability-positioned-pins.json').write_text(json.dumps(pins, indent=2), encoding='utf-8')
    print('Audio layout positions set; pins captured. Routing must follow before save.')

def route_audio(plan_only=False):
    activate('audio')
    b = json.loads((OUT / 'audio-readability-baseline.json').read_text(encoding='utf-8'))
    pins = json.loads((OUT / 'audio-readability-positioned-pins.json').read_text())
    handled = {('R_SD','1'),('J_AMP_PWR','1'),('J_AMP_PWR','2'),('J_AMP_PWR','3'),
               ('JP_MUTE','1'),('JP_MUTE','2'),('C1','1'),('C1','2'),('C2','1'),('C2','2'),
               ('J_MIC','6'),('JP_LR','1'),('J_AMP_SIG','4'),('JP_GAIN','1')}
    paths = [
        ('AMP_SD',[700,530,700,500,760,500,940,500,940,460,980,460]),
        ('AMP_SD',[780,485,760,485,760,500]),
        ('GND',[780,475,740,475,740,290,780,290,880,290,950,290,950,450,980,450]),
        ('GND',[780,315,780,290]),('GND',[880,315,880,290]),
        ('+5V',[980,440,920,440,920,370,880,370,780,370,780,345]),
        ('+5V',[880,345,880,370]),
        ('MIC_LR',[1000,625,950,625,950,575,820,575]),
        ('AMP_GAIN',[1000,245,960,245,960,180,720,180,720,225,800,225]),
    ]
    labels = [(705,507,'AMP_SD',10,3),(745,296,'GND',10,3),(785,377,'+5V',10,3),
              (860,581,'MIC_LR',10,3),(835,205,'AMP_GAIN',10,3)]
    for c in json.loads(b['netlist'])['components'].values():
        name=c['props']['Designator']
        for n,p in c['pinInfoMap'].items():
            net=p.get('net')
            if not net or (name,n) in handled:
                continue
            pin=pins[name][n]
            x,y=round(pin['x'],5),round(pin['y'],5)
            angle=math.radians(pin['rotation'])
            dx,dy=round(math.cos(angle)),round(math.sin(angle))
            ex,ey=x+dx*40,y+dy*40
            paths.append((net,[x,y,ex,ey]))
            if dx<0: labels.append((ex-4,ey,net,9,8))
            elif dx>0: labels.append((ex+4,ey,net,9,2))
            else: labels.append((ex+5,ey,net,10,2))
    if plan_only:
        return paths, labels
    api('const ws=await eda.sch_PrimitiveWire.getAll(); if(ws.length)await eda.sch_PrimitiveWire.delete(ws.map(w=>w.primitiveId)); const ts=await eda.sch_PrimitiveText.getAll(); if(ts.length)await eda.sch_PrimitiveText.delete(ts.map(t=>t.primitiveId)); await eda.sch_Document.save();await eda.dmt_EditorControl.closeDocument("4b6aafcf375345b9");return true;')
    activate('audio')
    if api('return (await eda.sch_PrimitiveWire.getAll()).length;'):
        raise RuntimeError('Old wires remain after reload')
    js = 'const made=[];'
    js += 'for(const [net,line] of '+json.dumps(paths)+'){const w=await eda.sch_PrimitiveWire.create(line,net); if(!w)throw Error("Wire failed"); made.push(w.primitiveId); for(const a of await eda.sch_PrimitiveAttribute.getAll(w.primitiveId))if(a.valueVisible||a.keyVisible)await eda.sch_PrimitiveAttribute.modify(a.primitiveId,{valueVisible:false,keyVisible:false});} return made;'
    result=api(js)
    print('Routed',len(result),'wires')
    # These named constants mirror the documented text-alignment enumeration.
    js='const ALIGN={LEFT_MIDDLE:2,LEFT_BOTTOM:3,RIGHT_MIDDLE:8};'
    js+='for(const [x,y,t,size,align] of '+json.dumps(labels)+')await eda.sch_PrimitiveText.create(x,y,t,0,null,"Arial",size,false,false,false,align);return true;'
    api(js)
    cs=api('return await eda.sch_PrimitiveComponent.getAll();')
    for c in cs:
        if not c.get('designator'): continue
        name=c['designator'];x=c['x'];y=c['y']
        if name in ('J14','J15'):
            loc=(x-20,y+125);val=(x-45,y-125)
        elif name.startswith('C') or name=='R_SD':
            loc=(x+22,y+15);val=(x+22,y-5)
        else:
            loc=(x+25,y+15);val=(x+25,y-8)
        show_value=name in ('C1','C2','C3','R_SD')
        edits={'Designator':dict(x=loc[0],y=loc[1],fontSize=12,rotation=0,alignMode=2,valueVisible=True),
               'Name':dict(x=val[0],y=val[1],fontSize=10,rotation=0,alignMode=2,valueVisible=show_value)}
        api('const edits='+json.dumps(edits)+';for(const a of await eda.sch_PrimitiveAttribute.getAll('+json.dumps(c['primitiveId'])+'))if(edits[a.key])await eda.sch_PrimitiveAttribute.modify(a.primitiveId,edits[a.key]);return true;')
    api('await eda.sch_Document.save(); await eda.dmt_EditorControl.closeDocument("4b6aafcf375345b9");return true;')
    activate('audio')
    after=api('return await (await eda.sch_ManufactureData.getNetlistFile()).text();')
    (OUT/'audio-readability-after-netlist.json').write_text(after,encoding='utf-8')
    if connectivity(b['netlist'])!=connectivity(after):
        before_c,after_c=connectivity(b['netlist']),connectivity(after)
        print([(k,before_c.get(k),after_c.get(k)) for k in before_c.keys()|after_c.keys() if before_c.get(k)!=after_c.get(k)])
        raise RuntimeError('Connectivity mismatch; investigate before save')
    print('Connectivity unchanged:',api('return await eda.sch_Document.save();'))

def verify(board):
    activate(board)
    b=json.loads((OUT/f'{board}-readability-baseline.json').read_text(encoding='utf-8'))
    after=api('return await (await eda.sch_ManufactureData.getNetlistFile()).text();')
    old,new=connectivity(b['netlist']),connectivity(after)
    diff={k:{'before':old.get(k),'after':new.get(k)} for k in old.keys()|new.keys() if old.get(k)!=new.get(k)}
    print(json.dumps(diff,ensure_ascii=False,indent=2))
    if diff: raise RuntimeError('Connectivity mismatch')
    (OUT/f'{board}-readability-verified-netlist.json').write_text(after,encoding='utf-8')
    print(board, 'all component identities and pin nets unchanged')

def restore_audio_baseline():
    activate('audio')
    draft=api('return await eda.sys_FileManager.getDocumentSource();')
    (OUT/'audio-readability-draft-investigate.txt').write_text(draft,encoding='utf-8')
    original=(OUT/'audio-readability-source-before.txt').read_text(encoding='utf-8')
    old_records=list(records(original)); current_records=list(records(draft))
    desired={(m['type'],m.get('id',m['type'])):(m,d) for _,_,m,d in old_records if m['type'] not in ('DOCHEAD','EDIT_HEAD')}
    present={(m['type'],m.get('id',m['type'])):(m,d) for _,_,m,d in current_records if m['type'] not in ('DOCHEAD','EDIT_HEAD')}
    ticket=max(m.get('ticket',0) for _,_,m,_ in current_records)+100
    lines=[draft.splitlines()[0]]
    for key in present.keys()|desired.keys():
        ticket+=1
        m,d=desired.get(key,(present[key][0],'')) if key in present else desired[key]
        m=dict(m,ticket=ticket)
        lines.append(json.dumps(m)+'||'+json.dumps(d,ensure_ascii=False)+'|')
    source='\n'.join(lines)
    if not api('return await eda.sys_FileManager.setDocumentSource('+json.dumps(source)+');'):
        raise RuntimeError('Source restore failed')
    api('await eda.sch_Document.save();await eda.dmt_EditorControl.closeDocument("4b6aafcf375345b9");return true;')
    activate('audio')
    clean_duplicate_labels('audio')

if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[2] == 'restore':
        restore_audio_baseline()
    elif len(sys.argv) > 2 and sys.argv[2] == 'verify':
        verify(sys.argv[1])
    elif len(sys.argv) > 2 and sys.argv[2] == 'route':
        route_audio()
    elif len(sys.argv) > 2 and sys.argv[2] == 'layout':
        layout_audio()
    elif len(sys.argv) > 2 and sys.argv[2] == 'clean':
        clean_duplicate_labels(sys.argv[1])
    else:
        snapshot(sys.argv[1])
