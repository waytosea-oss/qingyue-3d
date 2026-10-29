import bpy,bmesh,numpy as np,sys,math
from mathutils import Vector,Matrix,Euler,Quaternion
sys.path.insert(0,'/Users/administrator/Tilo工作台/20261028-青跃三维/project/src'); import sdf
BUILD='/Users/administrator/Tilo工作台/20261028-青跃三维/project/build/'
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
def mesh_from(name,v,f):
    me=bpy.data.meshes.new(name); me.from_pydata(v.tolist(),[],f.tolist()); me.update()
    ob=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(ob); return ob
def activate(ob):
    for o in bpy.context.selected_objects: o.select_set(False)
    bpy.context.view_layer.objects.active=ob; ob.select_set(True)
def apply_mods(ob):
    activate(ob)
    for m in list(ob.modifiers): bpy.ops.object.modifier_apply(modifier=m.name)
def shade_smooth(ob):
    for p in ob.data.polygons: p.use_smooth=True
def verts_np(ob):
    a=np.zeros(len(ob.data.vertices)*3); ob.data.vertices.foreach_get('co',a); return a.reshape(-1,3)
