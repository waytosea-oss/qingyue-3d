# v6: arm-sweep clearance for the vest. blender -b --python armsweep.py   (needs build/stage4.blend from a previous pass)
# For every action (every 2nd frame) the skinned body is evaluated; for each torso vertex we keep the smallest
# distance to any arm vertex. stage3v cuts the vest wherever an arm ever comes closer than the vest needs.
exec(open('/Users/administrator/Tilo工作台/20261028-青跃三维/project/src/common.py').read())
import os
from mathutils import kdtree
bpy.ops.wm.open_mainfile(filepath=BUILD+'stage4.blend')
sc=bpy.context.scene; rig=bpy.data.objects['Qingyue_Rig']; rig.animation_data_create()
for tr in rig.animation_data.nla_tracks: tr.mute=True
VD=np.load(BUILD+'verts.npz'); g=VD['grp']; V0=VD['V']
cand=np.nonzero((g==0)&(V0[:,2]>0.1)&(V0[:,2]<0.65))[0]
if os.path.exists(BUILD+'vest_cand.npy'): cand=np.load(BUILD+'vest_cand.npy')   # only vertices that can carry the vest
# only the torso band can carry the vest; test it against EVERY other part of the body (arms, legs, head/jaw/throat):
# a vertex is 'other' if it is >8 cm away in the rest pose (so the vest's own neighbourhood never counts)
dmin=np.full(len(V0),9.0); body=bpy.data.objects['Qingyue_Body']
from mathutils import kdtree as _k
KR=_k.KDTree(len(V0))
for i,p in enumerate(V0): KR.insert(p,i)
KR.balance()
for act in bpy.data.actions:
    rig.animation_data.action=act
    try: rig.animation_data.action_slot=act.slots[0]
    except Exception: pass
    f0,f1=[int(v) for v in act.frame_range]
    for f in range(f0,f1+1,2):
        sc.frame_set(f); dg=bpy.context.evaluated_depsgraph_get(); oe=body.evaluated_get(dg); m=oe.to_mesh()
        P=np.zeros(len(m.vertices)*3); m.vertices.foreach_get('co',P); P=P.reshape(-1,3); oe.to_mesh_clear()
        kt=kdtree.KDTree(len(P))
        for i,p in enumerate(P): kt.insert(p,i)
        kt.balance()
        for i in cand:
            r=kt.find_range(P[i],0.035)
            if len(r)<2: continue
            js=np.fromiter((x[1] for x in r),int,len(r)); ds=np.fromiter((x[2] for x in r),float,len(r))
            far=np.einsum('ij,ij->i',V0[js]-V0[i],V0[js]-V0[i])>0.0064     # >8 cm apart at rest = another body part
            if far.any(): dmin[i]=min(dmin[i],ds[far].min())
    print('SWEEP',act.name,'done')
np.save(BUILD+'armsweep.npy',dmin)
print('SWEEP OK  torso verts ever within 3 cm of another body part:',int((dmin[cand]<0.03).sum()),'of',len(cand))
