# Stage 2: geometry assembly, UVs, masks, bake position/normal/mask/AO -> npy
exec(open('/Users/administrator/Tilo工作台/20261028-青跃三维/project/src/common.py').read())
reset()
D=np.load(BUILD+'mesh.npz')
parts=[]
S_=lambda t:np.clip(t,0,1)**2*(3-2*np.clip(t,0,1))
for g,ratio in (('body',0.15),('armL',0.16),('armR',0.16)):
    ob=mesh_from(g,D[g+'_v'],D[g+'_f'])
    m=ob.modifiers.new('sm','SMOOTH'); m.factor=0.5; m.iterations=2
    m=ob.modifiers.new('dec','DECIMATE'); m.ratio=ratio
    if g=='body':   # keep density on lips / mouth cavity / eye sockets / toes
        Vg=D[g+'_v']; zl=sdf.zm(Vg[:,0],Vg[:,1])
        w=S_((0.05-sdf.mouth_vol(Vg))/0.05)*S_((0.09-np.abs(Vg[:,2]-zl))/0.05)
        for sx in (1,-1): w=np.maximum(w,S_((sdf.EYE_R+0.04-np.linalg.norm(Vg-sdf.eye_c(sx),axis=-1))/0.03)*0.8)
        w=np.maximum(w,S_((0.06-Vg[:,2])/0.03)*0.6)
        vg=ob.vertex_groups.new(name='protect')
        for lvl in (0.25,0.5,0.75,1.0):
            idx=np.nonzero((w>lvl-0.25)&(w<=lvl)&(w>0.01))[0].tolist()
            if idx: vg.add(idx,lvl,'REPLACE')
        pass   # (vertex-group weighted collapse over-decimates everything else; uniform decimation is used)
    apply_mods(ob); shade_smooth(ob); parts.append(ob)
nv_parts=[len(p.data.vertices) for p in parts]
activate(parts[0]); [p.select_set(True) for p in parts]; bpy.ops.object.join()
body=bpy.context.active_object; body.name='Qingyue_Body'; body.data.name='Qingyue_Body'
body.data.validate()
print('body tris',sum(len(p.vertices)-2 for p in body.data.polygons))
import bmesh as _bm
_b=_bm.new(); _b.from_mesh(body.data); _open=sum(1 for e in _b.edges if e.is_boundary); _b.free()
print('WATERTIGHT check: boundary edges =',_open); assert _open==0,'mesh has holes'
activate(body); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(60),island_margin=0.012,area_weight=0.0)
# v8: smart_project left islands packed edge-to-edge (no real gutter) -> texture filtering blended cream with the
#     neighbouring island's green along every UV seam = thin jagged 'cracks' on the cream jaw. Repack with a hard gap.
bpy.ops.uv.select_all(action='SELECT')
bpy.ops.uv.pack_islands(rotate=True,margin_method='FRACTION',margin=0.008,shape_method='CONCAVE')
bpy.ops.object.mode_set(mode='OBJECT')
V0=verts_np(body)
raw0=sdf.body_raw(V0,'body')
grp0=np.repeat(np.arange(3),nv_parts)   # island of origin: 0 body, 1 armL, 2 armR (join keeps active first)
V=V0.copy(); V[grp0==0]=sdf.lip_close(V0[grp0==0],raw0[grp0==0])
body.data.vertices.foreach_set('co',V.ravel()); body.data.update()
N=np.zeros(len(V)*3); body.data.vertices.foreach_get('normal',N); N=N.reshape(-1,3)
grp=grp0
dl=np.stack([sdf.prim_d(V,pr) for pr in sdf.P],-1)
for gi,g in enumerate(('body','armL','armR')):
    bad=np.array([pr[0]!=g for pr in sdf.P]); dl[np.ix_(grp==gi,bad)]=9
lab=dl.argmin(-1); bones_of=np.array([pr[1] for pr in sdf.P]); vb=bones_of[lab]
S=lambda t:np.clip(t,0,1)**2*(3-2*np.clip(t,0,1))
x,y,z=V.T
is_torso=np.isin(vb,['TORSO','hips','chest'])
is_head=vb=='head'
# v8: in the tight hug the knees sit right under the chin, so some chin vertices are LABELLED 'thigh' by the nearest
#     primitive -> the cream jaw/throat masks skipped them -> thin jagged green 'cracks'. Decide geometrically instead.
_legd=np.min([sdf.cone(V0,*pr[3]) for pr in sdf.P if pr[0]=='body' and pr[1].startswith(('thigh','shin','foot')) and pr[2]=='cone'],axis=0)
not_leg=(grp==0)&(_legd>0.012)
zmv=sdf.zm(x,y)
belly=is_torso*S((-N[:,1]-0.05)/0.45)*S((0.66+sdf.HZ-z)/0.06)*S((0.27-np.abs(x))/0.1)
z0=V0[:,2]
chin=not_leg*S((zmv-z0-0.003)/0.012)*S((0.12-y)/0.10)*S((0.40-np.abs(x))/0.06)
belly=np.maximum(belly,chin)
throat=not_leg*S((-N[:,1]-0.1)/0.3)*S((zmv-z0)/0.01)*S((0.32-np.abs(x))/0.06)*S((z0-0.30)/0.05)
belly=np.maximum(belly,throat)   # v5: chin cream and belly cream join without a green seam
belly=np.maximum(belly,np.char.startswith(vb.astype(str),'thigh')*S((-np.sign(x)*N[:,0]-0.2)/0.5)*S((-N[:,2]+0.3)/0.6)*0.55)
raw=raw0
mouth=(grp==0)*S((-raw-0.0025)/0.004)*(sdf.mouth_vol(V0)<0.05)*(np.abs(V0[:,2]-zmv)<0.07)
tongue=mouth*S((1.05-np.linalg.norm((V0-np.array(sdf.TONGUE[0]))/np.array(sdf.TONGUE[1]),axis=-1))/0.3)
tymp=np.zeros(len(V))
for s in (1,-1):
    dd=np.linalg.norm(V-sdf.TYMP(s),axis=-1); tymp=np.maximum(tymp,(grp==0)*S((0.066-dd)/0.01))
tips=np.zeros(len(V))
for i,pr in enumerate(sdf.P):
    if pr[2]=='sph' and (pr[1].startswith('toe') or pr[1].startswith('finger')):
        tips=np.maximum(tips,S((0.028-np.linalg.norm(V-np.array(pr[3][0]),axis=-1))/0.012))
facefront=is_head*S((-N[:,1]-0.4)/0.4)*S((0.84+sdf.HZ-z)/0.06)*S((0.24-np.abs(x))/0.08)
np.savez(BUILD+'verts.npz',V=V,V0=V0,raw=raw0,tongue=tongue,N=N,belly=belly,mouth=mouth,tymp=tymp,tips=tips,face=facefront,grp=grp,vb=vb.astype(str),dl=dl)
col=body.data.color_attributes.new('masks','FLOAT_COLOR','POINT')
col.data.foreach_set('color',np.stack([belly,mouth,tymp,tips],-1).astype(np.float32).ravel())
sc=bpy.context.scene; sc.render.engine='CYCLES'; sc.cycles.device='CPU'
mat=bpy.data.materials.new('bake'); mat.use_nodes=True; body.data.materials.append(mat)
nt=mat.node_tree; nt.nodes.clear()
out=nt.nodes.new('ShaderNodeOutputMaterial'); em=nt.nodes.new('ShaderNodeEmission')
nt.links.new(em.outputs[0],out.inputs[0])
img_node=nt.nodes.new('ShaderNodeTexImage'); nt.nodes.active=img_node
geo=nt.nodes.new('ShaderNodeNewGeometry'); attr=nt.nodes.new('ShaderNodeAttribute'); attr.attribute_name='masks'
RES=2048
def bake(name,socket,typ='EMIT',samples=1):
    im=bpy.data.images.new(name,RES,RES,float_buffer=True,alpha=True); im.generated_color=(0,0,0,0)
    img_node.image=im
    if socket is not None: nt.links.new(socket,em.inputs[0])
    sc.cycles.samples=samples
    activate(body); bpy.ops.object.bake(type=typ,margin=0,use_clear=True)
    a=np.array(im.pixels[:],dtype=np.float32).reshape(RES,RES,4); np.save(BUILD+'bake_%s.npy'%name,a); print('baked',name)
bake('pos',geo.outputs['Position']); bake('nrm',geo.outputs['Normal']); bake('mask',attr.outputs['Color'])
c0=body.data.color_attributes.new('pos0','FLOAT_COLOR','POINT')   # pre-lip-close positions -> exact per-texel mouth SDF
c0.data.foreach_set('color',np.concatenate([V0,np.ones((len(V0),1))],1).astype(np.float32).ravel())
attr.attribute_name='pos0'; bake('pos0',attr.outputs['Color']); attr.attribute_name='masks'
for s,n in ((1,'L'),(-1,'R')):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=16,radius=sdf.EYE_R,location=sdf.eye_c(s))
nt.links.new(nt.nodes.new('ShaderNodeBsdfDiffuse').outputs[0],out.inputs[0])
sc.cycles.samples=48
im=bpy.data.images.new('ao',RES,RES,float_buffer=True); img_node.image=im; nt.nodes.active=img_node
activate(body); bpy.ops.object.bake(type='AO',margin=0)
np.save(BUILD+'bake_ao.npy',np.array(im.pixels[:],dtype=np.float32).reshape(RES,RES,4))
for o in list(bpy.data.objects):
    if o.name.startswith('Sphere'): bpy.data.objects.remove(o)
body.data.materials.clear()
# v6: the marching-cubes faces were wound inward since v1 (hidden by double-sided materials, but wrong for
#     3ds Max/FBX and for anything offset along the normal). Flip them now - after the bakes/masks, so colours don't change.
import bmesh as _bm2
_b=_bm2.new(); _b.from_mesh(body.data); _bm2.ops.reverse_faces(_b,faces=_b.faces[:]); _b.to_mesh(body.data); _b.free(); body.data.update()
_N=np.zeros(len(body.data.vertices)*3); body.data.vertices.foreach_get('normal',_N); _N=_N.reshape(-1,3)
_i=np.nonzero(grp==0)[0][::50]; print('NORMALS outward fraction after flip: %.3f'%(sdf.sdf(V[_i]+_N[_i]*0.005)>sdf.sdf(V[_i])).mean())
bpy.ops.wm.save_as_mainfile(filepath=BUILD+'stage2.blend')
print('STAGE2 OK')
