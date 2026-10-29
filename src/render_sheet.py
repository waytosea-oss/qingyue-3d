exec(open('/Users/administrator/Tilo工作台/20261028-青跃三维/project/src/common.py').read())
args=sys.argv[sys.argv.index('--')+1:]; out=args[0]; shots=[a.split(':') for a in args[1:]]
sc=bpy.context.scene; sc.render.engine='CYCLES'; sc.cycles.samples=int(os.environ.get('SAMPLES','20')) if 'os' in dir() else 20
import os; sc.cycles.samples=int(os.environ.get('SAMPLES','20')); sc.cycles.device='CPU'
R=int(os.environ.get('RES','400')); sc.render.resolution_x=R; sc.render.resolution_y=R
sc.render.film_transparent=False
w=bpy.data.worlds.new('w'); sc.world=w; w.use_nodes=True; bg=w.node_tree.nodes['Background']; bg.inputs[0].default_value=(0.75,0.82,0.7,1); bg.inputs[1].default_value=0.55
L=bpy.data.lights.new('key','SUN'); L.energy=3.2; L.color=(1,0.93,0.8); L.angle=0.2; lo=bpy.data.objects.new('key',L); sc.collection.objects.link(lo); lo.rotation_euler=(math.radians(55),0,math.radians(-35))
L2=bpy.data.lights.new('rim','SUN'); L2.energy=2.5; L2.color=(1,0.9,0.7); lo2=bpy.data.objects.new('rim',L2); sc.collection.objects.link(lo2); lo2.rotation_euler=(math.radians(-60),0,math.radians(20))
cam=bpy.data.objects.new('Cam',bpy.data.cameras.new('Cam')); sc.collection.objects.link(cam); sc.camera=cam; cam.data.lens=55
rig=bpy.data.objects['Qingyue_Rig']; acts={a.name:a for a in bpy.data.actions}
rig.animation_data_create()
for tr in rig.animation_data.nla_tracks: tr.mute=True
files=[]
for i,(act,fr,az) in enumerate(shots):
    rig.animation_data.action=acts[act] if act!='rest' else None
    sc.frame_set(int(fr))
    a=math.radians(float(az)); r=3.6; t=Vector((0,-0.05,0.5 if act not in('jump','happy_spin') else 0.75))
    cam.location=t+Vector((-math.sin(a)*r,-math.cos(a)*r,0.5))
    cam.rotation_mode='QUATERNION'; cam.rotation_quaternion=(t-cam.location).to_track_quat('-Z','Y')
    f=out+'_%02d.png'%i; sc.render.filepath=f; bpy.ops.render.render(write_still=True); files.append(f)
print('FILES',' '.join(files))
