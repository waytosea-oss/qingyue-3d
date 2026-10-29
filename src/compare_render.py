exec(open('/Users/administrator/Tilo工作台/20261028-青跃三维/project/src/common.py').read())
import os
OUT=sys.argv[sys.argv.index('--')+1]; AZ=[float(a) for a in sys.argv[sys.argv.index('--')+2:]]
sc=bpy.context.scene; sc.render.engine='CYCLES'; sc.cycles.samples=int(os.environ.get('SAMPLES','48')); sc.cycles.device='CPU'; sc.cycles.use_denoising=True
R=int(os.environ.get('RES','800')); sc.render.resolution_x=R; sc.render.resolution_y=R
sc.view_settings.view_transform='AgX'; sc.view_settings.look='AgX - Punchy'; sc.view_settings.exposure=float(os.environ.get('EXPO','-1.0'))
w=bpy.data.worlds.new('w'); sc.world=w; w.use_nodes=True; bg=w.node_tree.nodes['Background']; bg.inputs[0].default_value=(0.85,0.86,0.72,1); bg.inputs[1].default_value=0.55
def sun(name,e,c,rot,ang=0.1):
    L=bpy.data.lights.new(name,'SUN'); L.energy=e; L.color=c; L.angle=ang; o=bpy.data.objects.new(name,L); sc.collection.objects.link(o); o.rotation_euler=[math.radians(a) for a in rot]
sun('key',3.0,(1,0.93,0.8),(50,0,-40),0.4); sun('back',5.0,(1,0.85,0.6),(-60,0,-150),0.08)
bpy.ops.mesh.primitive_circle_add(vertices=96,radius=1.5,fill_type='NGON',location=(0,0,0.0))
pad=bpy.context.active_object; m=bpy.data.materials.new('pad'); m.use_nodes=True; m.node_tree.nodes['Principled BSDF'].inputs[0].default_value=(0.10,0.22,0.05,1); m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=0.3; pad.data.materials.append(m)
b=bpy.data.objects['Qingyue_Body']
if b.data.shape_keys: b.data.shape_keys.key_blocks['smile'].value=0.6
rig=bpy.data.objects['Qingyue_Rig']; rig.animation_data_create(); rig.animation_data.action=bpy.data.actions['sit_hug']
try: rig.animation_data.action_slot=bpy.data.actions['sit_hug'].slots[0]   # Blender 5: actions need a slot
except Exception: pass
sc.frame_set(1)
cam=bpy.data.objects.new('Cam',bpy.data.cameras.new('Cam')); sc.collection.objects.link(cam); sc.camera=cam; cam.data.lens=70
for az in AZ:
    t=Vector((0.0,-0.05,0.47)); a=math.radians(az)
    cam.location=t+Vector((-math.sin(a)*3.3,-math.cos(a)*3.3,0.8))
    cam.rotation_mode='QUATERNION'; cam.rotation_quaternion=(t-cam.location).to_track_quat('-Z','Y')
    sc.render.filepath=OUT+'_az%d.png'%az; bpy.ops.render.render(write_still=True)
