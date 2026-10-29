# Stage 3v (v6): outdoor field-research vest, skinned to the rig.  Runs after stage3 (edits build/stage3.blend in place).
#  - shell  : copy of the body's torso faces pushed 11 mm out (5.5 mm thick); every vertex copies the bone weights and
#             shape-key deltas of the body vertex it came from -> it deforms exactly with the skin in every action.
#  - opening: open front placket, armholes clear of the upper-arm sweep, hem at the waist, neckline under the chin,
#             kept off the thighs (hug pose) - edges smoothed and covered with a binding tape; rolled collar; zipper.
#  - parts  : parametric patches that follow the body surface (pockets, flaps, snaps, badges), pen + magnifier.
#  - textures: real canvas fabric maps (colour / roughness / normal) with stitches, plus a printed badge texture.
exec(open('/Users/administrator/Tilo工作台/20261028-青跃三维/project/src/common.py').read())
import os
from mathutils import kdtree
bpy.ops.wm.open_mainfile(filepath=BUILD+'stage3.blend')
for _o in [o for o in bpy.data.objects if o.name.startswith('Qingyue_Vest')]:   # idempotent: drop any earlier vest
    bpy.data.objects.remove(_o,do_unlink=True)
for _m in [m for m in bpy.data.meshes if m.users==0]: bpy.data.meshes.remove(_m)
TEX='/Users/administrator/Tilo工作台/20261028-青跃三维/project/textures/'
S=lambda t:np.clip(t,0,1)**2*(3-2*np.clip(t,0,1))
body=bpy.data.objects['Qingyue_Body']; rig=bpy.data.objects['Qingyue_Rig']; me=body.data
VD=np.load(BUILD+'verts.npz'); V=verts_np(body); assert np.allclose(V,VD['V'])
N=np.zeros(len(V)*3); me.vertices.foreach_get('normal',N); N=N.reshape(-1,3)
vb=VD['vb'].astype(str); grp=VD['grp']; x,y,z=V.T
F=np.array([list(p.vertices) for p in me.polygons]); assert F.shape[1]==3
gnames=[g.name for g in body.vertex_groups]
W=np.zeros((len(V),len(gnames)),np.float32)
for v in me.vertices:
    for ge in v.groups: W[v.index,ge.group]=ge.weight
KB=me.shape_keys.key_blocks; KEYS={}
for kb in KB[1:]:
    a=np.zeros(len(V)*3); kb.data.foreach_get('co',a); KEYS[kb.name]=a.reshape(-1,3)-V
def seg_d(p,a,b):
    a=np.asarray(a,float); b=np.asarray(b,float); ab=b-a; t=np.clip(((p-a)@ab)/(ab@ab),0,1); return np.linalg.norm(p-(a+t[:,None]*ab),axis=1)
# ---------------------------------------------------------------- region (per body vertex)
OFF=0.011; THK=0.0055
zl=sdf.zm(x,y)
legd=np.min([sdf.cone(V,*pr[3]) for pr in sdf.P if pr[0]=='body' and pr[1].startswith(('thigh','shin','foot')) and pr[2]=='cone'],axis=0)
torso=(grp==0)&~np.char.startswith(vb,'toe')&(legd>0.03)     # geometric: any body surface that is not leg surface
reg=torso&(z>0.15)
reg&=np.where(y<0.06, z<0.455, z<0.52)                          # flat neckline under the chin; back kept below where the head tips back in flight
headd=np.min([sdf.prim_d(V,pr) for pr in sdf.P if pr[0]=='body' and pr[1]=='head'],axis=0)
reg&=headd>0.035                                                  # keep >=3.5 cm under the head (head tilts/turns, cheeks overhang)
np.save(BUILD+'vest_cand.npy',np.nonzero(reg)[0])                  # full pre-sweep candidate set (armsweep tests all of it)
if os.path.exists(BUILD+'armsweep.npy'):                          # arm sweep over ALL actions (armsweep.py): cut wherever an arm ever
    reg&=np.load(BUILD+'armsweep.npy')>0.03                       # comes within 3 cm of the skin -> arms never pass through the vest
for s,n in ((1,'L'),(-1,'R')):
    A=sdf.ARM[n]; piv=np.array(A['sh'])+np.array([-0.04*s,0.03,0])
    reg&=(np.linalg.norm(V-piv,axis=1)>0.10)&(seg_d(V,A['sh'],A['el'])>0.086)   # armholes: >2 cm clear of the upper-arm skin
reg&=~((y<-0.02)&(np.abs(x)<0.085))                              # open front placket
fsel=reg[F].all(1)
# keep big connected pieces only
par=np.arange(len(V))
def find(i):
    while par[i]!=i: par[i]=par[par[i]]; i=par[i]
    return i
for f in F[fsel]:
    a,b,c=find(f[0]),find(f[1]),find(f[2]); par[b]=a; par[find(c)]=a
roots=np.array([find(f[0]) for f in F[fsel]]); u,cnt=np.unique(roots,return_counts=True)
keep=np.isin(roots,u[cnt>=300]); FS=F[fsel][keep]
src=np.unique(FS); remap=-np.ones(len(V),int); remap[src]=np.arange(len(src))
np.save(BUILD+'vest_src.npy',src)
import time; _t0=time.time()
print('VEST faces',len(FS),'pieces',int((cnt>=300).sum()))
# ---------------------------------------------------------------- shell with smoothed opening edges
P=V[src]+N[src]*OFF
buv=np.zeros(len(me.loops)*2); me.uv_layers.active.data.foreach_get('uv',buv); buv=buv.reshape(-1,2)
fl=np.array([p.loop_start for p in me.polygons]); fidx=np.nonzero(fsel)[0][keep]
bm=bmesh.new(); bv=[bm.verts.new(p) for p in P]; bm.verts.ensure_lookup_table(); ul=bm.loops.layers.uv.new('UVMap')
for f,fi in zip(remap[FS],fidx):
    face=bm.faces.new([bv[i] for i in f])
    for k,lp in enumerate(face.loops): lp[ul].uv=buv[fl[fi]+k]
bm.edges.ensure_lookup_table()
filled=bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=30)['faces']   # close tiny holes
for face in filled:
    for lp in face.loops:
        other=[l2 for l2 in lp.vert.link_loops if l2.face not in filled]
        if other: lp[ul].uv=other[0][ul].uv
bmesh.ops.triangulate(bm,faces=filled)
print('VEST tiny holes filled:',len(filled))
bnd=[v for v in bm.verts if v.is_boundary]
for it in range(12):   # smooth the stair-stepped boundary along itself, then re-seat it on the skin offset
    new={}
    for v in bnd:
        nb=[e.other_vert(v) for e in v.link_edges if e.is_boundary]
        if len(nb)==2: new[v]=(v.co*0.5+(nb[0].co+nb[1].co)*0.25)
    for v,c in new.items(): v.co=c
pts=np.array([tuple(v.co) for v in bnd])
q=sdf.project(pts,lambda p:sdf.sdf(p))
nq=np.stack([(sdf.sdf(q+np.eye(3)[i]*1e-3)-sdf.sdf(q)) for i in range(3)],-1); nq/=np.linalg.norm(nq,axis=1,keepdims=True)
for v,p in zip(bnd,q+nq*OFF): v.co=Vector(p)
# boundary loops (for binding tape + collar + zipper)
loops=[];seen=set()
for v0 in bnd:
    if v0 in seen: continue
    loop=[v0]; seen.add(v0); cur=v0; prev=None
    while True:
        nb=[e.other_vert(cur) for e in cur.link_edges if e.is_boundary and e.other_vert(cur)!=prev]
        nb=[w for w in nb if w not in seen] or nb
        if not nb or nb[0]==v0 or nb[0] in seen: break
        prev=cur; cur=nb[0]; loop.append(cur); seen.add(cur)
    arr=np.array([tuple(v.co) for v in loop])
    cut=np.nonzero(np.linalg.norm(np.diff(arr,axis=0),axis=1)>0.025)[0]+1       # tracer jumped -> split
    for segm in np.split(arr,cut):
        if len(segm)>8: loops.append(segm)
print('VEST edge loops',len(loops),[len(l) for l in loops],'t=%.0fs'%(time.time()-_t0))
vest_me=bpy.data.meshes.new('Qingyue_Vest'); bm.to_mesh(vest_me); bm.free()
vest=bpy.data.objects.new('Qingyue_Vest',vest_me); bpy.context.collection.objects.link(vest)
# UVs: the shell re-uses the body's UV layout (texel <-> body position known from the stage2 bakes)
buv=np.zeros(len(me.loops)*2); me.uv_layers.active.data.foreach_get('uv',buv); buv=buv.reshape(-1,2)
fl=np.array([p.loop_start for p in me.polygons]); fidx=np.nonzero(fsel)[0][keep]
so=vest.modifiers.new('so','SOLIDIFY'); so.thickness=THK; so.offset=-1; so.use_rim=True
apply_mods(vest); shade_smooth(vest)
nsrc=len(src); VV=verts_np(vest); vsrc=np.concatenate([src,src])[:len(VV)]   # solidify: originals then the offset copies
# ---------------------------------------------------------------- skinning helpers
from mathutils import kdtree
KT=kdtree.KDTree(len(V))
for i,p in enumerate(V):
    if grp[i]==0: KT.insert(p,i)
KT.balance()
def near_src(pts): return np.array([KT.find(Vector(p))[1] for p in pts])
def skin(ob,s_idx,with_keys=True):
    ob.parent=rig
    for j,gn in enumerate(gnames):
        w=W[s_idx,j]; idx=np.nonzero(w>0.002)[0]
        if len(idx)==0: continue
        vg=ob.vertex_groups.get(gn) or ob.vertex_groups.new(name=gn)
        for i in idx: vg.add([int(i)],float(w[i]),'REPLACE')
    m=ob.modifiers.new('Armature','ARMATURE'); m.object=rig
    if with_keys and KEYS:
        ob.shape_key_add(name='Basis'); B0=verts_np(ob)
        for kn,d in KEYS.items():
            if np.abs(d[s_idx]).max()<1e-6: continue
            k=ob.shape_key_add(name=kn,from_mix=False); k.data.foreach_set('co',(B0+d[s_idx]).astype(np.float32).ravel())
skin(vest,vsrc)
# ---------------------------------------------------------------- materials (+ real texture maps)
def principled(name):
    m=bpy.data.materials.new(name); m.use_nodes=True; return m,m.node_tree.nodes['Principled BSDF'],m.node_tree
def tex_mat(name,base,rough,nrm,strength=0.6):
    m,b,nt=principled(name)
    for fn,sock,nc in ((base,'Base Color',False),(rough,'Roughness',True)):
        t=nt.nodes.new('ShaderNodeTexImage'); t.image=bpy.data.images.load(TEX+fn)
        if nc: t.image.colorspace_settings.name='Non-Color'
        nt.links.new(t.outputs[0],b.inputs[sock])
    t=nt.nodes.new('ShaderNodeTexImage'); t.image=bpy.data.images.load(TEX+nrm); t.image.colorspace_settings.name='Non-Color'
    nm=nt.nodes.new('ShaderNodeNormalMap'); nm.inputs[0].default_value=strength; nt.links.new(t.outputs[0],nm.inputs[1]); nt.links.new(nm.outputs[0],b.inputs['Normal'])
    b.inputs['Sheen Weight'].default_value=0.25; return m
def solid(name,col,rough,metal=0.0):
    m,b,_=principled(name); b.inputs['Base Color'].default_value=(*[(c/255)**2.2 for c in col],1); b.inputs['Roughness'].default_value=rough; b.inputs['Metallic'].default_value=metal; return m
from mathutils import kdtree
# --- textures (numpy): canvas weave everywhere + stitches along the shell edges (body-UV space)
RES=2048
pos=np.load(BUILD+'bake_pos.npy'); cov=pos[...,3]>0.5
uu,vv=np.meshgrid((np.arange(RES)+0.5)/RES,(np.arange(RES)+0.5)/RES)
def weave(u,v,f):
    a=np.sin(u*f*np.pi*2); b=np.sin(v*f*np.pi*2); return 0.5+0.25*np.sign(a*b)*np.abs(a)**0.5*np.abs(b)**0.5+0.25*np.sin((u+v)*f*np.pi)
wv=weave(uu,vv,420)
# distance (3D) from each covered texel to the vest edges -> stitch line 7 mm inside every edge
E=np.concatenate(loops); KE=kdtree.KDTree(len(E))
for i,p in enumerate(E): KE.insert(p,i)
KE.balance()
P3all=pos[...,:3]; cand=cov&(P3all[...,2]>0.10)&(P3all[...,2]<0.66)&(np.abs(P3all[...,0])<0.45)
ed=np.full((RES,RES),9.0); ci=np.nonzero(cand)
ed[ci]=np.array([KE.find(p)[2] for p in P3all[ci]])
dash=(np.sin((uu+vv)*RES*0.9)>-0.2)
stitch=S(1-np.abs(ed-0.007)/0.0011)*dash
hem=S((0.012-ed)/0.004)                                 # slightly darker, worn edge band
sand=np.array([196,170,118])/255.; dark=np.array([150,126,84])/255.; thread=np.array([236,222,186])/255.
col=sand[None,None]*(0.90+0.16*wv[...,None])
col=col*(1-0.25*hem[...,None])+dark[None,None]*0.25*hem[...,None]
col=col*(1-stitch[...,None])+thread[None,None]*stitch[...,None]
# subtle sun-faded mottling (3D noise from texel positions)
P3=pos[...,:3]; mott=np.sin(P3[...,0]*31+1.3)*np.sin(P3[...,1]*27+0.4)*np.sin(P3[...,2]*23+2.1)
col*=(0.96+0.05*mott)[...,None]
rough=0.82+0.08*(wv-0.5)-0.1*stitch
h=0.5*wv+1.4*stitch-0.6*hem
def save(name,a,gamma=True):
    im=bpy.data.images.new(name,RES if a.shape[0]==RES else a.shape[0],a.shape[1],alpha=False)
    rgb=a if a.ndim==3 else np.repeat(a[...,None],3,-1)
    rgb=np.clip(rgb,0,1)**(1/2.2 if gamma else 1) if gamma else np.clip(rgb,0,1)
    im.pixels[:]=np.concatenate([rgb,np.ones(rgb.shape[:2]+(1,))],-1).astype(np.float32).ravel()
    im.filepath_raw=TEX+name+'.png'; im.file_format='PNG'; im.save(); return im
def normal_from(hh,s):
    gy,gx=np.gradient(hh); nm=np.stack([-gx*s,-gy*s,np.ones_like(hh)],-1); nm/=np.linalg.norm(nm,axis=-1,keepdims=True); return nm*0.5+0.5
print('VEST texture distances done t=%.0fs'%(time.time()-_t0)); save('qingyue_vest_basecolor',col**2.2*0+col**1.0 if False else col**2.2)   # stored as sRGB (save() re-applies 1/2.2)
save('qingyue_vest_roughness',rough,gamma=False); save('qingyue_vest_normal',normal_from(h,3.0),gamma=False)
# --- trim texture (pockets / flaps / binding / collar): 1024 unit square, stitch border all round
TR=1024; tu,tv=np.meshgrid((np.arange(TR)+0.5)/TR,(np.arange(TR)+0.5)/TR)
tw=weave(tu,tv,180); bd=np.minimum(np.minimum(tu,1-tu),np.minimum(tv,1-tv))
tst=S(1-np.abs(bd-0.06)/0.007)*(np.sin((tu+tv)*TR*0.45)>-0.2)
olive=np.array([128,112,70])/255.
tcol=olive[None,None]*(0.88+0.18*tw[...,None]); tcol=tcol*(1-tst[...,None])+thread[None,None]*tst[...,None]
tcol*=(1-0.18*S((0.03-bd)/0.03))[...,None]
save('qingyue_vest_trim_basecolor',tcol**2.2); save('qingyue_vest_trim_roughness',0.8+0.08*(tw-0.5)-0.1*tst,gamma=False)
save('qingyue_vest_trim_normal',normal_from(0.5*tw+1.4*tst-0.8*S((0.03-bd)/0.03),3.0),gamma=False)
# --- badge texture: embroidered round patch, leaf + 凤凰岛科普 (no brand logos)
# badge texture is drawn by vest_badge.py (venv: PIL) before this stage
assert os.path.exists(TEX+'qingyue_vest_badge.png')
fab=tex_mat('Qingyue_Vest_Fabric','qingyue_vest_basecolor.png','qingyue_vest_roughness.png','qingyue_vest_normal.png')
trim=tex_mat('Qingyue_Vest_Trim','qingyue_vest_trim_basecolor.png','qingyue_vest_trim_roughness.png','qingyue_vest_trim_normal.png')
badge,bb,bnt=principled('Qingyue_Vest_Badge'); t=bnt.nodes.new('ShaderNodeTexImage'); t.image=bpy.data.images.load(TEX+'qingyue_vest_badge.png'); bnt.links.new(t.outputs[0],bb.inputs['Base Color']); bb.inputs['Roughness'].default_value=0.75
snapm=solid('Qingyue_Vest_Snap',(70,52,34),0.35,0.3); zipm=solid('Qingyue_Vest_Zip',(178,146,86),0.3,0.9)
penm=solid('Qingyue_Vest_Pen',(40,92,150),0.3); penclip=solid('Qingyue_Vest_PenClip',(200,200,205),0.25,1.0)
glass,bg,_=principled('Qingyue_Vest_Glass'); bg.inputs['Transmission Weight'].default_value=1; bg.inputs['Roughness'].default_value=0.03; bg.inputs['IOR'].default_value=1.45
vest.data.materials.append(fab)
# ---------------------------------------------------------------- surface-following parametric parts
def sfun(p): return sdf.sdf(p)
def on_body(p,off):
    q=sdf.project(np.atleast_2d(p),sfun)
    n=np.stack([(sfun(q+np.eye(3)[i]*1e-3)-sfun(q)) for i in range(3)],-1); n/=np.linalg.norm(n,axis=1,keepdims=True)
    return q+n*off,n
def frame(c):
    q,n=on_body(c,0); n=n[0]; up=np.array([0,0,1.0])-n*n[2]; up/=np.linalg.norm(up); return q[0],n,up,np.cross(up,n)
parts=[]
def patch(name,c,w,h,off,thk,mat,nu=14,nv=12,curve=0.0,round_=0.0):
    """rectangular (or rounded) patch draped on the body surface, UV 0..1 over the patch"""
    q0,n0,up,rt=frame(np.array(c))
    G=np.zeros((nv+1,nu+1,3)); UV=np.zeros((nv+1,nu+1,2))
    for j in range(nv+1):
        for i in range(nu+1):
            a=i/nu-0.5; b=j/nv-0.5
            if round_>0:  # square grid -> disc (badges); UV follows the disc so the printed circle maps 1:1
                r=max(abs(a),abs(b))*2; ang=math.atan2(b,a); a=0.5*r*math.cos(ang); b=0.5*r*math.sin(ang)
            G[j,i]=q0+rt*a*w+up*(b*h+curve*(a*a))
            UV[j,i]=(a+0.5,b+0.5)
    pts,_=on_body(G.reshape(-1,3),off)
    bm=bmesh.new(); vs=[bm.verts.new(p) for p in pts]
    for j in range(nv):
        for i in range(nu):
            k=j*(nu+1)+i; bm.faces.new((vs[k],vs[k+1],vs[k+nu+2],vs[k+nu+1]))
    me_=bpy.data.meshes.new(name); bm.to_mesh(me_); bm.free()
    l=me_.uv_layers.new(name='UVMap'); uv=UV.reshape(-1,2)
    l.data.foreach_set('uv',np.array([uv[lp.vertex_index] for lp in me_.loops]).ravel())
    ob=bpy.data.objects.new(name,me_); bpy.context.collection.objects.link(ob); me_.materials.append(mat)
    so=ob.modifiers.new('so','SOLIDIFY'); so.thickness=thk; so.offset=-1; apply_mods(ob); shade_smooth(ob); parts.append(ob); return ob,q0,n0,up,rt
def disc(name,p,n,r,t,mat,seg=20):
    bpy.ops.mesh.primitive_cylinder_add(vertices=seg,radius=r,depth=t,location=p)
    ob=bpy.context.active_object; ob.name=name; ob.rotation_mode='QUATERNION'; ob.rotation_quaternion=Vector((0,0,1)).rotation_difference(Vector(n))
    bev=ob.modifiers.new('b','BEVEL'); bev.width=t*0.35; bev.segments=2; apply_mods(ob)
    activate(ob); bpy.ops.object.transform_apply(location=True,rotation=True,scale=True); ob.data.materials.append(mat); shade_smooth(ob); parts.append(ob); return ob
def tube(name,pts,r,mat,closed=False,res=6):
    cu=bpy.data.curves.new(name,'CURVE'); cu.dimensions='3D'; cu.bevel_depth=r; cu.bevel_resolution=2; cu.use_fill_caps=True
    sp=cu.splines.new('POLY'); sp.points.add(len(pts)-1); sp.use_cyclic_u=bool(closed)
    for i,p in enumerate(pts): sp.points[i].co=(*p,1)
    ob=bpy.data.objects.new(name,cu); bpy.context.collection.objects.link(ob); cu.materials.append(mat)
    activate(ob); bpy.ops.object.convert(target='MESH'); ob=bpy.context.active_object; shade_smooth(ob)
    me_=ob.data; l=me_.uv_layers.new(name='UVMap') if not me_.uv_layers else me_.uv_layers[0]
    parts.append(ob); return ob
print('VEST textures saved t=%.0fs'%(time.time()-_t0))
# pockets: two flapped chest pockets + two lower flank pockets (field-vest layout)
POCK=[]
LAY=np.load(BUILD+'vest_layout.npy') if os.path.exists(BUILD+'vest_layout.npy') else None   # searched layout: 100% on fabric, clear of every body sweep
if LAY is not None:
    POCK=[('chest',LAY[0],0.06,0.05),('flank',LAY[1],0.085,0.075),('chest',LAY[2],0.06,0.05),('flank',LAY[3],0.085,0.075)]
else:
    for s in (1,-1):
        POCK.append(('chest',np.array([0.18*s,0.10,0.39]),0.06,0.05)); POCK.append(('flank',np.array([0.235*s,0.205,0.29]),0.09,0.078))
REGV=np.nonzero(reg)[0]; KR=kdtree.KDTree(len(V))
for i in np.nonzero(grp==0)[0]: KR.insert(V[i],i)
KR.balance()
def on_vest_frac(pts): return float(np.mean([reg[KR.find(Vector(p))[1]] for p in pts]))
for k,(kind,c,w,h) in enumerate(POCK):
    ob,q0,n0,up,rt=patch('VestPocket%d'%k,c,w,h,OFF+0.0045,0.004,trim)
    print('VEST pocket',k,kind,'on vest fabric: %.0f%%'%(100*on_vest_frac(verts_np(ob))))
    fl,_,_,_,_=patch('VestFlap%d'%k,q0+up*(h*0.5-0.012),w*1.08,0.032,OFF+0.0105,0.0035,trim,nv=4,curve=-0.01)
    p,n=on_body(q0+up*(h*0.5-0.022),OFF+0.0145); disc('VestSnap%d'%k,p[0],n[0],0.0085,0.004,snapm)
    POCK[k]=(kind,q0,n0,up,rt,w,h)
# chest badge (leaf patch) above the left chest pocket + large back badge
_,q0,n0,up,rt,w,h=POCK[0]
bdg,_,_,_,_=patch('VestBadgeChest',LAY[5] if LAY is not None else np.array([-0.18,0.25,0.48]),0.062,0.062,OFF+0.004,0.002,badge,nu=12,nv=12,round_=1)
bk,_,_,_,_=patch('VestBadgeBack',LAY[4] if LAY is not None else np.array([0.0,0.30,0.40]),0.14,0.14,OFF+0.004,0.002,badge,nu=16,nv=16,round_=1)
print('VEST back badge on vest fabric: %.0f%%'%(100*on_vest_frac(verts_np(bk))),' chest badge: %.0f%%'%(100*on_vest_frac(verts_np(bdg))))
# pen in the right chest pocket, magnifier in the left flank pocket
_,q0,n0,up,rt,w,h=POCK[2]
base=q0+n0*(OFF+0.012)+(rt if q0[0]>0 else -rt)*0.0-np.sign(q0[0])*np.array([0.018,0,0])-up*0.01   # inner side of the pocket (away from the shoulder)
pdir=up+n0*0.25; pdir/=np.linalg.norm(pdir)                      # leans slightly out with the body curve
pen=tube('VestPen',[base,base+pdir*0.075],0.0058,penm)
clip=tube('VestPenClip',[base+pdir*0.072+n0*0.007,base+pdir*0.045+n0*0.007],0.0018,penclip)
_,q0,n0,up,rt,w,h=POCK[1]
mb=q0+n0*(OFF+0.012)-rt*0.02
mdir=up+n0*0.45; mdir/=np.linalg.norm(mdir); mside=np.cross(n0,mdir)
tube('VestMagHandle',[mb-mdir*0.01,mb+mdir*0.055],0.0055,snapm)
ring_c=mb+mdir*0.085; ringpts=[ring_c+(math.cos(a)*mside+math.sin(a)*mdir)*0.026 for a in np.linspace(0,2*np.pi,33)]
tube('VestMagRing',ringpts,0.0035,zipm,closed=True)
disc('VestMagGlass',ring_c,n0,0.024,0.003,glass,seg=28)
# binding tape on every opening edge; rolled collar on the neckline loop; zipper teeth on the front edges
for i,lp in enumerate(loops):
    sm=lp.copy(); closed=np.linalg.norm(sm[0]-sm[-1])<0.025
    for it in range(4):
        nb=0.5*sm+0.25*(np.roll(sm,1,0)+np.roll(sm,-1,0))
        if not closed: nb[0],nb[-1]=sm[0],sm[-1]
        sm=nb
    sm=on_body(sm,OFF+0.001)[0]                                    # re-seat the smoothed tape on the vest surface (smoothing cuts corners into the body)
    neck=sm[:,2].mean()>0.40 and np.abs(sm[:,0]).max()<0.3
    tube('VestBind%d'%i,sm,0.0048,trim,closed=closed)
    if neck:   # collar: thicker rolled band on the upper part of the neckline loop
        top=sm[sm[:,2]>np.percentile(sm[:,2],35)]
        nrm=on_body(top,0)[1]; tube('VestCollar%d'%i,top+nrm*0.005,0.0085,trim)   # one batched projection; slim enough for a full head turn
# zipper: metal teeth along both front edges (the placket boundary points facing forward, |x| ~ 0.085)
fe=np.concatenate(loops); fe=fe[(fe[:,1]<-0.12)&(np.abs(np.abs(fe[:,0])-0.09)<0.03)&(fe[:,2]>0.2)]
for s in (1,-1):
    side=fe[np.sign(fe[:,0])==s]
    if len(side)<4: continue
    side=side[np.argsort(side[:,2])]
    zz=np.arange(side[0,2]+0.01,side[-1,2]-0.005,0.0075)
    TP=np.stack([np.interp(zz,side[:,2],side[:,0]),np.interp(zz,side[:,2],side[:,1]),zz],-1)
    PP,NN=on_body(TP,OFF+0.004)                      # one batched projection for all teeth
    bm=bmesh.new()
    for pp,nn in zip(PP,NN):                          # teeth built directly in one bmesh (fast)
        q=Vector((0,0,1)).rotation_difference(Vector(nn)).to_matrix()
        r=bmesh.ops.create_cube(bm,size=1.0); vs=r['verts']
        bmesh.ops.scale(bm,vec=(0.007,0.004,0.004),verts=vs); bmesh.ops.rotate(bm,verts=vs,cent=(0,0,0),matrix=q); bmesh.ops.translate(bm,verts=vs,vec=Vector(pp))
    zm_=bpy.data.meshes.new('VestZip%d'%(0 if s==1 else 1)); bm.to_mesh(zm_); bm.free()
    tb=bpy.data.objects.new(zm_.name,zm_); bpy.context.collection.objects.link(tb); zm_.materials.append(zipm); parts.append(tb)
    print('VEST zipper teeth',len(PP))
    if s==-1:   # zipper pull at the top of the right edge
        p=side[-1]-np.array([0,0,0.02]); pp,nn=on_body(p,OFF+0.008)
        bpy.ops.mesh.primitive_cube_add(size=1,location=pp[0]-np.array([0,0,0.012])); zp=bpy.context.active_object; zp.scale=(0.012,0.004,0.026)
        activate(zp); bpy.ops.object.transform_apply(scale=True); bev=zp.modifiers.new('b','BEVEL'); bev.width=0.003; apply_mods(zp); zp.data.materials.append(zipm); parts.append(zp)
print('VEST parts built t=%.0fs'%(time.time()-_t0))
# join all parts into one skinned 'Qingyue_VestParts' object (weights from the nearest skin vertex)
for o in parts: o.select_set(False)
activate(parts[0]); [o.select_set(True) for o in parts]; bpy.ops.object.join()
vp=bpy.context.active_object; vp.name='Qingyue_VestParts'; vp.data.name='Qingyue_VestParts'
activate(vp); bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
skin(vp,near_src(verts_np(vp)))
print('VEST shell verts',len(VV),'parts verts',len(vp.data.vertices),'materials',[m.name for m in vp.data.materials])
# rest-pose sanity: nothing of the vest inside the skin
for ob in (vest,vp):
    pv=verts_np(ob); d=sdf.sdf(pv)
    print('VEST rest check',ob.name,'min distance to skin %.4f m, verts inside skin: %d'%(d.min(),int((d<-0.001).sum())))
bpy.ops.wm.save_as_mainfile(filepath=BUILD+'stage3.blend')
print('STAGE3V OK')
