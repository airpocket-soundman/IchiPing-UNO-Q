"""Offline conservative two-layer route planning; does not mutate EasyEDA."""
import heapq
import itertools
import json
import math
from pathlib import Path
import numpy as np
import shapely
from shapely.geometry import Point, LineString, box
from pcb_local_audit import OUT

STEP = 5
NX, NY = 271, 411
XS, YS = np.meshgrid(np.arange(NX)*STEP+10, -np.arange(NY)*STEP-10)

def node(x,y,z):
    return (round((x-10)/STEP),round((-y-10)/STEP),z)

def xy(n):
    return (n[0]*STEP+10,-n[1]*STEP-10)

def search(start, goal, blocked, via_blocked):
    starts=[node(*start,z) for z in range(2)]
    goals={node(*goal,z) for z in range(2)}
    gx,gy,_=next(iter(goals))
    h=lambda n:math.hypot(n[0]-gx,n[1]-gy)
    queue=[]; costs={}; parents={}; serial=itertools.count()
    for n in starts:
        if not blocked[n[2]][n[1],n[0]]:
            costs[n]=0;heapq.heappush(queue,(h(n),next(serial),n))
    moves=[(1,0,1),(-1,0,1),(0,1,1),(0,-1,1),(1,1,1.4142),(-1,1,1.4142),(1,-1,1.4142),(-1,-1,1.4142)]
    visited=set()
    while queue:
        _,_,n=heapq.heappop(queue)
        if n in visited:continue
        visited.add(n)
        if n in goals:
            path=[n]
            while n in parents:n=parents[n];path.append(n)
            return path[::-1]
        x,y,z=n
        for dx,dy,c in moves+[(0,0,25)]:
            zz=1-z if dx==dy==0 else z
            xx,yy=x+dx,y+dy
            if not(0<=xx<NX and 0<=yy<NY) or blocked[zz][yy,xx]:continue
            if zz!=z and (via_blocked[0][y,x] or via_blocked[1][y,x]):continue
            if dx and dy and (blocked[z][y,xx] or blocked[z][yy,x]):continue
            nn=(xx,yy,zz); nc=costs[n]+c
            if nc<costs.get(nn,1e100):
                costs[nn]=nc;parents[nn]=n
                heapq.heappush(queue,(nc+h(nn),next(serial),nn))
    raise RuntimeError(f'No path {start} -> {goal}; visited {len(visited)}')

def main():
    data=json.loads((OUT/'audio-route-input.json').read_text(encoding='utf-8'))
    nets={p['net'] for p in data['pads'] if p['net']}
    obstacles=[]
    for p in data['pads']:
        w,h=p['pad'][1:3]
        if int(round(p['rotation']))%180==90:w,h=h,w
        geom=box(p['x']-w/2,p['y']-h/2,p['x']+w/2,p['y']+h/2)
        obstacles.append((p['net'],None,geom))
    for v in data['vias']:
        obstacles.append((v['net'],None,Point(v['x'],v['y']).buffer(v['diameter']/2)))
    paths=[]; newvias=[]
    order=sorted(nets,key=lambda n:(n!='GND', not n.startswith('MI2S'),n))
    for net in order:
        width=20 if net.startswith('+') else 10
        blocked=[];via_blocked=[]
        for z in range(2):
            shapes=[s for n,l,s in obstacles if n!=net and (l is None or l==z)]
            geom=shapely.union_all(shapes)
            blocked.append(shapely.intersects_xy(geom.buffer(width/2+7),XS,YS))
            via_blocked.append(shapely.intersects_xy(geom.buffer(12+7),XS,YS))
        terminals=list(dict.fromkeys((p['x'],p['y']) for p in data['pads'] if p['net']==net))
        terminals += [(v['x'],v['y']) for v in data['vias'] if v['net']==net]
        if len(terminals)<2:continue
        tree=[terminals.pop(0)]; count=0
        while terminals:
            _,i,target=min((math.dist(a,b),i,b) for i,a in enumerate(terminals) for b in tree)
            start=terminals.pop(i)
            for candidate in sorted(tree,key=lambda t:math.dist(start,t)):
                try:
                    path=search(start,candidate,blocked,via_blocked)
                    target=candidate
                    break
                except RuntimeError:
                    continue
            else:
                raise RuntimeError(f'No connection from {net} {start} to tree')
            coords=[(*start,path[0][2])]+[(*xy(n),n[2]) for n in path]+[(*target,path[-1][2])]
            compact=[coords[0]]
            for i in range(1,len(coords)-1):
                a,b,c=compact[-1],coords[i],coords[i+1]
                if a[2]==b[2]==c[2] and abs((b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0]))<1e-7:continue
                compact.append(b)
            compact.append(coords[-1])
            for a,b in zip(compact,compact[1:]):
                if a[:2]==b[:2]:
                    if a[2]!=b[2]:newvias.append({'net':net,'x':a[0],'y':a[1]})
                    continue
                paths.append({'net':net,'layer':a[2]+1,'a':a[:2],'b':b[:2],'width':width})
            tree.append(start);count+=1
        for l in paths:
            if l['net']==net:obstacles.append((net,l['layer']-1,LineString([l['a'],l['b']]).buffer(l['width']/2)))
        for v in newvias:
            if v['net']==net:obstacles.append((net,None,Point(v['x'],v['y']).buffer(12)))
        print(net,count,'connections',flush=True)
    result={'lines':paths,'vias':newvias,'replaceLines':[l['primitiveId'] for l in data['lines'] if l['layer'] in [1,2]],'nets':sorted(nets)}
    (OUT/'audio-route-plan.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('Planned',len(paths),'segments',len(newvias),'vias')

if __name__=='__main__':main()
