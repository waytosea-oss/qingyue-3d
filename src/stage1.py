exec(open('/Users/administrator/Tilo工作台/20261028-青跃三维/project/src/common.py').read())
reset()
D=np.load(BUILD+'mesh.npz')
parts=[]
for g,ratio in (('body',0.11),('armL',0.3),('armR',0.3)):
    ob=mesh_from(g,D[g+'_v'],D[g+'_f'])
    m=ob.modifiers.new('sm','SMOOTH'); m.factor=0.5; m.iterations=2
    m=ob.modifiers.new('dec','DECIMATE'); m.ratio=ratio
    apply_mods(ob); shade_smooth(ob); parts.append(ob); print(g,len(ob.data.polygons))
activate(parts[0]); [p.select_set(True) for p in parts]; bpy.ops.object.join()
body=bpy.context.active_object; body.name='Qingyue_Body'
# eyes
eyes=[]
for s,n in ((1,'L'),(-1,'R')):
    c=sdf.eye_c(s)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=40,ring_count=24,radius=sdf.EYE_R,location=c)
    e=bpy.context.active_object; e.name='Eye_'+n
    fwd=Vector((0.42*s,-0.88,0.12)).normalized()
    e.rotation_mode='QUATERNION'; e.rotation_quaternion=Vector((0,0,-1)).rotation_difference(fwd)
    shade_smooth(e); eyes.append(e)
bpy.ops.wm.save_as_mainfile(filepath=BUILD+'stage1.blend')
