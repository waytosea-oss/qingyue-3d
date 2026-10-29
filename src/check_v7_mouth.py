# v7 talk-mouth self check: blender -b --python check_v7_mouth.py -- <blend> <label> [report.txt]
# Lateral (left/right, x in the head's own frame) displacement of the mouth-corner vertices during speech:
#   (1) every mouth shape key at 1.0   (2) jaw bone at 2..10 deg   (3) every frame of the 'talk' action.
# Requirement (TASK v7): <= 0.5 mm.
exec(open('/Users/administrator/Tilo工作台/20261028-青跃三维/project/src/common.py').read())
args=sys.argv[sys.argv.index('--')+1:]; bpy.ops.wm.open_mainfile(filepath=args[0]); label=args[1]; rep=args[2] if len(args)>2 else None
sc=bpy.context.scene; rig=bpy.data.objects['Qingyue_Rig']; body=bpy.data.objects['Qingyue_Body']; me=body.data
for tr in rig.animation_data.nla_tracks: tr.mute=True
V=verts_np(body); VD=np.load(BUILD+'verts.npz') if len(V)==len(np.load(BUILD+'verts.npz')['V']) else None
x,y,z=V.T; zl=sdf.zm(x,y)
# mouth-corner vertices: outer lip surface at the two ends of the lip slit
near=(np.abs(z-zl)<0.012)&(np.abs(sdf.mouth_vol(V))<0.035)&(sdf.body_raw(V)>-0.004)&(y<0.0)
corners=[]
for s in (1,-1):
    idx=np.nonzero(near&(np.sign(x)==s))[0]; corners+=list(idx[np.argsort(-np.abs(x[idx]))[:8]])
corners=np.array(corners)
lines=['[%s] mouth-corner vertices: %d (x = %s .. %s m)'%(label,len(corners),np.round(x[corners].min(),3),np.round(x[corners].max(),3))]
kb=me.shape_keys.key_blocks
worst={}
for k in ('mouth_open','viseme_A','viseme_O','viseme_E','viseme_U','smile'):
    if k not in kb: continue
    a=np.zeros(len(V)*3); kb[k].data.foreach_get('co',a); a=a.reshape(-1,3)
    dx=np.abs(a[corners,0]-V[corners,0]).max()*1000; dz=np.abs(a[corners,2]-V[corners,2]).max()*1000
    tag='(static default expression, not driven by speech)' if k=='smile' else ''
    lines.append('  shape key %-10s at 1.0: corner lateral |dx| max %.3f mm, vertical |dz| max %.2f mm %s'%(k,dx,dz,tag))
    if k!='smile': worst['keys']=max(worst.get('keys',0),dx)
for k in kb[1:]: k.value=0
def head_local(P):
    hb=rig.pose.bones['head']; M=rig.data.bones['head'].matrix_local@hb.matrix.inverted()
    return np.array([tuple(M@Vector(p)) for p in P])
def corners_now():
    dg=bpy.context.evaluated_depsgraph_get(); oe=body.evaluated_get(dg); m=oe.to_mesh()
    P=np.array([tuple(m.vertices[int(i)].co) for i in corners]); oe.to_mesh_clear(); return head_local(P)
rig.animation_data.action=None
for pb in rig.pose.bones: pb.rotation_mode='QUATERNION'; pb.rotation_quaternion=(1,0,0,0); pb.location=(0,0,0); pb.scale=(1,1,1)
sc.frame_set(1); base=corners_now()
for deg in (2,4,8,12,16,20,22,24):
    rig.pose.bones['jaw'].rotation_quaternion=Quaternion(Vector((1,0,0)),math.radians(-deg)); bpy.context.view_layer.update()
    P=corners_now(); dx=np.abs(P[:,0]-base[:,0]).max()*1000; dz=np.abs(P[:,2]-base[:,2]).max()*1000
    lines.append('  jaw bone %2d deg: corner lateral |dx| max %.3f mm, vertical |dz| max %.2f mm'%(deg,dx,dz)); worst['jaw']=max(worst.get('jaw',0),dx)
rig.pose.bones['jaw'].rotation_quaternion=(1,0,0,0)
act=bpy.data.actions.get('talk')
if act:
    rig.animation_data.action=act
    try: rig.animation_data.action_slot=act.slots[0]
    except Exception: pass
    mx=0; mz=0
    for f in range(int(act.frame_range[0]),int(act.frame_range[1])+1):
        sc.frame_set(f); P=corners_now(); mx=max(mx,np.abs(P[:,0]-base[:,0]).max()*1000); mz=max(mz,np.abs(P[:,2]-base[:,2]).max()*1000)
    lines.append('  talk action, all %d frames (head frame): corner lateral |dx| max %.3f mm, vertical |dz| max %.2f mm'%(int(act.frame_range[1]-act.frame_range[0]+1),mx,mz)); worst['talk']=mx
w=max(worst.values()); lines.append('  RESULT [%s]: worst corner lateral displacement during speech = %.3f mm -> %s (limit 0.5 mm)'%(label,w,'PASS' if w<=0.5 else 'FAIL'))
txt='\n'.join(lines); print(txt)
if rep: open(rep,'a').write(txt+'\n')
print('MOUTHCHECK DONE')
