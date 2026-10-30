# v11 精细动物 · stage 2 (Blender 5.2, background): high-res SDF mesh -> decimated low mesh (+ LOD1) with smart UVs,
# Cycles bake (selected-to-active) of colour / tangent normal (feather scallops, turtle scales) / roughness,
# armature from the bone list, distance + part based skin weights, feather cards with a 'fold' shape key, eyes, turtle shell.
# Export: ../animals/<kind>.glb (WebP textures, skins + morph targets, no baked clips: the pond drives the bones procedurally).
# usage: blender -b --python animals_blender.py -- [kind ...]
import bpy,bmesh,numpy as np,json,os,sys,math,time
from mathutils import Vector,kdtree
HERE=os.path.dirname(os.path.abspath(__file__));IN=os.path.join(HERE,'..','build','animals');OUTD=os.path.join(HERE,'..','animals');os.makedirs(OUTD,exist_ok=True)
TEX=os.path.join(IN,'tex')
def bl(v):v=np.asarray(v,np.float64);return np.stack([v[...,0],-v[...,2],v[...,1]],-1)     # three (Y up, +Z fwd) -> blender (Z up, -Y fwd)
CFG={  # target tris (LOD0 body), LOD1 ratio, bake res, feather bump cell size, cage
 'egret':dict(tris=10000,lod1=0.28,res=1024,cell=0.011,cage=0.003,size=1.0),
 'heron':dict(tris=10000,lod1=0.28,res=1024,cell=0.011,cage=0.003,size=1.0),
 'kingfisher':dict(tris=6000,lod1=0.3,res=1024,cell=0.0035,cage=0.0012,size=0.25),
 'grebe':dict(tris=6000,lod1=0.3,res=1024,cell=0.0045,cage=0.0015,size=0.3),
 'turtle':dict(tris=8000,lod1=0.3,res=1024,cell=0.0055,cage=0.002,size=0.5,q=72)}

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=4;sc.cycles.use_denoising=False
    sc.render.bake.margin=6
def mesh_obj(name,v,f,smooth=True):
    me=bpy.data.meshes.new(name);me.from_pydata([tuple(x) for x in bl(v)],[],[tuple(x) for x in f]);me.validate();me.update()
    if smooth:me.polygons.foreach_set('use_smooth',[True]*len(me.polygons))
    ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);return ob
def point_attr(ob,name,typ,data):
    a=ob.data.attributes.new(name,typ,'POINT');key='color' if typ=='FLOAT_COLOR' else ('vector' if typ=='FLOAT_VECTOR' else 'value')
    a.data.foreach_set(key,np.asarray(data,np.float32).ravel())
def select_only(*obs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:o.select_set(True)
    bpy.context.view_layer.objects.active=obs[-1]
def decimate(ob,ratio):
    m=ob.modifiers.new('dec','DECIMATE');m.ratio=ratio;m.use_collapse_triangulate=True
    select_only(ob);bpy.ops.object.modifier_apply(modifier=m.name)
def smart_uv(ob,margin=0.004):
    select_only(ob);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(62),island_margin=margin,area_weight=0.6,correct_aspect=True,scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')
def new_img(name,res,noncolor=False):
    im=bpy.data.images.new(name,res,res,alpha=False,float_buffer=False)
    if noncolor:im.colorspace_settings.name='Non-Color'
    return im
def N(nt,typ,**kw):
    n=nt.nodes.new(typ)
    for k,v in kw.items():
        if k=='inputs':
            for i,x in v.items():n.inputs[i].default_value=x
        else:setattr(n,k,v)
    return n

def hi_material(kind,cfg,scales):
    """procedural detail for the bake: vertex colour (+ alpha = roughness), feather scallops along the flow attribute / turtle scales"""
    m=bpy.data.materials.new('hi_'+kind);m.use_nodes=True;nt=m.node_tree;nt.nodes.clear();L=nt.links.new
    out=N(nt,'ShaderNodeOutputMaterial');bs=N(nt,'ShaderNodeBsdfPrincipled')
    col=N(nt,'ShaderNodeAttribute',attribute_name='Col');fm=N(nt,'ShaderNodeAttribute',attribute_name='fmask');fl=N(nt,'ShaderNodeAttribute',attribute_name='flow')
    geo=N(nt,'ShaderNodeNewGeometry')
    sc=N(nt,'ShaderNodeVectorMath',operation='SCALE');L(geo.outputs['Position'],sc.inputs[0]);sc.inputs['Scale'].default_value=1.0/cfg['cell']
    if not scales:
        vor=N(nt,'ShaderNodeTexVoronoi',voronoi_dimensions='3D',feature='F1');vor.inputs['Scale'].default_value=1.0;vor.inputs['Randomness'].default_value=0.85
        L(sc.outputs[0],vor.inputs['Vector'])
        dif=N(nt,'ShaderNodeVectorMath',operation='SUBTRACT');L(vor.outputs['Position'],dif.inputs[0]);L(sc.outputs[0],dif.inputs[1])
        dot=N(nt,'ShaderNodeVectorMath',operation='DOT_PRODUCT');L(dif.outputs[0],dot.inputs[0]);L(fl.outputs['Vector'],dot.inputs[1])
        # height rises toward each feather's free (downstream) edge, then drops where the next feather starts -> overlapping scallops
        h=N(nt,'ShaderNodeMath',operation='MULTIPLY_ADD',use_clamp=True);L(dot.outputs['Value'],h.inputs[0]);h.inputs[1].default_value=-0.9;h.inputs[2].default_value=0.55
        # fine barbs: stretched noise
        sc2=N(nt,'ShaderNodeVectorMath',operation='SCALE');L(geo.outputs['Position'],sc2.inputs[0]);sc2.inputs['Scale'].default_value=6.0/cfg['cell']
        nz=N(nt,'ShaderNodeTexNoise');nz.inputs['Scale'].default_value=1.0;nz.inputs['Detail'].default_value=3;L(sc2.outputs[0],nz.inputs['Vector'])
        mix=N(nt,'ShaderNodeMath',operation='MULTIPLY_ADD');L(nz.outputs['Fac'],mix.inputs[0]);mix.inputs[1].default_value=0.25;L(h.outputs[0],mix.inputs[2])
        hm=N(nt,'ShaderNodeMath',operation='MULTIPLY');L(mix.outputs[0],hm.inputs[0]);L(fm.outputs['Fac'],hm.inputs[1])
        bstr=0.55;dist=cfg['cell']*0.12
        shade=h
    else:
        vor=N(nt,'ShaderNodeTexVoronoi',voronoi_dimensions='3D',feature='DISTANCE_TO_EDGE');vor.inputs['Scale'].default_value=1.0;L(sc.outputs[0],vor.inputs['Vector'])
        h=N(nt,'ShaderNodeMapRange',inputs={1:0.0,2:0.12,3:0.0,4:1.0});h.clamp=True;L(vor.outputs['Distance'],h.inputs[0])
        sc2=N(nt,'ShaderNodeVectorMath',operation='SCALE');L(geo.outputs['Position'],sc2.inputs[0]);sc2.inputs['Scale'].default_value=0.4/cfg['cell']
        wr=N(nt,'ShaderNodeTexNoise');wr.inputs['Scale'].default_value=1.0;wr.inputs['Detail'].default_value=4;L(sc2.outputs[0],wr.inputs['Vector'])
        mix=N(nt,'ShaderNodeMath',operation='MULTIPLY_ADD');L(wr.outputs['Fac'],mix.inputs[0]);mix.inputs[1].default_value=0.35;L(h.outputs[0],mix.inputs[2])
        hm=N(nt,'ShaderNodeMath',operation='MULTIPLY');L(mix.outputs[0],hm.inputs[0]);L(fm.outputs['Fac'],hm.inputs[1])
        bstr=0.7;dist=cfg['cell']*0.18
        shade=h
    bump=N(nt,'ShaderNodeBump');bump.inputs['Strength'].default_value=bstr;bump.inputs['Distance'].default_value=dist;L(hm.outputs[0],bump.inputs['Height']);L(bump.outputs[0],bs.inputs['Normal'])
    # colour: vertex colour, slightly darker in the overlaps / crevices
    dk=N(nt,'ShaderNodeMath',operation='MULTIPLY_ADD');L(shade.outputs[0],dk.inputs[0]);dk.inputs[1].default_value=0.16;dk.inputs[2].default_value=0.88
    dkm=N(nt,'ShaderNodeMix',data_type='FLOAT');L(fm.outputs['Fac'],dkm.inputs['Factor']);dkm.inputs['A'].default_value=1.0;L(dk.outputs[0],dkm.inputs['B'])
    cm=N(nt,'ShaderNodeVectorMath',operation='SCALE');L(col.outputs['Color'],cm.inputs[0]);L(dkm.outputs['Result'],cm.inputs['Scale'])
    em=N(nt,'ShaderNodeEmission');L(cm.outputs[0],em.inputs['Color'])
    m['em_color']=cm.name;m['em_node']=em.name;m['rough_src']=col.name
    L(bs.outputs[0],out.inputs['Surface']);nt.nodes['Material Output'].target='ALL'
    m['bsdf']=bs.name;m['out']=out.name
    return m
def bake(hi,lo,m,img,typ,cfg,what=None):
    nt=m.node_tree;out=nt.nodes[m['out']];em=nt.nodes[m['em_node']]
    if typ=='EMIT':
        if what=='rough':nt.links.new(nt.nodes[m['rough_src']].outputs['Alpha'],em.inputs['Color'])
        else:nt.links.new(nt.nodes[m['em_color']].outputs[0],em.inputs['Color'])
        nt.links.new(em.outputs[0],out.inputs['Surface'])
    else:nt.links.new(nt.nodes[m['bsdf']].outputs[0],out.inputs['Surface'])
    lm=lo.data.materials[0];ln=lm.node_tree;tn=ln.nodes.get('BAKE') or ln.nodes.new('ShaderNodeTexImage');tn.name='BAKE';tn.image=img;ln.nodes.active=tn
    select_only(hi,lo);b=bpy.context.scene.render.bake
    b.use_selected_to_active=True;b.cage_extrusion=cfg['cage'];b.max_ray_distance=cfg['cage']*2.5
    t=time.time();bpy.ops.object.bake(type=typ,normal_space='TANGENT',use_selected_to_active=True,cage_extrusion=cfg['cage'],max_ray_distance=cfg['cage']*2.5,margin=6)
    print('  bake',typ,what or '',img.size[0],'%.1fs'%(time.time()-t),flush=True)
def save_img(img,path,fmt='PNG'):
    img.filepath_raw=path;img.file_format=fmt;img.save()
def pbr_material(name,col_img,nrm_img,orm_img,alpha=False,vcol=False,double=False,nscale=1.0):
    m=bpy.data.materials.new(name);m.use_nodes=True;nt=m.node_tree;bs=nt.nodes['Principled BSDF'];L=nt.links.new
    t=N(nt,'ShaderNodeTexImage',image=col_img)
    if vcol:
        vc=N(nt,'ShaderNodeVertexColor',layer_name='Col');mx=N(nt,'ShaderNodeMix',data_type='RGBA',blend_type='MULTIPLY');mx.inputs['Factor'].default_value=1.0
        L(t.outputs['Color'],mx.inputs['A']);L(vc.outputs['Color'],mx.inputs['B']);L(mx.outputs['Result'],bs.inputs['Base Color'])
    else:L(t.outputs['Color'],bs.inputs['Base Color'])
    if alpha:L(t.outputs['Alpha'],bs.inputs['Alpha'])
    if nrm_img:
        tn=N(nt,'ShaderNodeTexImage',image=nrm_img);nm=N(nt,'ShaderNodeNormalMap');nm.inputs['Strength'].default_value=nscale;L(tn.outputs['Color'],nm.inputs['Color']);L(nm.outputs[0],bs.inputs['Normal'])
    if orm_img:
        to=N(nt,'ShaderNodeTexImage',image=orm_img);sp=N(nt,'ShaderNodeSeparateColor');L(to.outputs['Color'],sp.inputs[0]);L(sp.outputs['Green'],bs.inputs['Roughness']);L(sp.outputs['Blue'],bs.inputs['Metallic'])
    else:bs.inputs['Roughness'].default_value=0.7
    m.use_backface_culling=not double
    return m
def orm_from(rough_img,name):
    px=np.array(rough_img.pixels[:],np.float32).reshape(-1,4);o=np.zeros_like(px);o[:,0]=1;o[:,1]=px[:,0];o[:,2]=0;o[:,3]=1
    im=new_img(name,rough_img.size[0],True);im.pixels.foreach_set(o.ravel());return im

def build_armature(name,bones):
    arm=bpy.data.armatures.new(name);ob=bpy.data.objects.new(name,arm);bpy.context.collection.objects.link(ob);select_only(ob)
    bpy.ops.object.mode_set(mode='EDIT');eb={}
    for n,p,h,t in bones:
        b=arm.edit_bones.new(n);b.head=Vector(bl(h));b.tail=Vector(bl(t));b.roll=0;eb[n]=b
    for n,p,h,t in bones:
        if p:eb[n].parent=eb[p];eb[n].use_connect=False
    bpy.ops.object.mode_set(mode='OBJECT');return ob
def seg_dist(P,A,Bv):
    ab=Bv-A;t=np.clip(((P-A)@ab)/max(ab@ab,1e-12),0,1);return np.linalg.norm(P-(A+t[:,None]*ab),axis=1)
def skin_weights(ob,arm_ob,bones,allowed_per_vertex,sigma):
    bd={n:(bl(h),bl(t)) for n,p,h,t in bones};names=[b[0] for b in bones]
    me=ob.data;P=np.array([v.co[:] for v in me.vertices])
    D=np.stack([seg_dist(P,*bd[n]) for n in names],1)
    mask=np.zeros_like(D,bool)
    for i,al in enumerate(allowed_per_vertex):
        for n in al:mask[i,names.index(n)]=True
    D=np.where(mask,D,1e9);dmin=D.min(1,keepdims=True);W=np.exp(-(D-dmin)/sigma)*mask
    # keep the 3 strongest influences
    idx=np.argsort(-W,1)[:,3:];np.put_along_axis(W,idx,0,1);W/=W.sum(1,keepdims=True)
    for j,n in enumerate(names):
        col=W[:,j];nz=np.nonzero(col>0.01)[0]
        if not len(nz):continue
        g=ob.vertex_groups.get(n) or ob.vertex_groups.new(name=n)
        for i in nz:g.add([int(i)],float(col[i]),'REPLACE')
def bind(ob,arm_ob):
    ob.parent=arm_ob;m=ob.modifiers.new('Armature','ARMATURE');m.object=arm_ob
def rigid(ob,bone):
    g=ob.vertex_groups.new(name=bone);g.add(list(range(len(ob.data.vertices))),1.0,'REPLACE')

def eyes(meta,name):
    e=meta['eye'];c=np.array(e['c']);r=e['r'];V=[];F=[];C=[];nu,nv=20,12
    for sx in (1,-1):
        o=len(V);ax=np.array([sx*0.92,0.0,0.39 if name!='turtle' else 0.55]);ax/=np.linalg.norm(ax)
        up=np.array([0,1.0,0]);s1=np.cross(up,ax);s1/=np.linalg.norm(s1);s2=np.cross(ax,s1)
        for j in range(nv+1):
            th=j/nv*np.pi
            for i in range(nu):
                ph=i/nu*2*np.pi;d=ax*np.cos(th)+np.sin(th)*(s1*np.cos(ph)+s2*np.sin(ph))
                V.append(c*np.array([sx,1,1])+d*r)
                a=th/np.pi
                if a<0.16*e['pupil']*2:cc=[0.01,0.01,0.012]
                elif a<0.36:cc=list(np.array(e['iris'])*(0.75+0.5*(a-0.1)))
                else:cc=[0.05,0.045,0.04]
                C.append(cc+[1])
        for j in range(nv):
            for i in range(nu):
                a=o+j*nu+i;b=o+j*nu+(i+1)%nu;F+=[(a,b,b+nu),(a,b+nu,a+nu)]
    ob=mesh_obj(name+'_eyes',np.array(V),np.array(F));point_attr(ob,'Col','FLOAT_COLOR',np.array(C))
    m=bpy.data.materials.new(name+'_eye');m.use_nodes=True;nt=m.node_tree;bs=nt.nodes['Principled BSDF'];vc=N(nt,'ShaderNodeVertexColor',layer_name='Col')
    nt.links.new(vc.outputs['Color'],bs.inputs['Base Color']);bs.inputs['Roughness'].default_value=0.06;bs.inputs['Coat Weight'].default_value=1.0
    ob.data.materials.append(m);return ob

def feather_obj(name,d,ftex):
    ob=mesh_obj(name+'_feathers',d['fv'],d['ff']);me=ob.data
    uv=me.uv_layers.new(name='UVMap');lo=np.zeros(len(me.loops)*2,np.float32);vi=np.zeros(len(me.loops),np.int32);me.loops.foreach_get('vertex_index',vi)
    fuv=d['fuv'][vi];fuv[:,1]=fuv[:,1];uv.data.foreach_set('uv',fuv.ravel())
    col=np.concatenate([d['fcol'],np.ones((len(d['fcol']),1))],1);point_attr(ob,'Col','FLOAT_COLOR',col)
    ob.shape_key_add(name='Basis');k=ob.shape_key_add(name='fold');k.data.foreach_set('co',bl(d['ffold']).astype(np.float32).ravel())
    for j,bn in enumerate(d['fwb']):
        g=ob.vertex_groups.new(name=str(bn));w=d['fw'][:,j];nz=np.nonzero(w>0.01)[0]
        for i in nz:g.add([int(i)],float(w[i]),'REPLACE')
    me.materials.append(pbr_material(name+'_feather',ftex[0],ftex[1],None,alpha=True,vcol=True,double=True,nscale=0.6))
    return ob

def build(kind):
    t0=time.time();reset();cfg=CFG[kind];d=np.load(os.path.join(IN,kind+'.npz'),allow_pickle=True);J=json.load(open(os.path.join(IN,kind+'.json')));bones=J['bones'];meta=J['meta']
    hi=mesh_obj(kind+'_hi',d['v'],d['f']);point_attr(hi,'Col','FLOAT_COLOR',d['col']);point_attr(hi,'fmask','FLOAT',d['fmask'])
    point_attr(hi,'flow','FLOAT_VECTOR',bl(d['flow']))
    hm=hi_material(kind,cfg,scales=(kind=='turtle'));hi.data.materials.append(hm)
    lo=mesh_obj(kind+'_body',d['v'],d['f']);decimate(lo,cfg['tris']/len(d['f']))
    smart_uv(lo)
    res=cfg['res'];ci=new_img(kind+'_body_basecolor',res);ni=new_img(kind+'_body_normal',res,True);ri=new_img(kind+'_rough',res,True)
    tmp=bpy.data.materials.new('tmp');tmp.use_nodes=True;lo.data.materials.append(tmp)
    bake(hi,lo,hm,ci,'EMIT',cfg);bake(hi,lo,hm,ri,'EMIT',cfg,'rough');bake(hi,lo,hm,ni,'NORMAL',cfg)
    oi=orm_from(ri,kind+'_body_orm')
    for im in (ci,ni,oi):save_img(im,os.path.join(IN,im.name+'.png'))
    lo.data.materials.clear();lo.data.materials.append(pbr_material(kind+'_body',ci,ni,oi))
    # part label per low vertex from the nearest high vertex -> allowed bones
    kd=kdtree.KDTree(len(hi.data.vertices))
    for i,v in enumerate(hi.data.vertices):kd.insert(v.co,i)
    kd.balance();parts=d['part'];PB=meta['partBones']
    lod1=lo.copy();lod1.data=lo.data.copy();lod1.name=kind+'_body_LOD1';bpy.context.collection.objects.link(lod1);decimate(lod1,cfg['lod1'])
    arm=build_armature(kind+'_rig',bones)
    sig=0.035*cfg['size']
    for ob in (lo,lod1):
        al=[PB[str(parts[kd.find(v.co)[1]])] for v in ob.data.vertices];skin_weights(ob,arm,bones,al,sig);bind(ob,arm)
    bpy.data.objects.remove(hi,do_unlink=True)
    ey=eyes(meta,kind);rigid(ey,'head');bind(ey,arm)
    objs=[lo,lod1,ey]
    if 'fv' in d.files:
        ft=bpy.data.images.load(os.path.join(TEX,'feather_basecolor.png'));fn=bpy.data.images.load(os.path.join(TEX,'feather_normal.png'));fn.colorspace_settings.name='Non-Color'
        fo=feather_obj(kind,d,(ft,fn));bind(fo,arm);objs.append(fo)
    if 'sv' in d.files:
        so=mesh_obj(kind+'_shell',d['sv'],d['sf']);me=so.data;uv=me.uv_layers.new(name='UVMap');vi=np.zeros(len(me.loops),np.int32);me.loops.foreach_get('vertex_index',vi)
        uv.data.foreach_set('uv',d['suv'][vi].ravel())
        sc=bpy.data.images.load(os.path.join(TEX,'turtle_shell_basecolor.png'));sn=bpy.data.images.load(os.path.join(TEX,'turtle_shell_normal.png'));sn.colorspace_settings.name='Non-Color'
        so_=bpy.data.images.load(os.path.join(TEX,'turtle_shell_orm.png'));so_.colorspace_settings.name='Non-Color'
        me.materials.append(pbr_material('turtle_shell',sc,sn,so_,nscale=1.0));rigid(so,'root');bind(so,arm);objs.append(so)
        so1=so.copy();so1.data=so.data.copy();so1.name='turtle_shell_LOD1';bpy.context.collection.objects.link(so1);decimate(so1,0.3)
        so1.modifiers.clear();bind(so1,arm);objs.append(so1)
    for o in objs:
        if o.data.materials and 'tmp' in [m.name for m in o.data.materials if m]:pass
    bpy.data.materials.remove(tmp)
    arm['legLen']=meta.get('legLen',0)
    path=os.path.join(OUTD,kind+'.glb');select_only(arm,*objs)
    bpy.ops.export_scene.gltf(filepath=path,export_format='GLB',use_selection=True,export_skins=True,export_morph=True,export_morph_normal=True,export_animations=False,
        export_image_format='WEBP',export_image_quality=cfg.get('q',82),export_vertex_color='ACTIVE',export_extras=True,export_yup=True,export_apply=False,export_tangents=False)
    tris={o.name:sum(len(p.vertices)-2 for p in o.data.polygons) for o in objs}
    print('OK',kind,'%.0f KB'%(os.path.getsize(path)/1024),tris,'%.0fs'%(time.time()-t0),flush=True)

kinds=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
for k in (kinds or ['turtle','egret','heron','kingfisher','grebe']):build(k)
