# debug renders: blender -b --python dbg_render.py -- <blend> <outprefix> <spec>...
# spec = name:action:frame:az:el:dist:tz[:extra]  extra: jaw=deg,blink=1,throat=s,smile=v,mouth=v
exec(open('/Users/administrator/Tilo工作台/20261028-青跃三维/project/src/common.py').read())
import os
args=sys.argv[sys.argv.index('--')+1:]
bpy.ops.wm.open_mainfile(filepath=args[0]); out=args[1]
if os.environ.get('RELINK'):   # render an older .blend with its own texture set
    for im in bpy.data.images:
        fn=os.path.basename(bpy.path.abspath(im.filepath)) if im.filepath else ''
        if fn and os.path.exists(os.path.join(os.environ['RELINK'],fn)): im.filepath=os.path.join(os.environ['RELINK'],fn); im.reload()
sc=bpy.context.scene
sc.render.engine='CYCLES'; sc.cycles.samples=int(os.environ.get('SAMPLES','24')); sc.cycles.device='CPU'; sc.cycles.use_denoising=True
R=int(os.environ.get('RES','520')); sc.render.resolution_x=R; sc.render.resolution_y=R
sc.view_settings.view_transform='AgX'; sc.view_settings.look='AgX - Base Contrast'; sc.view_settings.exposure=float(os.environ.get('EXPO','-0.3'))
w=bpy.data.worlds.new('w'); sc.world=w; w.use_nodes=True; bg=w.node_tree.nodes['Background']; bg.inputs[0].default_value=(0.85,0.86,0.72,1); bg.inputs[1].default_value=0.6
def sun(name,e,c,rot,ang=0.1):
    L=bpy.data.lights.new(name,'SUN'); L.energy=e; L.color=c; L.angle=ang; o=bpy.data.objects.new(name,L); sc.collection.objects.link(o); o.rotation_euler=[math.radians(a) for a in rot]
sun('key',2.6,(1,0.95,0.85),(50,0,-40),0.5); sun('back',4.0,(1,0.85,0.6),(-60,0,-150),0.1)
cam=bpy.data.objects.new('Cam',bpy.data.cameras.new('Cam')); sc.collection.objects.link(cam); sc.camera=cam; cam.data.lens=60
rig=bpy.data.objects['Qingyue_Rig']; rig.animation_data_create()
for tr in rig.animation_data.nla_tracks: tr.mute=True
body=bpy.data.objects['Qingyue_Body']
acts={a.name:a for a in bpy.data.actions}
for spec in args[2:]:
    p=spec.split(':'); name,act,fr,az,el,dist,tz=p[:7]; ex=dict(kv.split('=') for kv in p[7].split(',')) if len(p)>7 and p[7] else {}
    rig.animation_data.action=acts.get(act)
    if act in acts:
        try: rig.animation_data.action_slot=acts[act].slots[0]
        except Exception: pass
    for pb in rig.pose.bones:
        pb.rotation_mode='QUATERNION'
        if act not in acts: pb.rotation_quaternion=(1,0,0,0); pb.location=(0,0,0); pb.scale=(1,1,1)
    sc.frame_set(int(fr))
    if 'jaw' in ex: rig.pose.bones['jaw'].rotation_quaternion=Quaternion(Vector((1,0,0)),math.radians(float(ex['jaw'])))
    if 'throat' in ex: rig.pose.bones['throat'].scale=(float(ex['throat']),)*3
    for k in body.data.shape_keys.key_blocks[1:]: k.value=0
    body.data.shape_keys.key_blocks['smile'].value=float(ex.get('smile',0.6))
    for k in ('mouth_open','viseme_A','viseme_O','viseme_E','viseme_U','throat_puff'):
        if k in ex: body.data.shape_keys.key_blocks[k].value=float(ex[k])
    for n in 'LR':
        lid=bpy.data.objects['Qingyue_Lid_'+n]; lid.data.shape_keys.key_blocks['blink_'+n].value=float(ex.get('blink',0))
    bpy.context.view_layer.update()
    t=Vector((0.0,-0.05,float(tz))); a=math.radians(float(az)); e=math.radians(float(el)); r=float(dist)
    cam.location=t+Vector((-math.sin(a)*math.cos(e)*r,-math.cos(a)*math.cos(e)*r,math.sin(e)*r))
    cam.rotation_mode='QUATERNION'; cam.rotation_quaternion=(t-cam.location).to_track_quat('-Z','Y')
    sc.render.filepath=out+'_'+name+'.png'; bpy.ops.render.render(write_still=True)
print('DBG DONE')
