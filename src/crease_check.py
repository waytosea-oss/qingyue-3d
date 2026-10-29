# v8: count sharp creases (dihedral > 50 deg) on the mouth interior, upper (roof) vs lower (floor), rest pose and jaw 22 deg
# blender -b --python crease_check.py -- <blend>
exec(open('/Users/administrator/Tilo工作台/20261028-青跃三维/project/src/common.py').read())
args=sys.argv[sys.argv.index('--')+1:]; bpy.ops.wm.open_mainfile(filepath=args[0])
rig=bpy.data.objects['Qingyue_Rig']; body=bpy.data.objects['Qingyue_Body']; rig.animation_data.action=None
for tr in rig.animation_data.nla_tracks: tr.mute=True
for k in body.data.shape_keys.key_blocks[1:]: k.value=0
VD=np.load(BUILD+'verts.npz'); V0=VD['V0']; raw=VD['raw']
inmouth=(sdf.mouth_vol(V0)<0.0)&(raw<-0.002)
zl=sdf.zm(V0[:,0],V0[:,1]); upper=V0[:,2]>zl
def creases(deg):
    rig.pose.bones['jaw'].rotation_mode='QUATERNION'; rig.pose.bones['jaw'].rotation_quaternion=Quaternion(Vector((1,0,0)),math.radians(-deg)); bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get(); oe=body.evaluated_get(dg); m=oe.to_mesh()
    bm=bmesh.new(); bm.from_mesh(m); oe.to_mesh_clear(); bm.edges.ensure_lookup_table(); bm.normal_update()
    out={'roof':[],'floor':[]}
    for e in bm.edges:
        if len(e.link_faces)!=2: continue
        a,b=e.verts[0].index,e.verts[1].index
        if not(inmouth[a] and inmouth[b]): continue
        ang=math.degrees(e.link_faces[0].normal.angle(e.link_faces[1].normal))
        if ang>50: out['roof' if upper[a] and upper[b] else 'floor'].append(((e.verts[0].co+e.verts[1].co)/2)[:])
    bm.free(); return out
for deg in (0,22):
    o=creases(deg); print('CREASE jaw %2d deg: roof sharp edges %d, floor sharp edges %d'%(deg,len(o['roof']),len(o['floor'])))
    if o['roof']: R=np.array(o['roof']); print('   roof crease z range %.3f..%.3f, mean dist below/above lip line'%(R[:,2].min(),R[:,2].max()))
