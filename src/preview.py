exec(open('/Users/administrator/Tilo工作台/20261028-青跃三维/project/src/common.py').read())
import os
out=sys.argv[sys.argv.index('--')+1]
sc=bpy.context.scene
sc.render.engine='CYCLES'; sc.cycles.samples=24; sc.cycles.device='CPU'
sc.render.resolution_x=640; sc.render.resolution_y=640
if not sc.world: sc.world=bpy.data.worlds.new('w')
sc.world.use_nodes=True; sc.world.node_tree.nodes['Background'].inputs[0].default_value=(0.8,0.85,0.8,1); sc.world.node_tree.nodes['Background'].inputs[1].default_value=0.6
if not any(o.type=='LIGHT' for o in sc.objects):
    L=bpy.data.lights.new('sun','SUN'); L.energy=3.5; lo=bpy.data.objects.new('sun',L); sc.collection.objects.link(lo); lo.rotation_euler=(math.radians(50),0,math.radians(-30))
for o in sc.objects:
    if o.type=='MESH' and not o.data.materials:
        m=bpy.data.materials.new('pv'); m.diffuse_color=(0.4,0.6,0.2,1); o.data.materials.append(m)
        m.use_nodes=True; m.node_tree.nodes['Principled BSDF'].inputs[0].default_value=(0.35,0.55,0.15,1) if 'Eye' not in o.name else (0.02,0.01,0.005,1)
cam=bpy.data.objects.get('PCam')
if not cam:
    cam=bpy.data.objects.new('PCam',bpy.data.cameras.new('PCam')); sc.collection.objects.link(cam)
sc.camera=cam; cam.data.lens=60
for tag,az,el in [('front',0,8),('q34',-35,12),('side',-90,5)]:
    a=math.radians(az); r=3.3; t=Vector((0,-0.05,0.5))
    cam.location=t+Vector((math.sin(a)*r*-1*-1, -math.cos(a)*r, math.tan(math.radians(el))*r))
    cam.location=t+Vector((-math.sin(a)*r,-math.cos(a)*r,math.tan(math.radians(el))*r))
    cam.rotation_mode='QUATERNION'; cam.rotation_quaternion=(t-cam.location).to_track_quat('-Z','Y')
    sc.render.filepath=out+'_'+tag+'.png'; bpy.ops.render.render(write_still=True)
