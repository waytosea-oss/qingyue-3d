exec(open('/Users/administrator/Tilo工作台/20261028-青跃三维/project/src/common.py').read())
import subprocess
bpy.ops.wm.open_mainfile(filepath=BUILD+'stage2.blend')
body=bpy.data.objects['Qingyue_Body']
TEX='/Users/administrator/Tilo工作台/20261028-青跃三维/project/textures/'
S=lambda t:np.clip(t,0,1)**2*(3-2*np.clip(t,0,1))
def principled(name):
    m=bpy.data.materials.new(name); m.use_nodes=True; return m,m.node_tree.nodes['Principled BSDF'],m.node_tree
def teximg(nt,path,noncolor=False):
    n=nt.nodes.new('ShaderNodeTexImage'); n.image=bpy.data.images.load(path)
    if noncolor: n.image.colorspace_settings.name='Non-Color'
    return n
# ---------- skin material
skin,bs,nt=principled('Qingyue_Skin')
t=teximg(nt,TEX+'qingyue_basecolor.png'); nt.links.new(t.outputs[0],bs.inputs['Base Color'])
r=teximg(nt,TEX+'qingyue_roughness.png',True); nt.links.new(r.outputs[0],bs.inputs['Roughness'])
n=teximg(nt,TEX+'qingyue_normal.png',True); nm=nt.nodes.new('ShaderNodeNormalMap'); nm.inputs[0].default_value=0.05
nt.links.new(n.outputs[0],nm.inputs[1]); nt.links.new(nm.outputs[0],bs.inputs['Normal'])
bs.inputs['Coat Weight'].default_value=0.35; bs.inputs['Coat Roughness'].default_value=0.12
bs.inputs['Specular IOR Level'].default_value=0.55
bs.inputs['Subsurface Weight'].default_value=0.0
body.data.materials.append(skin)
# ---------- eyes
ER=sdf.EYE_R
def eye_fwd(s): return Vector((0.55*s,-0.81,0.17)).normalized()
RES=512; v=np.linspace(0,1,RES)[:,None]; u=np.linspace(0,1,RES)[None,:]
th=v*180  # 0 at front pole (bottom pole mapped to front)
rng=np.random.default_rng(3); streak=np.zeros((1,RES))
for k in range(1,40): streak+=np.sin(u*2*np.pi*k*3+rng.uniform(0,6))*rng.uniform(0,1)/k**0.3
streak=streak/np.abs(streak).max()
# big glossy eye: black pupil, warm amber iris (brown inside -> golden rim), dark limbal ring
iris_r=54; pupil_r=33
dark=np.array([0.018,0.011,0.007]); inner=np.array([0.16,0.075,0.018]); amber=np.array([0.52,0.27,0.05]); gold=np.array([0.62,0.40,0.10])
t_=np.clip((th-pupil_r)/(iris_r-pupil_r),0,1)[...,None]
irisc=(inner*(1-S(t_/0.55))+amber*S(t_/0.55))*(1-S((t_-0.6)/0.4))+gold*S((t_-0.6)/0.4)
irisc=irisc*(0.78+0.32*streak[...,None])
pr=S((th-pupil_r)/1.5)[...,None]
c=np.where((th<iris_r)[...,None],np.array([0.008,0.006,0.005])*(1-pr)+irisc*pr,dark)
ring=S(1-np.abs(th-iris_r)/3.5)[...,None]; c=c*(1-ring)+np.array([0.035,0.02,0.008])*ring
im=bpy.data.images.new('Qingyue_Eye',RES,RES); im.pixels[:]=np.concatenate([c**(1/2.2),np.ones((RES,RES,1))],-1).astype(np.float32).ravel()
im.filepath_raw=TEX+'qingyue_eye.png'; im.file_format='PNG'; im.save()
eyem,be,ent=principled('Qingyue_Eye'); te=ent.nodes.new('ShaderNodeTexImage'); te.image=im
ent.links.new(te.outputs[0],be.inputs['Base Color']); be.inputs['Roughness'].default_value=0.12
be.inputs['Coat Weight'].default_value=1.0; be.inputs['Coat Roughness'].default_value=0.02
be.inputs['Specular IOR Level'].default_value=0.8
eyes={}
for s,nme in ((1,'L'),(-1,'R')):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=32,radius=ER,location=sdf.eye_c(s))
    e=bpy.context.active_object; e.name='Qingyue_Eye_'+nme; e.data.name=e.name
    e.rotation_mode='QUATERNION'; e.rotation_quaternion=Vector((0,0,-1)).rotation_difference(eye_fwd(s))
    activate(e); bpy.ops.object.transform_apply(location=False,rotation=True,scale=False)
    shade_smooth(e); e.data.materials.append(eyem); eyes[nme]=e
# ---------- lids (skin coloured, darker olive rim, UV = angle from lid pole)
LRES=256; vv=np.linspace(0,1,LRES)[:,None]*np.ones((1,64))
srgbv=lambda c:(np.array(c)/255.)**2.2
lc=srgbv([166,194,72])[None,None]*(1-S((vv-0.35)/0.5)[...,None])+srgbv([136,166,56])[None,None]*S((vv-0.35)/0.5)[...,None]
rim=S((vv-0.86)/0.08)[...,None]; lc=lc*(1-rim)+srgbv([66,88,38])[None,None]*rim
spt=np.zeros_like(vv)
for (cu,cv,cr) in ((0.15,0.30,0.06),(0.55,0.22,0.05),(0.80,0.42,0.045)):
    uu=np.linspace(0,1,64)[None,:]*np.ones((LRES,1)); spt=np.maximum(spt,S((cr-np.hypot((uu-cu)*0.9,(vv-cv)*0.5))/0.02))
lc=lc*(1-0.6*spt[...,None])+srgbv([92,120,52])[None,None]*0.6*spt[...,None]
lim=bpy.data.images.new('Qingyue_LidTex',64,LRES); lim.pixels[:]=np.concatenate([lc**(1/2.2),np.ones((LRES,64,1))],-1).astype(np.float32).ravel()
lim.filepath_raw=TEX+'qingyue_lid.png'; lim.file_format='PNG'; lim.save()
lidm,bl,lnt=principled('Qingyue_Lid'); lt=lnt.nodes.new('ShaderNodeTexImage'); lt.image=lim; lt.extension='EXTEND'
lnt.links.new(lt.outputs[0],bl.inputs['Base Color'])
bl.inputs['Roughness'].default_value=0.45; bl.inputs['Coat Weight'].default_value=0.3; bl.inputs['Coat Roughness'].default_value=0.15
LID={}
LIDANG=100   # >hemisphere: the closed lid also covers the top/back of the eyeball
for s_,nme in ((1,'L'),(-1,'R')):
    c=Vector(sdf.eye_c(s_)); f=eye_fwd(s_); up=(Vector((0,0,1))-f*f.z).normalized()
    a_open=(Quaternion(f.cross(up).normalized(),math.radians(4+LIDANG-66))@up).normalized()  # slight back tilt: lid covers the top ~22% of the eye
    axis=a_open.cross(f).normalized()
    bm=bmesh.new(); bmesh.ops.create_uvsphere(bm,u_segments=48,v_segments=32,radius=ER*1.03)
    rot=Vector((0,0,1)).rotation_difference(a_open)
    bmesh.ops.rotate(bm,verts=bm.verts,cent=(0,0,0),matrix=rot.to_matrix())
    kill=[vv_ for vv_ in bm.verts if vv_.co.normalized().dot(a_open)<math.cos(math.radians(LIDANG))]
    bmesh.ops.delete(bm,geom=kill,context='VERTS')
    uvl=bm.loops.layers.uv.new('UVMap')
    ref=(f-a_open*f.dot(a_open)).normalized(); ref2=a_open.cross(ref)
    for fc in bm.faces:
        for lp in fc.loops:
            q=lp.vert.co.normalized(); ang=math.degrees(math.acos(max(-1,min(1,q.dot(a_open)))))
            az=math.atan2(q.dot(ref2),q.dot(ref))/(2*math.pi)+0.5
            lp[uvl].uv=(az,min(1,ang/LIDANG))
    bmesh.ops.translate(bm,verts=bm.verts,vec=c)
    me=bpy.data.meshes.new('Qingyue_Lid_'+nme); bm.to_mesh(me); ob=bpy.data.objects.new(me.name,me); bpy.context.collection.objects.link(ob)
    so=ob.modifiers.new('so','SOLIDIFY'); so.thickness=0.005; so.offset=1
    sub=ob.modifiers.new('sub','SUBSURF'); sub.levels=1
    apply_mods(ob); shade_smooth(ob); me.materials.append(lidm)
    LID[nme]=dict(ob=ob,c=c,axis=axis,a=a_open,f=f)
BLINK=112
# ---------- crown: fine gold vine circlet, tilted toward the viewer's right (+X)
gold,bg,_=principled('Qingyue_Crown_Gold'); bg.inputs['Base Color'].default_value=(0.86,0.62,0.26,1); bg.inputs['Metallic'].default_value=1; bg.inputs['Roughness'].default_value=0.22
leafm,bf,_=principled('Qingyue_Crown_Leaf'); bf.inputs['Base Color'].default_value=(0.80,0.68,0.32,1); bf.inputs['Metallic'].default_value=0.75; bf.inputs['Roughness'].default_value=0.3
dew,bd,_=principled('Qingyue_Dew'); bd.inputs['Base Color'].default_value=(0.92,0.98,1,1); bd.inputs['Transmission Weight'].default_value=1; bd.inputs['Roughness'].default_value=0.02; bd.inputs['IOR'].default_value=1.33
# v5 crown: worn slanted on the head's right (+X) side; thick twisted 3-strand vine bundle hugging the skin,
#     leaves of varied size/orientation, gold buds, 2 tendrils hanging down the side, dew drops.
# v6 crown: ~1.5x bigger and moved FORWARD. Instead of a tilted circle (which would have to climb over the
#     big eye domes), the circlet follows a designed closed path on the head: across the forehead/brow ridge
#     between the eyes, over the inner-back of the right eye dome, down behind the right eye (slanted),
#     round the back, high on the left. Every point keeps >=17 mm from the eyelid sphere (lids rotate on that
#     sphere, so blinking can never touch it).
CPATH=np.array([[0.0,-0.18,0.94],[0.115,-0.14,0.99],[0.225,-0.045,1.0],[0.31,0.03,0.88],[0.28,0.13,0.80],
                [0.12,0.21,0.88],[-0.05,0.18,0.95],[-0.16,0.04,1.0],[-0.12,-0.11,0.99]])+np.array([0,0,sdf.HZ])
def _cat(u):
    m=len(CPATH); x=(u%1.0)*m; i=int(x)%m; t=x-int(x)
    p0,p1,p2,p3=CPATH[i-1],CPATH[i],CPATH[(i+1)%m],CPATH[(i+2)%m]
    return 0.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t**3)
CC=CPATH.mean(0); CR=0.0
cn=Vector((0.18,0.05,1.0)).normalized()            # mean 'up' of the slanted circlet (crown bone axis)
VR=[0.0063,0.0051,0.0045]; TW=0.0078               # v6: ~1.5x thicker strands and twist
LIFT=TW+max(VR)+0.0008                             # bundle rests ON the skin (no float, no intersection)
LIDR=sdf.EYE_R*1.03+0.005                          # eyelid shell radius (open or closed, lids stay on this sphere)
def surf_n(p):
    n=np.array([sdf.body_raw(p[None]+np.eye(3)[i]*1e-3)[0] for i in range(3)])-sdf.body_raw(p[None])[0]; return n/np.linalg.norm(n)
def avoid_eyes(p,clear):
    for sx in (1,-1):
        c=sdf.eye_c(sx); v=p-c; d=np.linalg.norm(v); R=LIDR+0.003+clear
        if d<R: p=c+v/d*R
    return p
def on_skin(p,lift):
    p=sdf.project(np.array(p)[None],lambda q:sdf.body_raw(q))[0]
    q=avoid_eyes(p+surf_n(p)*lift,lift)
    for _ in range(4):   # concave spots: push out until the whole bundle clears the skin (true distance >= lift)
        dfi=sdf.sdf(q[None])[0]
        if dfi>=lift-0.0003: break
        q=q+surf_n(q)*(lift-dfi)
    return q
def ring_pt(t,rad=None,lift=0.0):
    return on_skin(_cat(t/(2*np.pi)),LIFT+lift)
crown_objs=[]
def curve_obj(pts,rad,name,mat,taper=False,cyclic=False,radii=None):
    cu=bpy.data.curves.new(name,'CURVE'); cu.dimensions='3D'; cu.bevel_depth=rad; cu.bevel_resolution=3
    sp=cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts)-1); sp.use_cyclic_u=cyclic
    for i,p in enumerate(pts):
        bp=sp.bezier_points[i]; bp.co=p; bp.handle_left_type='AUTO'; bp.handle_right_type='AUTO'
        if taper: bp.radius=1-0.8*i/max(1,len(pts)-1)
        if radii is not None: bp.radius=radii[i]
    ob=bpy.data.objects.new(name,cu); bpy.context.collection.objects.link(ob); cu.materials.append(mat)
    cu.resolution_u=5; crown_objs.append(ob); return ob
T=np.linspace(0,2*np.pi,97)[:-1]
base=[ring_pt(t) for t in T]
rng=np.random.default_rng(23)
for k,ph in enumerate((0,2*np.pi/3,4*np.pi/3)):     # clearly twisted & braided, with slight thickness swelling
    pts=[];rad=[]
    for i,t in enumerate(T):
        p=base[i]; tang=base[(i+1)%len(T)]-base[i-1]; tang/=np.linalg.norm(tang)
        nn=surf_n(p); side=np.cross(tang,nn); side/=np.linalg.norm(side)
        a=t*7+ph; pts.append(p+side*TW*math.cos(a)+nn*TW*math.sin(a)); rad.append(0.85+0.3*(0.5+0.5*math.sin(t*5+k)))
    curve_obj(pts,VR[k],'crown_vine%d'%k,gold,cyclic=True,radii=rad)
def leaf(p,dirv,normal,size,mat,fold=0.12,curl=0.18):
    """pointed leaf with midrib fold and tip curl (local x=width, y=length, z=normal)"""
    bm=bmesh.new(); n=10; rows=[]
    for i in range(n+1):
        t=i/n; w=(math.sin(math.pi*min(1,t*1.08))**1.1)*0.30*size; y=t*size; c=curl*size*t*t
        rows.append([bm.verts.new((-w,y,c+fold*w)),bm.verts.new((0,y,c)),bm.verts.new((w,y,c+fold*w))])
    for i in range(n):
        a_,b_=rows[i],rows[i+1]; bm.faces.new((a_[0],a_[1],b_[1],b_[0])); bm.faces.new((a_[1],a_[2],b_[2],b_[1]))
    me=bpy.data.meshes.new('leaf'); bm.to_mesh(me); ob=bpy.data.objects.new('crown_leaf',me); bpy.context.collection.objects.link(ob)
    so=ob.modifiers.new('s','SOLIDIFY'); so.thickness=0.0012; so.offset=0
    Y=Vector(dirv).normalized(); Z=Vector(normal); Z=(Z-Y*Z.dot(Y)).normalized(); X=Y.cross(Z)
    ob.matrix_world=Matrix.Translation(Vector(p))@Matrix((X,Y,Z)).transposed().to_4x4()
    me.materials.append(mat); shade_smooth(ob); crown_objs.append(ob); return ob
def rot(v,ax,ang):
    ax=ax/np.linalg.norm(ax); return v*math.cos(ang)+np.cross(ax,v)*math.sin(ang)+ax*np.dot(ax,v)*(1-math.cos(ang))
# leaves: 26, sizes 1.8-6 cm, each with its own lean/twist; denser on the visible front/right
leaf_ts=np.sort(np.concatenate([np.linspace(-2.8,2.2,20),rng.uniform(2.4,3.6,6)]))+rng.uniform(-0.06,0.06,26)
for i,t in enumerate(leaf_ts):
    p=ring_pt(t,lift=0.001); nn=surf_n(p)
    tang=ring_pt(t+0.05)-ring_pt(t-0.05); tang/=np.linalg.norm(tang); outv=np.cross(tang,nn)
    if np.dot(outv,p-CC)<0: outv=-outv
    sgn=1 if i%2 else -1
    d=tang*sgn*rng.uniform(0.2,0.7)+nn*rng.uniform(0.5,1.0)+outv*rng.uniform(0.0,0.5); d/=np.linalg.norm(d)
    d=rot(d,tang,rng.uniform(-0.5,0.5))
    nrm=rot(outv*0.8+nn*0.2,d,rng.uniform(-0.9,0.9))
    size=rng.choice([rng.uniform(0.026,0.042),rng.uniform(0.042,0.062),rng.uniform(0.062,0.082)],p=[0.4,0.4,0.2])   # v6: ~1.4x
    leaf(p,d,nrm,size,leafm if i%3 else gold,fold=rng.uniform(0.05,0.2),curl=rng.uniform(0.05,0.3))
# gold buds (small elongated drops on short stems)
for t in np.linspace(-2.5,2.0,9)+0.17:
    p=ring_pt(t,lift=0.003); nn=surf_n(p)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=14,ring_count=10,radius=0.0082,location=p+nn*0.006)
    bb=bpy.context.active_object; bb.scale=(1,1,1.35); bb.rotation_mode='QUATERNION'; bb.rotation_quaternion=Vector((0,0,1)).rotation_difference(Vector(nn))
    bb.data.materials.append(gold); shade_smooth(bb); crown_objs.append(bb)
# short upright filigree curls on top
def tendril(p,d,outv,turns=2.2,L=0.05):
    tp=[np.array(p)]; dd=np.array(d,float); ax=np.cross(dd,outv); ax/=np.linalg.norm(ax)+1e-9; n=26
    for j in range(n):
        ang=turns*2*np.pi/n*(0.4+1.2*j/n); c_,s_=math.cos(ang),math.sin(ang)
        dd=dd*c_+np.cross(ax,dd)*s_+ax*np.dot(ax,dd)*(1-c_); dd/=np.linalg.norm(dd)
        tp.append(tp[-1]+dd*L/n*(1.25-0.9*j/n))
    curve_obj(tp,0.0025,'tendril',gold,taper=True)
for t,turn in ((-2.0,1.8),(-0.9,1.6),(0.3,1.9),(1.4,1.7),(2.9,1.6)):
    p=ring_pt(t); nn=surf_n(p); outv=p-CC; outv/=np.linalg.norm(outv)
    d=outv*0.3+nn*1.0; d/=np.linalg.norm(d); tendril(p,d,outv,turn,0.10)
# two tendrils hanging DOWN the side of the head (follow the skin, then curl at the end)
lowest=T[np.argmin([b_[2] for b_ in base])]
for k,dt in enumerate((-0.25,0.2)):
    p=ring_pt(lowest+dt); path=[p]; L=[0.15,0.12][k]; n=16
    for j in range(n):
        nn=surf_n(path[-1]); down=np.array([0,0,-1.0])-nn*np.dot([0,0,-1.0],nn); down/=np.linalg.norm(down)
        drift=np.array([0,0.35 if k else -0.35,0]); drift-=nn*np.dot(drift,nn)
        q=path[-1]+(down+drift)/np.linalg.norm(down+drift)*L/n
        path.append(on_skin(q,0.0045))
    # end curl lifting off the skin
    nn=surf_n(path[-1]); dd=(path[-1]-path[-2]); dd-=nn*np.dot(dd,nn); dd/=np.linalg.norm(dd)
    for j in range(12):   # curl lies flat over the skin (rotation about the skin normal) and rises slightly off it
        dd=rot(dd,nn,0.55*(1 if k else -1)); path.append(path[-1]+dd*0.0075*(1-j/16)+nn*0.0012)
    curve_obj(path,0.0028,'tendril_hang%d'%k,gold,taper=True)
# dew: one clear drop resting on the bundle above the right eye + one tiny bead
p=ring_pt(0.95,lift=0.013)
bpy.ops.mesh.primitive_uv_sphere_add(segments=28,ring_count=18,radius=0.015,location=p)
d=bpy.context.active_object; d.scale=(1,1,0.92); d.data.materials.append(dew); shade_smooth(d); crown_objs.append(d)
bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=10,radius=0.0065,location=ring_pt(4.4,lift=0.008)); d2=bpy.context.active_object; d2.data.materials.append(dew); shade_smooth(d2); crown_objs.append(d2)
# verification: closest approach of the vine bundle to the skin and to the eye/lid shells
_chk=np.array([ring_pt(t) for t in np.linspace(0,2*np.pi,240)])
print('CROWN skin gap (bundle centre - skin): min %.4f max %.4f  | eye clearance min %.4f'%(
    sdf.body_raw(_chk).min(),sdf.body_raw(_chk).max(),min(np.linalg.norm(_chk-sdf.eye_c(sx),axis=1).min()-LIDR for sx in (1,-1))))
for o in crown_objs:
    if o.type=='CURVE':
        activate(o); bpy.ops.object.convert(target='MESH')
for o in crown_objs:
    if o.modifiers: apply_mods(o)
for o in crown_objs: o.select_set(True)
bpy.context.view_layer.objects.active=crown_objs[0]; bpy.ops.object.join()
crown=bpy.context.active_object; crown.name='Qingyue_Crown'; crown.data.name='Qingyue_Crown'
activate(crown); bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
shade_smooth(crown)
print('crown tris',sum(len(p.vertices)-2 for p in crown.data.polygons))
# ---------- v8 vocal sac: a real inflatable balloon under the chin (about head width when full)
#   modelled DEFLATED (6% scale, hidden inside the throat) so the rest/FBX pose is clean; its own bone 'vsac' scales it up.
SAC_C=np.array([0,-0.43,0.425]); SAC_R=np.array([0.33,0.14,0.125]); SAC_S0=0.06   # v8c: centred on the throat midline UNDER the chin (was in front of the mouth); SAC_S0=0.06
_P=sdf.project(np.array([[0,-0.30,0.44]]),sdf.sdf)[0]; _n=np.array([sdf.sdf(_P[None]+np.eye(3)[i]*1e-3)[0] for i in range(3)])-sdf.sdf(_P[None])[0]; _n/=np.linalg.norm(_n)
SAC_A=np.array([0,-0.08,0.37])                     # anchor deep in throat/chest flesh, outside the jaw-weighted zone (searched: deflated sac >=8.5 cm under the skin)
print('VOCALSAC anchor depth inside flesh: %.3f m (needs < -0.03)'%sdf.sdf(SAC_A[None])[0])
sacm,bsac,_=principled('Qingyue_VocalSac'); bsac.inputs['Base Color'].default_value=(*[(c/255)**2.2 for c in (236,224,170)],1)   # matches the cream throat skin
bsac.inputs['Roughness'].default_value=0.42; bsac.inputs['Coat Weight'].default_value=0.35; bsac.inputs['Coat Roughness'].default_value=0.12
bsac.inputs['Subsurface Weight'].default_value=0.15
bm=bmesh.new(); bmesh.ops.create_uvsphere(bm,u_segments=64,v_segments=40,radius=1.0)
dCA=(SAC_A-SAC_C)/np.linalg.norm(SAC_A-SAC_C)
neckw=[]
for v in bm.verts:
    u=np.array(v.co); p=SAC_C+u*SAC_R
    w=np.clip(np.dot(u,dCA),0,1)**2.2                                  # back of the balloon tapers into a neck that enters the throat
    p=p+(SAC_A-p)*0.62*w; neckw.append(w)
    v.co=Vector(SAC_A+SAC_S0*(p-SAC_A))
sac_me=bpy.data.meshes.new('Qingyue_VocalSac'); bm.to_mesh(sac_me); bm.free()
sac=bpy.data.objects.new('Qingyue_VocalSac',sac_me); bpy.context.collection.objects.link(sac); sac_me.materials.append(sacm); shade_smooth(sac)
_ng=sac.vertex_groups.new(name='sac_neck'); _ng.add([i for i,w in enumerate(neckw) if w>0.02],1.0,'REPLACE')   # neck part runs inside the body (checker skips it)
sub=sac.modifiers.new('sub','SUBSURF'); sub.levels=1; apply_mods(sac)
_d=sdf.sdf(verts_np(sac)); print('VOCALSAC deflated: verts %d, outside the skin: %d (must be 0)'%(len(_d),int((_d>0).sum())))
# ---------- armature
BN={}
def cone_of(b):
    for pr in sdf.P:
        if pr[1]==b and pr[2]=='cone': return np.array(pr[3][0]),np.array(pr[3][1])
def sph_of(b):
    for pr in sdf.P:
        if pr[1]==b and pr[2] in('sph','ell'): return np.array(pr[3][0])
arm_d=bpy.data.armatures.new('Qingyue_Rig'); rig=bpy.data.objects.new('Qingyue_Rig',arm_d); bpy.context.collection.objects.link(rig)
activate(rig); bpy.ops.object.mode_set(mode='EDIT'); eb=arm_d.edit_bones
def B(name,h,t,parent=None,up=(0,-1,0)):
    b=eb.new(name); b.head=Vector(h); b.tail=Vector(t)
    if parent: b.parent=eb[parent]; b.use_connect=False
    b.align_roll(Vector(up)); return b
B('root',(0,0,0),(0,0.25,0),None,(0,0,1))
HZ=sdf.HZ
B('hips',(0,0.07,0.15),(0,0.06,0.31),'root'); B('spine',(0,0.06,0.31),(0,0.03,0.44),'hips')
B('chest',(0,0.03,0.44),(0,0.0,0.61+HZ),'spine'); B('neck',(0,0.0,0.61+HZ),(0,-0.02,0.69+HZ),'chest')
B('head',(0,-0.02,0.69+HZ),(0,-0.02,1.02+HZ),'neck'); B('jaw',(0,0.06,0.66+HZ),(0,-0.31,0.62+HZ),'head',(0,0,1))
B('throat',(0,-0.07,0.56+HZ),(0,-0.22,0.53+HZ),'neck',(0,0,1)); B('vsac',tuple(SAC_A),tuple(SAC_A+np.array([0,-0.1,0])),'throat',(0,0,1)); B('crown',tuple(CC),tuple(CC+np.array(cn)*0.1),'head')
for s,n in ((1,'L'),(-1,'R')):
    c=sdf.eye_c(s); f=np.array(eye_fwd(s)); B('eye.'+n,c,c+f*0.12,'head',(0,0,1))
    L=LID[n]; B('lid.'+n,c,c+np.array(L['a'])*0.12,'head',tuple(L['f']))
    for seg,par in (('upper_arm','chest'),('forearm','upper_arm'),('thigh','hips'),('shin','thigh'),('foot','shin')):
        h,t=cone_of(seg+'.'+n); B(seg+'.'+n,h,t,par+'.'+n if par not in('chest','hips') else par,(0,0,1) if seg in('upper_arm','forearm','foot') else (0,-1,0))
    wr=cone_of('forearm.'+n)[1]; hc=sph_of('hand.'+n); B('hand.'+n,wr,wr+(hc-wr)*2.0,'forearm.'+n,(0,0,1))
    for i in range(1,5):
        h,t=cone_of('finger%d.%s'%(i,n)); B('finger%d.%s'%(i,n),h,t,'hand.'+n,(0,-1,0))
    for i in range(1,6):
        h,t=cone_of('toe%d.%s'%(i,n)); B('toe%d.%s'%(i,n),h,t,'foot.'+n,(0,0,1))
bpy.ops.object.mode_set(mode='OBJECT')
bone_names=[b.name for b in arm_d.bones]
# ---------- weights for body
VD=np.load(BUILD+'verts.npz'); V=verts_np(body); assert np.allclose(V,VD['V'])
dl=VD['dl']; vb_p=np.array([pr[1] for pr in sdf.P]); grp=VD['grp']
x,y,z=V.T
dmin=dl.min(-1,keepdims=True); E=np.exp(-(dl-dmin)/0.018)
W={}
for j,b in enumerate(vb_p):
    W[b]=W.get(b,0)+E[:,j]
tor=W.pop('TORSO')
def tri(zv,a,b,c):
    return np.clip(np.minimum((zv-a)/(b-a),(c-zv)/(c-b)),0,1)
W['hips']=W.get('hips',0)+tor*np.clip((0.31-z)/0.12,0,1)
W['spine']=W.get('spine',0)+tor*tri(z,0.18,0.33,0.46)
W['chest']=W.get('chest',0)+tor*np.clip((z-0.33)/0.12,0,1)
# neck blend between chest/head
nk=S(1-np.abs(z-0.635-sdf.HZ)/0.07)*(grp==0)*(np.abs(x)<0.3)
tot=sum(W.values())
for k in W: W[k]=W[k]/tot
W['neck']=nk*0.5
for k in list(W):
    if k!='neck': W[k]=W[k]*(1-nk*0.5)
zmv=sdf.zm(x,y)
V0=VD['V0']; z0=V0[:,2]
# jaw = everything under the lip slit (decided on the pre-closed positions, so the two lips separate cleanly)
side=S((sdf.zm(V0[:,0],V0[:,1])-z0+0.003)/0.006)
inM=S((0.03-sdf.mouth_vol(V0))/0.10)   # wider corner blend -> corners stretch like a cheek, no tearing
jw=(grp==0)*side*inM*S((z0-0.50-sdf.HZ)/0.06)*S((0.12-y)/0.08)
# v5: the mouth floor must never rotate further than the outer chin skin below it, otherwise at a wide croak
#     the floor swings down through the (partially throat-weighted) chin -> red slit on the throat.
raw0=VD['raw']; zl0=sdf.zm(V0[:,0],V0[:,1])
outer=(grp==0)&(raw0>-0.002)&(z0<zl0)&(jw<0.999)
inner=np.nonzero((grp==0)&(raw0<-0.003)&(side>0.5))[0]
from mathutils import kdtree as _kd
_T=_kd.KDTree(int(outer.sum())); _oi=np.nonzero(outer)[0]
for k,i in enumerate(_oi): _T.insert((V0[i,0],V0[i,1],0.0),k)
_T.balance(); _cap=0
for i in inner:
    best=None
    for co,k,dist in _T.find_n((V0[i,0],V0[i,1],0.0),24):
        j=_oi[k]
        if dist<0.03 and z0[j]<z0[i] and (best is None or z0[j]>z0[best]): best=j
    if best is not None and jw[best]<jw[i]: jw[i]=jw[best]; _cap+=1
print('MOUTH-FLOOR weights capped to outer chin:',_cap,'of',len(inner))
# smooth the floor weights over the floor's own edges (no isolated vertices left at full rotation -> no spikes)
_ed=np.zeros(len(body.data.edges)*2,int); body.data.edges.foreach_get('vertices',_ed); _ed=_ed.reshape(-1,2)
_isin=np.zeros(len(V),bool); _isin[inner]=True
for _it in range(90):   # v8c: longer smoothing -> no folds in the mouth floor when the jaw opens 22 deg
    acc=np.zeros(len(V)); cnt=np.zeros(len(V))
    np.add.at(acc,_ed[:,0],jw[_ed[:,1]]); np.add.at(cnt,_ed[:,0],1); np.add.at(acc,_ed[:,1],jw[_ed[:,0]]); np.add.at(cnt,_ed[:,1],1)
    avg=acc/np.maximum(cnt,1); jw=np.where(_isin,0.5*jw+0.5*avg,jw)
_nb=np.zeros(len(V)); np.maximum.at(_nb,_ed[:,0],np.abs(jw[_ed[:,0]]-jw[_ed[:,1]])); np.maximum.at(_nb,_ed[:,1],np.abs(jw[_ed[:,0]]-jw[_ed[:,1]]))
print('MOUTH-FLOOR max neighbour weight jump inside the mouth: %.3f'%_nb[inner].max())
# throat sac: soft localized blob under the chin (no hard edges -> no flap)
TCEN=np.array([0,-0.20,0.548+sdf.HZ]); q=(V-TCEN)/np.array([0.16,0.13,0.075])
tw=(grp==0)*np.exp(-2.2*np.sum(q*q,1))*S((0.0-y)/0.08)*0.9
for k in list(W): W[k]=W[k]*(1-jw)
W['jaw']=jw
for k in list(W): W[k]=W[k]*(1-tw)
W['throat']=tw
names=list(W); M=np.stack([np.broadcast_to(W[k],(len(V),)) for k in names],-1).astype(np.float64)
# Laplacian smoothing of weights over mesh edges (lips are not connected, so the jaw split stays crisp)
ed=np.zeros(len(body.data.edges)*2,int); body.data.edges.foreach_get('vertices',ed); ed=ed.reshape(-1,2)
deg=np.bincount(ed.ravel(),minlength=len(V)).astype(float)+1e-9
jcol=names.index('jaw')
for it in range(10):
    acc=np.zeros_like(M); np.add.at(acc,ed[:,0],M[ed[:,1]]); np.add.at(acc,ed[:,1],M[ed[:,0]])
    Ms=0.5*M+0.5*acc/deg[:,None]
    Ms[:,jcol]=np.where(inM>0.98,M[:,jcol],Ms[:,jcol])   # keep the lip split exact
    M=Ms
M/=M.sum(1,keepdims=True)+1e-9
order=np.argsort(-M,axis=1); keep=np.zeros_like(M,bool); np.put_along_axis(keep,order[:,:4],True,axis=1)
M=np.where(keep,M,0); M/=M.sum(1,keepdims=True)+1e-9
for j,k in enumerate(names):
    idx=np.nonzero(M[:,j]>0.003)[0]
    if len(idx)==0: continue
    vg=body.vertex_groups.new(name=k)
    for i in idx: vg.add([int(i)],float(M[i,j]),'REPLACE')
def whole(ob,bone):
    vg=ob.vertex_groups.new(name=bone); vg.add(list(range(len(ob.data.vertices))),1.0,'REPLACE')
for n in 'LR': whole(eyes[n],'eye.'+n); whole(LID[n]['ob'],'lid.'+n)
whole(crown,'crown')
whole(sac,'vsac')
# ---------- shape keys body
body.shape_key_add(name='Basis')
piv=np.array([0,0.06,0.66+sdf.HZ])
def jawrot(P,ang,w):
    a=np.radians(ang)*w; q=P-piv; yy=q[:,1]*np.cos(a)-q[:,2]*np.sin(a); zz=q[:,1]*np.sin(a)+q[:,2]*np.cos(a)
    return np.stack([P[:,0],yy+piv[1],zz+piv[2]],-1)
band=np.exp(-((z-zmv)/0.04)**2)*(grp==0)*(y<0.08)
corner=band*S((np.abs(x)-0.06)/0.16)
def key(name,P):
    k=body.shape_key_add(name=name,from_mix=False); k.data.foreach_set('co',P.astype(np.float32).ravel())
def pinch(P,amt,fwd=0.0):
    P=P.copy(); P[:,0]*=1-amt*corner; P[:,1]-=fwd*band*S((0.2-np.abs(x))/0.1); return P
def widen(P,amt,lift):
    P=P.copy(); P[:,0]*=1+amt*corner; P[:,2]+=lift*corner; return P
key('mouth_open',jawrot(V,10,jw))
key('smile',widen(V,0.03,0.022)+np.stack([0*x,0.012*corner,0*x],-1))
key('viseme_A',jawrot(V,8,jw))      # v7: speech shapes are PURE vertical jaw opening (no corner widen/pinch)
key('viseme_O',jawrot(V,6,jw))
key('viseme_E',jawrot(V,4,jw))
key('viseme_U',jawrot(V,3,jw))
tc=np.array([0,-0.06,0.56+sdf.HZ]); dv=V-tc; dv/=np.linalg.norm(dv,axis=1,keepdims=True)+1e-9
dv[:,1]=np.minimum(dv[:,1],0.1); key('throat_puff',V+dv*(0.05*tw/0.9)[:,None])
for n in 'LR':
    L=LID[n]; ob=L['ob']; ob.shape_key_add(name='Basis')
    P=verts_np(ob); R=np.array(Matrix.Rotation(math.radians(BLINK),3,L['axis']))
    c=np.array(L['c']); k=ob.shape_key_add(name='blink_'+n,from_mix=False); k.data.foreach_set('co',((P-c)@R.T+c).astype(np.float32).ravel())
# ---------- parent
for ob in [body,eyes['L'],eyes['R'],LID['L']['ob'],LID['R']['ob'],crown,sac]:
    ob.parent=rig; m=ob.modifiers.new('Armature','ARMATURE'); m.object=rig
rig.data.display_type='STICK'
LIDAX={n:LID[n]['axis'] for n in 'LR'}
import pickle; pickle.dump({n:tuple(LID[n]['axis']) for n in 'LR'},open(BUILD+'lidax.pkl','wb'))
bpy.ops.wm.save_as_mainfile(filepath=BUILD+'stage3.blend')
print('STAGE3 OK', bone_names)
