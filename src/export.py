exec(open('/Users/administrator/Tilo工作台/20261028-青跃三维/project/src/common.py').read())
import os,shutil
bpy.ops.wm.open_mainfile(filepath=BUILD+'stage4.blend')
OUT='/Users/administrator/Tilo工作台/20261028-青跃三维/project/'
rig=bpy.data.objects['Qingyue_Rig']; rig.animation_data.action=None
for pb in rig.pose.bones:   # save the .blend in the clean rest pose
    pb.rotation_mode='QUATERNION'; pb.rotation_quaternion=(1,0,0,0); pb.location=(0,0,0); pb.scale=(1,1,1)
for ob in bpy.data.objects:
    if ob.type=='MESH' and ob.data.shape_keys:
        for k in ob.data.shape_keys.key_blocks[1:]: k.value=0.0
bpy.context.view_layer.update()
for tr in rig.animation_data.nla_tracks: tr.mute=True
b=bpy.data.objects['Qingyue_Body']
for a in list(b.data.color_attributes): b.data.color_attributes.remove(a)
b.data.validate()
bpy.ops.wm.save_as_mainfile(filepath=OUT+'qingyue.blend')
bpy.ops.export_scene.gltf(filepath=OUT+'qingyue.glb',export_format='GLB',export_animation_mode='ACTIONS',export_morph=True,export_skins=True,
    export_image_format='JPEG',export_jpeg_quality=90,export_image_quality=90,export_force_sampling=True,export_optimize_animation_size=False,export_yup=True,export_apply=False,export_def_bones=False)
os.makedirs(OUT+'fbx',exist_ok=True)
bpy.ops.export_scene.fbx(filepath=OUT+'fbx/qingyue.fbx',object_types={'ARMATURE','MESH'},add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=True,
    bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,path_mode='COPY',embed_textures=False,mesh_smooth_type='FACE',use_mesh_modifiers=False,
    armature_nodetype='NULL')
print('EXPORT OK')
