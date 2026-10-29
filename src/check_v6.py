# v6 automated deformation check: blender -b --python check_v6.py -- <blend> [report.txt]
# For every action at key frames, evaluates the skinned meshes and reports
#   vest  : shell/parts vertices that end up inside the skin or the arms (penetration), worst depth
#   crown : vertices inside the skin, largest gap to the skin (floating), min distance to the eyelids (open & closed)
exec(open('/Users/administrator/Tilo工作台/20261028-青跃三维/project/src/common.py').read())
from mathutils.bvhtree import BVHTree
args=sys.argv[sys.argv.index('--')+1:]
bpy.ops.wm.open_mainfile(filepath=args[0]); rep_path=args[1] if len(args)>1 else None
sc=bpy.context.scene; rig=bpy.data.objects['Qingyue_Rig']; rig.animation_data_create()
for tr in rig.animation_data.nla_tracks: tr.mute=True
acts={a.name:a for a in bpy.data.actions}
for _ob in bpy.data.objects:   # evaluate the runtime state: the page shows smile 0.6, every other shape key 0
    if _ob.type=='MESH' and _ob.data.shape_keys:
        for _k in _ob.data.shape_keys.key_blocks[1:]: _k.value=0.6 if _k.name=='smile' else 0.0
FR={'sit_hug':[1,30],'idle':[1,20,60,90],'croak':[4,8,13,21,35],'jump':[3,5,8,11,15,20,25,28,31,36,40],
    'hop_forward':[4,7,11,15,19,22,25,34],'wave':[8,13,18,24,30,48],'talk':[5,21],'happy_spin':[12,18,24,36,50],
    'sleep':[1,40],'look_around':[24,66],'swim':[1,5,9,12,15,18,21,25,28]}
def ev(name):
    ob=bpy.data.objects[name]; dg=bpy.context.evaluated_depsgraph_get(); oe=ob.evaluated_get(dg); m=oe.to_mesh()
    P=np.array([tuple(oe.matrix_world@v.co) for v in m.vertices]); tris=[tuple(p.vertices) for p in m.polygons]; oe.to_mesh_clear(); return P,tris
def bvh(P,tris): return BVHTree.FromPolygons([tuple(p) for p in P],tris)
DIRS=[Vector((0.0,0.0,1.0)),Vector((1.0,0.31,0.17)).normalized(),Vector((-0.23,-1.0,0.41)).normalized()]
def _parity(T,p,d):
    n=0; o=Vector(p)
    for _ in range(60):
        hit=T.ray_cast(o,d)
        if hit[0] is None: break
        n+=1; o=hit[0]+d*1e-5
    return n&1
def inside_depth(T,pts):
    """signed distance to the skin: negative = inside (ray-parity majority vote over 3 directions; robust to
    winding and to the overlapping arm/torso shells), magnitude = distance to the nearest skin point"""
    out=[]
    for p in pts:
        co,nn,fi,d=T.find_nearest(Vector(p))
        ins=(Vector(p)-co).dot(nn)<0 and sum(_parity(T,p,dv) for dv in DIRS)>=2   # both tests must agree
        out.append(-d if ins else d)
    return np.array(out)
lines=[]; worst={'vest':0,'parts':0,'crown_in':0}
for an,frames in FR.items():
    if an not in acts: continue
    rig.animation_data.action=acts[an]
    try: rig.animation_data.action_slot=acts[an].slots[0]
    except Exception: pass
    for f in frames:
        sc.frame_set(f)
        BP,BT=ev('Qingyue_Body'); TB=bvh(BP,BT)
        res=[]
        for vn,key,tol in (('Qingyue_Vest','vest',0.0015),('Qingyue_VestParts','parts',0.0015)):
            if vn not in bpy.data.objects: continue
            P,_=ev(vn); sd=inside_depth(TB,P[::2]); bad=sd<-tol
            worst[key]=min(worst[key],sd.min()); res.append('%s in-skin %d (worst %.1f mm)'%(key,int(bad.sum()),-1000*min(0,sd.min())))
        CP,_=ev('Qingyue_Crown'); sd=inside_depth(TB,CP[::3])
        worst['crown_in']=min(worst['crown_in'],sd.min())
        lid=min(min(np.linalg.norm(CP[:,None,:]-ev('Qingyue_Lid_'+n)[0][None,::7],axis=-1).min() for n in 'LR'),9)
        res.append('crown in-skin %d (worst %.1f mm), crown-eyelid min %.1f mm'%(int((sd<-0.0015).sum()),-1000*min(0,sd.min()),1000*lid))
        if 'Qingyue_VocalSac' in bpy.data.objects:   # v8: inflatable vocal sac (ignore its intended neck/attachment zone inside the throat)
            SP,_=ev('Qingyue_VocalSac'); _so=bpy.data.objects['Qingyue_VocalSac']; _gi=_so.vertex_groups['sac_neck'].index
            far=np.array([not any(g.group==_gi and g.weight>0.5 for g in v.groups) for v in _so.data.vertices]); sdS=inside_depth(TB,SP[far][::2]) if far.any() else np.zeros(1)
            VP,VT=ev('Qingyue_Vest'); TV=bvh(VP,VT); sdV=inside_depth(TV,SP[far][::4]) if far.any() else np.zeros(1)
            sac_w=float(np.ptp(SP[:,0]))
            if sac_w<0.5: res.append('sac width %.2f m: deflated / emerging from inside the throat (hidden or partly inside by design), in-vest %d'%(sac_w,int((sdV<-0.0015).sum())))
            else:
                worst['sac']=min(worst.get('sac',0),sdS.min())
                res.append('sac width %.2f m (inflated), in-body %d (worst %.1f mm), in-vest %d'%(sac_w,int((sdS<-0.0015).sum()),-1000*min(0,sdS.min()),int((sdV<-0.0015).sum())))
        lines.append('%-12s f%-3d | %s'%(an,f,' | '.join(res)))
# crown floating: largest gap between the vine bundle (crown verts near the skin side) and the skin, rest pose
rig.animation_data.action=acts['sit_hug']; sc.frame_set(1)
BP,BT=ev('Qingyue_Body'); TB=bvh(BP,BT); CP,_=ev('Qingyue_Crown')
gaps=np.array([TB.find_nearest(Vector(p))[3] for p in CP])
lines.append('crown: nearest-skin distance of crown vertices: min %.1f mm, 5th pct %.1f mm (vine bottoms touch the skin)'%(1000*gaps.min(),1000*np.percentile(gaps,5)))
# blink: crown vs closed eyelids in rest pose
for n in 'LR':
    lid=bpy.data.objects['Qingyue_Lid_'+n]
lines.append('WORST: vest %.1f mm, vest parts %.1f mm, crown %.1f mm inside skin, vocal sac %.1f mm'%(-1000*worst['vest'],-1000*worst['parts'],-1000*worst['crown_in'],-1000*worst.get('sac',0)))
txt='\n'.join(lines); print(txt)
if rep_path: open(rep_path,'w').write(txt+'\n')
print('CHECK DONE')
