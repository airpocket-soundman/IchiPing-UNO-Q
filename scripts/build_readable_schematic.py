"""Build a complete schematic page from preserved native records, preserving identities."""
import copy
import json
import uuid
import math
import sys
from collections import defaultdict
from pcb_local_audit import api, OUT, records
from schematic_readability import activate, route_audio, verify, PAGES

POSITIONS = {'J14': (190,620,0),'J15':(460,620,0),'J_MIC':(1020,650,0),
 'JP_LR':(840,570,0),'C3':(730,650,270),'J_AMP_SIG':(460,350,0),
 'JP_GAIN':(250,310,0),'J_AMP_PWR':(1000,450,0),'JP_MUTE':(800,480,0),
 'R_SD':(700,550,90),'C1':(780,330,270),'C2':(880,330,270)}

def build_audio():
    paths, labels = route_audio(plan_only=True)
    paths=[(net,line) for net,line in paths if net!='AMP_GAIN']
    paths.append(('AMP_GAIN',[230,315,210,315,210,335,440,335]))
    for i,(net,line) in enumerate(paths):
        if line[0]==1000 and line[1] in (275,265,255):
            paths[i]=(net,[v+(-560 if j%2==0 else 90) for j,v in enumerate(line)])
        elif line[0]==800 and line[1]==215:
            paths[i]=(net,[v+(-570 if j%2==0 else 90) for j,v in enumerate(line)])
    labels=[(x,y,t,size,a) for x,y,t,size,a in labels if t!='AMP_GAIN']
    for i,(x,y,t,size,a) in enumerate(labels):
        if x==956 and y in (275,265,255): labels[i]=(x-560,y+90,t,size,a)
        elif x==756 and y==215: labels[i]=(x-570,y+90,t,size,a)
        elif t=='MIC_LR': labels[i]=(855,560,t,size,3)
    labels.append((260,341,'AMP_GAIN',10,3))
    notes=[(55,785,'AUDIO SHIELD - SIGNAL AND POWER',18,3),
        (90,765,'UNO Q BREAKOUT CARRIER',12,3),(710,755,'MICROPHONE / 1.8 V I2S',12,3),
        (170,260,'GAIN: OPEN=9dB / SHORT=12dB',11,3),
        (840,540,'LR: SHORT=L / OPEN=UNDEFINED',10,3),(790,415,'MUTE: OPEN=ON / SHORT=MUTE',10,3)]
    return write_page('audio',POSITIONS,paths,labels,notes)

def write_page(board,positions,paths,labels,notes):
    b=json.loads((OUT/f'{board}-readability-baseline.json').read_text(encoding='utf-8'))
    original=(OUT/f'{board}-readability-source-before.txt').read_text(encoding='utf-8')
    rec=list(records(original))
    comps={c['primitiveId']:c for c in b['components'] if c.get('designator')}
    wireids={m['id'] for _,_,m,d in rec if m['type']=='WIRE'}
    rows=[]
    for _,_,m,d in rec:
        m,d=copy.deepcopy(m),copy.deepcopy(d)
        if m['type'] in ('DOCHEAD','EDIT_HEAD','TEXT','WIRE'): continue
        if m['type']=='LINE' and d.get('lineGroup') in wireids: continue
        if m['type']=='ATTR' and d.get('parentId') in wireids: continue
        if m['type']=='ATTR' and '-' in d.get('parentId',''):
            pid=d.get('parentId','').split('-')[0]
            if pid in comps:
                c=comps[pid];x,y,r=positions[c['designator']]
                if d.get('x') is not None and d.get('y') is not None:
                    dx,dy=d['x']-c['x'],-d['y']-c['y']
                    a=math.radians(r-c['rotation'])
                    d['x']=round(x+dx*math.cos(a)-dy*math.sin(a),6)
                    d['y']=round(-(y+dx*math.sin(a)+dy*math.cos(a)),6)
                if d.get('key')=='NAME':
                    d.update(keyVisible=False,valueVisible=False)
        if m['type']=='COMPONENT' and m['id'] in comps:
            c=comps[m['id']];x,y,r=positions[c['designator']]
            d.update(x=x,y=-y,rotation=r)
        if m['type']=='ATTR' and d.get('parentId') in comps:
            c=comps[d['parentId']];name=c['designator'];x,y,r=positions[name]
            if d['key'] in ('Designator','Name'):
                is_id=d['key']=='Designator'
                if name in ('J14','J15'):
                    tx,ty=x-20,y+125 if is_id else y-125
                elif name.startswith('C') or name=='R_SD':
                    tx,ty=x+22,y+(15 if is_id else -5)
                elif board=='uno':
                    tx,ty=x-10,y+55 if is_id else y-55
                else:
                    tx,ty=x+25,y+(15 if is_id else -8)
                if name=='JP_MUTE' and is_id:ty=y+35
                if board=='uno' and is_id:
                    if name in ('J_PWR_IN','J_SERVO_5V_OUT'):ty=y+30
                    elif name in ('J1','J3','J4'):ty=y+65
                    elif name=='J2':ty=y+90
                    elif name=='C_SERVO_BULK':tx,ty=760,560
                    elif name=='J_SERVO_CTRL':tx=1020
                d.update(x=tx,y=-ty,rotation=0,fontSize=12 if is_id else 10,
                         fontFamily='Arial',align='LEFT_MIDDLE',keyVisible=False,
                         valueVisible=is_id or name in ('C1','C2','C3','R_SD'))
            elif d.get('valueVisible') or d.get('keyVisible'):
                # Non-essential copied attributes must not obscure the circuit.
                d.update(valueVisible=False,keyVisible=False)
        rows.append((m,d))
    def add(kind,data):
        ident=uuid.uuid4().hex[:16]
        rows.append((dict(type=kind,id=ident,ticket=1),data))
        return ident
    grouped=defaultdict(list)
    for net,line in paths: grouped[net].append(line)
    for net,lines in grouped.items():
        wid=add('WIRE',{'zIndex':100})
        for line in lines:
            for i in range(0,len(line)-2,2):
                add('LINE',dict(fillColor=None,fillStyle=None,strokeColor=None,strokeStyle=None,
                    strokeWidth=None,startX=line[i],startY=-line[i+1],endX=line[i+2],endY=-line[i+3],lineGroup=wid))
        add('ATTR',dict(x=None,y=None,rotation=0,color=None,fontFamily='Arial',fontSize=10,
            fontWeight=False,italic=False,underline=False,align='LEFT_MIDDLE',value=net,
            keyVisible=False,valueVisible=False,key='NET',fillColor=None,parentId=wid,zIndex=100))
    text_template=next(d for _,_,m,d in rec if m['type']=='TEXT')
    aligns={2:'LEFT_MIDDLE',3:'LEFT_BOTTOM',8:'RIGHT_MIDDLE'}
    labels += notes
    for x,y,t,size,align in labels:
        d=copy.deepcopy(text_template)
        d.update(x=x,y=-y,text=t,fontSize=size,fontFamily='Arial',rotation=0,align=aligns[align])
        # Native TEXT records use content, not a component Name attribute.
        if 'content' in d: d['content']=t
        if 'value' in d: d['value']=t
        add('TEXT',d)
    lines=[original.splitlines()[0]]
    for i,(m,d) in enumerate(rows,1):
        m['ticket']=i
        lines.append(json.dumps(m,separators=(',',':'))+'||'+json.dumps(d,ensure_ascii=False,separators=(',',':'))+'|')
    source='\n'.join(lines)+'\n'
    (OUT/f'{board}-readable-candidate.txt').write_text(source,encoding='utf-8')
    activate(board)
    close='await eda.dmt_EditorControl.closeDocument('+json.dumps(PAGES[board])+');return true;'
    api(close)
    activate(board)
    print('Cleared',api('const w=await eda.sch_PrimitiveWire.getAll();const t=await eda.sch_PrimitiveText.getAll();if(w.length)await eda.sch_PrimitiveWire.delete(w.map(x=>x.primitiveId));if(t.length)await eda.sch_PrimitiveText.delete(t.map(x=>x.primitiveId));await eda.sch_Document.save();return {wires:w.length,texts:t.length};'))
    api(close)
    activate(board)
    if not api('return await eda.sys_FileManager.setDocumentSource('+json.dumps(source)+');'):
        raise RuntimeError('Import failed')
    api('await eda.sch_Document.save();'+close)
    activate(board)
    api(close)
    activate(board)
    print('Native source applied')

def build_uno():
    pos={'J1':(190,650,0),'J2':(190,470,0),'J3':(190,300,0),'J4':(190,150,0),
        'J_PWR_IN':(490,735,0),'J_SERVO_5V_OUT':(750,735,0),
        'C_PWR_BULK':(470,630,270),'C_PWR_HF':(620,630,270),'C_SERVO_BULK':(760,630,270),
        'J_WIN_A':(930,700,0),'J_WIN_B':(1090,700,0),'J_WIN_C':(930,590,0),
        'J_DOOR_AB':(1090,590,0),'J_DOOR_BC':(930,480,0),'J_EXEC':(1090,480,0),
        'J_RAIN':(930,365,0),'J_SERVO_CTRL':(1090,365,0),
        'J_TFT_PWR':(490,320,0),'J_TFT_SIG':(710,260,0)}
    b=json.loads((OUT/'uno-readability-baseline.json').read_text(encoding='utf-8'))
    byname={c['designator']:c for c in b['components'] if c.get('designator')}
    paths=[('+5V',[470,740,440,740,440,680,470,680,620,680,760,680,780,680,780,740,730,740]),
        ('GND',[470,730,420,730,420,585,470,585,620,585,760,585,810,585,810,710,710,710,710,730,730,730])]
    for x in (470,620,760):
        paths.extend([('+5V',[x,645,x,680]),('GND',[x,615,x,585])])
    handled={'J_PWR_IN','J_SERVO_5V_OUT','C_PWR_BULK','C_PWR_HF','C_SERVO_BULK'}
    labels=[(500,687,'+5V',10,3),(500,591,'GND',10,3)]
    for comp in json.loads(b['netlist'])['components'].values():
        name=comp['props']['Designator']
        if name in handled: continue
        c=byname[name];nx,ny,r=pos[name]
        for p in b['pins'][c['primitiveId']]:
            net=comp['pinInfoMap'][p['pinNumber']].get('net')
            if not net:continue
            x,y=p['x']+nx-c['x'],p['y']+ny-c['y']
            a=math.radians(p['rotation']);dx,dy=round(math.cos(a)),round(math.sin(a))
            ex,ey=x+dx*30,y+dy*30
            paths.append((net,[x,y,ex,ey]));labels.append((ex-4,ey,'NC (reserved)' if net.startswith('UNCONNECTED') else net,9,8))
    notes=[(45,785,'UNO Q SHIELD - POWER AND EXTERNAL I/O',18,3),
        (80,750,'UNO HEADERS',12,3),
        (920,790,'SWITCH INPUTS',12,3),(420,415,'DISPLAY',12,3),
        (492,625,'470u / 10V',10,2),(642,625,'100n',10,2),(760,542,'1000u',10,2)]
    write_page('uno',pos,paths,labels,notes)

def finish_labels(board):
    close='await eda.dmt_EditorControl.closeDocument('+json.dumps(PAGES[board])+');return true;'
    api(close);activate(board)
    print(api('let count=0;for(const w of await eda.sch_PrimitiveWire.getAll())for(const a of await eda.sch_PrimitiveAttribute.getAll(w.primitiveId))if(a.key==="NET"||a.key==="Name"){await eda.sch_PrimitiveAttribute.modify(a.primitiveId,{valueVisible:false,keyVisible:false});count++;}await eda.sch_Document.save();return count;'))
    api(close);activate(board)

if __name__=='__main__':
    if len(sys.argv)>2 and sys.argv[2]=='labels':finish_labels(sys.argv[1])
    else:build_uno() if len(sys.argv)>1 and sys.argv[1]=='uno' else build_audio()
