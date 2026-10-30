# v11 精细动物 · stage 1 (venv python): SDF bodies -> marching cubes (high-res, vertex colours, part labels, feather-flow attributes),
# feather cards for wings / tails / plumes (spread pose + folded morph), shell mesh + scute textures for the turtle, feather texture atlas.
# Coordinates here are three.js / glTF: Y up, +Z = forward (head), X = sideways. Units = scene metres (the pond's game scale).
# Output: ../build/animals/<kind>.npz (+ json meta) and ../build/animals/tex/*.png  ->  consumed by animals_blender.py
# usage: .venv/bin/python animals_gen.py [kind ...]
import numpy as np,json,os,sys,time
from skimage import measure
from scipy import ndimage
from PIL import Image
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','build','animals');os.makedirs(OUT+'/tex',exist_ok=True)
RNG=np.random.default_rng(11)

# ------------------------------------------------------------------ SDF primitives (vectorised over p[...,3])
def smin(a,b,k):
    if k<=0: return np.minimum(a,b)
    h=np.clip(0.5+0.5*(b-a)/k,0,1); return b*(1-h)+a*h-k*h*(1-h)
def rotx(a):
    c,s=np.cos(a),np.sin(a); return np.array([[1,0,0],[0,c,-s],[0,s,c]])
def roty(a):
    c,s=np.cos(a),np.sin(a); return np.array([[c,0,s],[0,1,0],[-s,0,c]])
def ell(p,c,r,R=None):
    q=p-np.asarray(c,float)
    if R is not None: q=q@np.asarray(R)          # world -> local (R columns = local axes)
    q=q/np.asarray(r,float); k0=np.linalg.norm(q,axis=-1); k1=np.linalg.norm(q/np.asarray(r,float),axis=-1)+1e-9
    return k0*(k0-1)/k1
def cone(p,a,b,ra,rb,sq=(1,1)):
    # capsule-cone a->b with radii ra->rb; sq squashes the cross-section (x,y scale of the radius in a frame around the axis)
    a=np.asarray(a,float);b=np.asarray(b,float);ab=b-a;L2=ab@ab
    t=np.clip(((p-a)@ab)/L2,0,1); c=a+t[...,None]*ab; d=p-c
    if sq!=(1,1):
        ax=ab/np.sqrt(L2); up=np.array([0,1.0,0]);
        if abs(ax@up)>0.95: up=np.array([0,0,1.0])
        sx=np.cross(up,ax);sx/=np.linalg.norm(sx); sy=np.cross(ax,sx)
        d=np.stack([(d@sx)/sq[0],(d@sy)/sq[1],d@ax],-1); r=(ra+(rb-ra)*t)
        return np.linalg.norm(d,axis=-1)*min(sq)-r*min(sq)
    return np.linalg.norm(d,axis=-1)-(ra+(rb-ra)*t)

class Body:
    """ordered list of primitives, smooth-unioned in order; each has a part label and an AABB for fast slice evaluation"""
    def __init__(s): s.P=[]
    def add(s,part,kind,args,k=0.0,flow=None):
        s.P.append(dict(part=part,kind=kind,args=args,k=k,flow=flow))
    def _bbox(s,pr):
        a=pr['args']
        if pr['kind']=='ell': c=np.asarray(a[0]);r=max(a[1])*1.05;return c-r,c+r
        if pr['kind']=='cone':
            A=np.asarray(a[0]);Bp=np.asarray(a[1]);r=max(a[2],a[3])*max(a[4] if len(a)>4 else (1,1))
            return np.minimum(A,Bp)-r,np.maximum(A,Bp)+r
    def bounds(s,pad=0.02):
        lo=np.min([s._bbox(p)[0] for p in s.P],0)-pad;hi=np.max([s._bbox(p)[1] for p in s.P],0)+pad;return lo,hi
    def prim(s,pr,p):
        a=pr['args']
        if pr['kind']=='ell': return ell(p,*a)
        return cone(p,*a)
    def eval(s,p,labels=False):
        d=np.full(p.shape[:-1],1e3,np.float64);lab=np.zeros(p.shape[:-1],np.int16);dmin=np.full(p.shape[:-1],1e3)
        for i,pr in enumerate(s.P):
            lo,hi=s._bbox(pr);m=pr['k']*2+0.03
            sel=np.all((p>lo-m)&(p<hi+m),axis=-1)
            if not sel.any(): continue
            di=np.full(p.shape[:-1],1e3);di[sel]=s.prim(pr,p[sel])
            d=smin(d,di,pr['k']) if i else di
            if labels:
                upd=di<dmin;dmin[upd]=di[upd];lab[upd]=i
        return (d,lab) if labels else d
    def mesh(s,vox):
        lo,hi=s.bounds();n=np.ceil((hi-lo)/vox).astype(int)+1
        xs=[lo[i]+np.arange(n[i])*vox for i in range(3)];vol=np.zeros(n,np.float32)
        X,Y=np.meshgrid(xs[0],xs[1],indexing='ij')
        for k,z in enumerate(xs[2]):
            vol[:,:,k]=s.eval(np.stack([X,Y,np.full_like(X,z)],-1))
        assert min(vol[0].min(),vol[-1].min(),vol[:,0].min(),vol[:,-1].min(),vol[:,:,0].min(),vol[:,:,-1].min())>0,'surface touches the box'
        v,f,_,_=measure.marching_cubes(vol,0.0,spacing=(vox,)*3);v=v+lo
        _,lab=s.eval(v,labels=True)
        return v.astype(np.float32),f.astype(np.int32),lab   # skimage winding is already outward for inside-negative SDFs

def flow_dir(body,v,lab):
    """feather/scale flow direction per vertex: along each primitive's axis toward its 'flow' end (None -> backwards -Z)"""
    out=np.zeros_like(v);out[:,2]=-1
    for i,pr in enumerate(body.P):
        m=lab==i
        if not m.any(): continue
        f=pr['flow']
        if f is None: continue
        out[m]=np.asarray(f,float)
    # project to the tangent plane later in Blender (normal known there); just normalise here
    return out/np.linalg.norm(out,axis=1,keepdims=True)

# ------------------------------------------------------------------ feather cards
class Feathers:
    """thin cambered cards (double-sided material). Each card: base point, along dir, side dir, length, width, uv region, colour, bone weights,
    plus a folded position computed by a per-animal fold map (shape key 'fold')."""
    def __init__(s): s.V=[];s.F=[];s.UV=[];s.C=[];s.W=[];s.FOLD=[];s.n=0
    def card(s,base,along,side,L,Wd,uvr,col,wfn,foldfn=None,nu=4,nv=7,camber=0.18,droop=0.06,twist=0.0,kind=0):
        base=np.asarray(base,float);a=np.asarray(along,float);a/=np.linalg.norm(a);sd=np.asarray(side,float);sd-=a*(sd@a);sd/=np.linalg.norm(sd)
        nrm=np.cross(sd,a);o=len(s.V)
        for j in range(nv+1):
            t=j/nv;w=Wd*(max(0.0,np.sin(np.pi*min(1,0.12+t*0.95)))**0.6)*(1-0.25*t)+Wd*0.08
            for i in range(nu+1):
                u=i/nu*2-1;tw=twist*t
                pside=sd*np.cos(tw)+nrm*np.sin(tw)
                p=base+a*(L*t)+pside*(u*w*0.5)+nrm*(camber*Wd*(1-u*u)*0.5-droop*L*t*t)
                s.V.append(p);s.UV.append((uvr[0]+(u*0.5+0.5)*(uvr[2]-uvr[0]),uvr[1]+t*(uvr[3]-uvr[1])))
                s.C.append(col);s.W.append(wfn(p,t));s.FOLD.append(foldfn(p,t,kind) if foldfn else p)
        for j in range(nv):
            for i in range(nu):
                q=o+j*(nu+1)+i;s.F+= [(q,q+1,q+nu+2),(q,q+nu+2,q+nu+1)]
        s.n+=1
    def tube(s,pts,radii,uvr,col,wfn,foldfn=None,seg=8,squash=0.45):
        """lofted leading-edge (patagium) tube along a polyline, flattened vertically"""
        pts=[np.asarray(p,float) for p in pts];o=len(s.V);n=len(pts)
        for j,p in enumerate(pts):
            a=(pts[min(n-1,j+1)]-pts[max(0,j-1)]);a/=np.linalg.norm(a);up=np.array([0,1.0,0]);sx=np.cross(up,a);sx/=np.linalg.norm(sx);sy=np.cross(a,sx)
            for i in range(seg+1):
                th=i/seg*2*np.pi;q=p+radii[j]*(np.cos(th)*sx*1.0+np.sin(th)*sy*squash)
                s.V.append(q);s.UV.append((uvr[0]+(i/seg)*(uvr[2]-uvr[0]),uvr[1]+j/(n-1)*(uvr[3]-uvr[1])));s.C.append(col);s.W.append(wfn(q,j/(n-1)))
                s.FOLD.append(foldfn(q,j/(n-1),9) if foldfn else q)
        for j in range(n-1):
            for i in range(seg):
                q=o+j*(seg+1)+i;s.F+=[(q,q+seg+1,q+1),(q+1,q+seg+1,q+seg+2)]
    def arrays(s):
        bones=sorted({b for w in s.W for b in w});idx={b:i for i,b in enumerate(bones)}
        W=np.zeros((len(s.W),len(bones)),np.float32)
        for i,w in enumerate(s.W):
            for b,x in w.items(): W[i,idx[b]]+=x
        W/=W.sum(1,keepdims=True)
        return dict(fv=np.array(s.V,np.float32),ff=np.array(s.F,np.int32),fuv=np.array(s.UV,np.float32),fcol=np.array(s.C,np.float32),
                    ffold=np.array(s.FOLD,np.float32),fw=W,fwb=np.array(bones))

def seg_param(p,a,b):
    a=np.asarray(a,float);b=np.asarray(b,float);ab=b-a;return float(np.clip((np.asarray(p)-a)@ab/(ab@ab),0,1))

# ------------------------------------------------------------------ feather texture atlas (RGBA): [0..0.5] contour / flight feather, [0.5..0.75] lacy plume, [0.75..1] opaque down (tubes)
def feather_atlas(N=512):
    H,Wd=N*2,N;img=np.zeros((H,Wd,4),np.float32);hgt=np.zeros((H,Wd),np.float32)
    yy,xx=np.mgrid[0:H,0:Wd].astype(np.float32)
    # region A: x in [0,0.5W) - flight/contour feather (v along y)
    def vane(x0,x1,lacy=False):
        u=(xx-x0)/(x1-x0)*2-1; v=1-yy/H        # v: 0 base .. 1 tip (image rows top = tip)
        inr=(u>=-1)&(u<=1)
        wprof=np.clip(np.maximum(0,np.sin(np.pi*np.clip(0.1+v*0.95,0,1)))**0.55*(1-0.2*v),0,1)
        au=np.abs(u)
        # barbs: slanted toward the tip, with random splits (gaps) along the edge
        barb=0.5+0.5*np.sin((au*0.9-v*1.0)*np.pi*(70 if not lacy else 26))
        rng=np.random.default_rng(5);gap=ndimage.zoom(rng.random((40,8)),(H/40,(x1-x0)/8),order=1)[:H,:int(x1-x0)]
        G=np.zeros_like(u);G[:,int(x0):int(x0)+gap.shape[1]]=gap
        edge=wprof*(0.96-0.12*(G>0.8)*(au>0.55))
        if lacy: edge=wprof*0.95
        a=np.clip((edge-au)/0.06,0,1)*inr
        rach=np.exp(-(u/0.035)**2)*(v<0.98)
        if lacy:
            a=a*np.clip(barb*1.6-0.35,0,1)*(0.35+0.65*(au<0.5)); a=np.maximum(a,rach*np.clip((1-v)*1.5,0,1))
        down=np.clip((0.16-v)/0.12,0,1)
        lum=0.82+0.1*barb-0.18*au*au+0.14*rach-0.1*down
        return a*inr,lum,barb*(1-rach)+rach*1.5,inr
    for (x0,x1,lacy) in [(0,Wd*0.5,False),(Wd*0.5,Wd*0.75,True)]:
        a,lum,h,inr=vane(x0,x1,lacy);m=inr
        img[...,3]=np.where(m,a,img[...,3]);img[...,0]=np.where(m,lum,img[...,0]);hgt=np.where(m,h*a,hgt)
    m=xx>=Wd*0.75; img[...,3][m]=1; img[...,0][m]=0.9+0.05*np.sin(yy[m]*0.6)*np.sin(xx[m]*0.9)
    hgt[m]=0.5+0.2*np.sin(yy[m]*0.6)
    img[...,1]=img[...,0];img[...,2]=img[...,0]
    # bleed colour into transparent texels (avoids dark fringes with mipmaps)
    rgb=Image.fromarray((np.clip(img[...,:3],0,1)*255).astype(np.uint8));a=Image.fromarray((np.clip(img[...,3],0,1)*255).astype(np.uint8))
    out=rgb.copy();out.putalpha(a);out=out.resize((Wd//2,H//2),Image.LANCZOS);out.save(OUT+'/tex/feather_basecolor.png')
    gy,gx=np.gradient(ndimage.gaussian_filter(hgt,1.0));k=2.5
    n=np.stack([-gx*k,gy*k,np.ones_like(gx)],-1);n/=np.linalg.norm(n,axis=-1,keepdims=True)
    Image.fromarray(((n*0.5+0.5)*255).astype(np.uint8)).resize((Wd//2,H//2),Image.LANCZOS).save(OUT+'/tex/feather_normal.png')
UV_FEATHER=(0.02,0.0,0.48,1.0);UV_PLUME=(0.52,0.0,0.73,1.0);UV_DOWN=(0.78,0.05,0.97,0.95)

# ------------------------------------------------------------------ BIRDS
def smooth_cols(v,f,c,iters):
    """umbrella-average vertex colours over the mesh: soft plumage boundaries instead of voxel stair-steps"""
    from scipy import sparse
    n=len(v);i=np.concatenate([f[:,0],f[:,1],f[:,2],f[:,1],f[:,2],f[:,0]]);j=np.concatenate([f[:,1],f[:,2],f[:,0],f[:,0],f[:,1],f[:,2]])
    A=sparse.csr_matrix((np.ones(len(i)),(i,j)),shape=(n,n));A.data[:]=1;A=A+sparse.identity(n,format='csr')
    A=sparse.diags(1/np.asarray(A.sum(1)).ravel())@A
    for _ in range(iters):c=A@c
    return c
def seat_eye(B,meta,sink=0.1):
    """push the eyeball into the head so only a cap shows (otherwise the far eye pokes through the head silhouette)"""
    e=meta['eye'];c=e['c'];xs=float(body_surface_x(B,np.array([c[1]]),np.array([c[2]]))[0])
    e['c']=[xs-sink*e['r'],c[1],c[2]];return meta
def bird_common(name,B,bones,col_fn,fmask_fn,wing,tail,extra=None,vox=0.0028,meta=None,blur=0.006):
    t=time.time();v,f,lab=B.mesh(vox);print(name,'mc',len(v),'verts',len(f),'tris %.1fs'%(time.time()-t),flush=True)
    parts=np.array([B.P[i]['part'] for i in lab])
    col=col_fn(v,parts);fm=fmask_fn(v,parts);fl=flow_dir(B,v,lab)
    col=smooth_cols(v,f,col,int(round((blur/vox)**2)));meta=seat_eye(B,meta)
    FE=Feathers();wing(FE)
    if tail: tail(FE)
    if extra: extra(FE)
    fa=FE.arrays()
    np.savez_compressed(OUT+'/%s.npz'%name,v=v,f=f,col=col.astype(np.float32),fmask=fm.astype(np.float32),flow=fl.astype(np.float32),part=parts,**fa)
    json.dump(dict(bones=bones,meta=meta or {}),open(OUT+'/%s.json'%name,'w'),indent=1)
    print(name,'feathers',FE.n,'cards',len(fa['fv']),'verts',flush=True)

def body_surface_x(B,y,z,xmax=0.4):
    """half-width of the body at (y,z): bisection along +x of the SDF (used to lay the folded wing on the flank)"""
    y=np.asarray(y,float);z=np.asarray(z,float);lo=np.zeros_like(y);hi=np.full_like(y,xmax)
    inside0=B.eval(np.stack([lo,y,z],-1))<0
    for _ in range(22):
        m=(lo+hi)/2;d=B.eval(np.stack([m,y,z],-1));ins=d<0;lo=np.where(ins,m,lo);hi=np.where(ins,hi,m)
    return np.where(inside0,lo,0.0)

def make_wing(FE,side,S,hum,fore,hand,prim,sec,ter,pcol,ccol,lead_col,uv=UV_FEATHER,fold=None,nprim=10,nsec=12,cov_col=None):
    """spread wing for side (+1 = +X). S shoulder; hum/fore/hand bone vectors (spread pose); prim=(len,width); sec=(len,width)"""
    sx=side;S=np.asarray(S,float);E=S+np.array([hum[0]*sx,hum[1],hum[2]]);Wr=E+np.array([fore[0]*sx,fore[1],fore[2]]);Hn=Wr+np.array([hand[0]*sx,hand[1],hand[2]])
    nm=lambda b:b+('.L' if sx>0 else '.R')
    def wsk(p,t=0):
        # blend weights along the arm by projected position (smooth joints)
        x=abs(p[0]-S[0]);xe=abs(E[0]-S[0]);xw=abs(Wr[0]-S[0])
        def sm(a,b,x):
            u=np.clip((x-a)/(b-a),0,1);return u*u*(3-2*u)
        w2=sm(xe-0.02,xe+0.02,x);w3=sm(xw-0.02,xw+0.02,x)
        return {nm('humerus'):(1-w2),nm('forearm'):w2*(1-w3),nm('hand'):w3}
    ff=(lambda p,t,k:fold(p,t,k,sx)) if fold else None
    back=np.array([0,0,-1.0]);out=np.array([sx,0,0.0]);up=np.array([0,1.0,0])
    lay=0
    def L(k): return np.array([0,-0.0012*k,0])
    # primaries along the hand, fanning from back-outward to nearly along the span
    for i in range(nprim):
        u=i/(nprim-1);base=Wr+(Hn-Wr)*u
        ang=np.radians(18+64*u**1.15);d=back*np.cos(ang)+out*np.sin(ang)
        Lp=prim[0]*(0.86+0.18*np.sin(np.pi*min(1,u*1.15)))
        FE.card(base+L(i)*0.5,d,np.cross(up,d)*sx,Lp,prim[1]*(1-0.25*u),uv,pcol,wsk,ff,camber=0.25,droop=0.03,kind=0)
    # secondaries along the forearm, pointing back
    for i in range(nsec):
        u=i/(nsec-1);base=E+(Wr-E)*u;ang=np.radians(4+12*u);d=back*np.cos(ang)+out*np.sin(ang)
        FE.card(base+np.array([0,0.0015,0])+L(i)*0.3,d,np.cross(up,d)*sx,sec[0]*(1-0.08*u),sec[1],uv,pcol,wsk,ff,camber=0.2,droop=0.02,kind=1)
    # tertials near the elbow / body
    for i in range(4):
        u=i/3;base=S+(E-S)*(0.35+0.65*u);d=back*np.cos(np.radians(-8+6*u))+out*np.sin(np.radians(-8+6*u))
        FE.card(base+np.array([0,0.004,0]),d,np.cross(up,d)*sx,ter[0]*(1.05-0.1*u),ter[1],uv,pcol,wsk,ff,camber=0.2,droop=0.02,kind=2)
    # greater + median coverts (two shorter rows lying over the flight feathers), lesser coverts row
    cc=cov_col if cov_col is not None else ccol
    for row,(fr,ly,n) in enumerate([(0.5,0.006,16),(0.3,0.009,14),(0.17,0.012,12)]):
        for i in range(n):
            u=i/(n-1);base=S+(Hn-S)*(0.08+0.9*u)
            hand_part=np.clip(((base-S)[0]*sx-(Wr-S)[0]*sx)/max(1e-6,(Hn-Wr)[0]*sx),0,1)
            ang=np.radians(6+40*hand_part**1.3);d=back*np.cos(ang)+out*np.sin(ang)
            Lc=(sec[0]*(1-hand_part)+prim[0]*0.7*hand_part)*fr
            c=np.asarray(cc[row] if np.ndim(cc)==2 else cc,float)
            FE.card(base+np.array([0,ly,0])-back*0.004,d,np.cross(up,d)*sx,Lc,sec[1]*(0.95-0.15*row),uv,c,wsk,ff,camber=0.15,droop=0.0,nv=4,nu=3,kind=3+row)
    # leading edge tube (patagium), shoulder -> wrist -> hand
    r0=sec[1]*0.42
    pts=[S,S+(E-S)*0.5,E,E+(Wr-E)*0.5,Wr,Wr+(Hn-Wr)*0.6,Hn];rad=[r0,r0*0.95,r0*0.85,r0*0.7,r0*0.6,r0*0.45,r0*0.25]
    FE.tube(pts,rad,UV_DOWN,lead_col,wsk,ff)
    return E,Wr,Hn

def fold_map(B,S,Lf,drop,tilt,span):
    """spread-wing point -> folded on the flank. s = fraction along the span, c = depth behind the leading edge, y layer -> outward."""
    S=np.asarray(S,float)
    def f(p,t,kind,sx):
        r=np.asarray(p,float)-S;s=np.clip(abs(r[0])/span,0,1.2);c=max(0.0,-r[2])
        z=S[2]-(0.03+0.85*s*Lf)-0.22*c
        y=S[1]+0.008-c*drop-s*0.03+(z-S[2])*tilt+r[1]*0.6
        lay={0:0.0,1:0.0035,2:0.007,3:0.009,4:0.011,5:0.013,9:0.004}.get(kind,0.0)
        x=float(body_surface_x(B,np.array([y]),np.array([z]))[0])
        x=max(x,0.012)+0.006+lay+max(0,r[1])*0.8
        return np.array([sx*x,y,z])
    return f

def catmull(P,R,k):
    P=[np.asarray(p,float) for p in P];P=[2*P[0]-P[1]]+P+[2*P[-1]-P[-2]];out=[];rr=[]
    for i in range(1,len(P)-2):
        for j in range(k):
            t=j/k;p0,p1,p2,p3=P[i-1],P[i],P[i+1],P[i+2]
            out.append(0.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t**3));rr.append(R[i-1]+(R[i]-R[i-1])*t)
    out.append(P[-2]);rr.append(R[-1]);return np.array(out),rr
def egret():
    B=Body();tilt=np.radians(24)
    B.add('body','ell',([0,0.80,0.0],[0.088,0.105,0.235],rotx(-tilt)),0)
    B.add('body','ell',([0,0.855,0.125],[0.078,0.098,0.115]),0.05)
    B.add('body','ell',([0,0.775,-0.165],[0.07,0.06,0.13],rotx(-tilt*0.5)),0.05)
    B.add('tail','cone',([0,0.765,-0.24],[0,0.72,-0.35],0.034,0.012,(1.3,0.6)),0.03,flow=[0,-0.3,-1])
    N=[[0,0.90,0.165],[0,1.02,0.205],[0,1.125,0.17],[0,1.215,0.125],[0,1.315,0.14],[0,1.40,0.195],[0,1.455,0.245]]
    R=[0.045,0.034,0.029,0.026,0.024,0.023,0.022]
    Ns,Rs=catmull(N,R,4)
    for i in range(len(Ns)-1):
        d=Ns[i]-Ns[i+1];B.add('neck','cone',(list(Ns[i]),list(Ns[i+1]),Rs[i],Rs[i+1],(0.85,1.0)),0.07 if i==0 else 0.006,flow=list(d/np.linalg.norm(d)))
    B.add('head','ell',([0,1.475,0.275],[0.029,0.033,0.052],rotx(np.radians(-8))),0.025,flow=[0,0.1,-1])
    B.add('bill','cone',([0,1.47,0.315],[0,1.452,0.49],0.0135,0.0012,(0.75,1.0)),0.008)
    legs={}
    for sx in (1,-1):
        Hh=[0.046*sx,0.73,0.0];A=[0.04*sx,0.44,-0.05];Fp=[0.04*sx,0.03,0.0]
        B.add('thigh','cone',(Hh,[0.044*sx,0.62,-0.025],0.026,0.013),0.04,flow=[0,-1,0])
        B.add('leg','cone',([0.044*sx,0.64,-0.022],A,0.0125,0.0085),0.01)
        B.add('leg','ell',(A,[0.011,0.012,0.012]),0.006)
        B.add('leg','cone',(A,Fp,0.0085,0.0075),0.006)
        for ang,L in ((-38,0.098),(0,0.112),(38,0.098),(180,0.05)):
            a=np.radians(ang)*sx;d=np.array([np.sin(a),0,np.cos(a)]);b0=np.array(Fp)+np.array([0,-0.012,0]);tip=b0+d*L;tip[1]=0.006
            B.add('foot','cone',(list(b0),list(tip),0.0062,0.0032),0.005)
        legs[sx]=(Hh,A,Fp)
    S=[0.072,0.885,0.07]
    def col(v,parts):
        c=np.ones((len(v),4));c[:,:3]=[0.93,0.93,0.9];c[:,3]=0.75
        y=v[:,1]
        c[parts=='bill',:3]=[0.86,0.66,0.12];c[parts=='bill',3]=0.32
        # lores (bare skin between eye and bill) yellow-green
        lo=(parts=='head')&(v[:,2]>0.29)&(np.abs(v[:,0])>0.012);c[lo,:3]=[0.72,0.78,0.3];c[lo,3]=0.4
        legm=np.isin(parts,['leg','foot'])|((parts=='thigh')&(y<0.66))
        c[legm,:3]=[0.035,0.035,0.032];c[legm,3]=0.45
        c[parts=='foot',:3]=[0.62,0.55,0.12]
        c[(parts=='leg')&(y<0.09),:3]=[0.4,0.38,0.1]
        # very subtle cream on the back / pale grey shadowing on the belly
        c[:,:3]*=np.where(np.isin(parts,['body','neck','head','tail','thigh'])[:,None],1-0.04*np.clip((0.78-y)/0.1,0,1)[:,None],1)
        return c
    def fmask(v,parts):return np.isin(parts,['body','neck','head','tail','thigh']).astype(float)*np.where(v[:,1]<0.66,0,1)
    fold=fold_map(B,S,0.42,0.42,0.38,0.52)
    W=np.array([0.95,0.95,0.92])
    def wing(FE):
        for sx in (1,-1):make_wing(FE,sx,[S[0]*sx,S[1],S[2]],(0.15,0.0,-0.02),(0.17,0,0.02),(0.10,0,-0.01),(0.25,0.048),(0.2,0.052),(0.18,0.056),W,W,W,fold=fold)
    def tail(FE):
        for i in range(10):
            a=np.radians(-36+72*i/9);d=np.array([np.sin(a)*0.5,-0.25,-np.cos(a)]);base=np.array([0,0.77,-0.24])
            FE.card(base+np.array([0,0.002*abs(i-4.5),0]),d,[np.cos(a),0,np.sin(a)*0.5],0.15,0.04,UV_FEATHER,W,lambda p,t:{'tail':1},
                    lambda p,t,k,a=a:p if k!=7 else p,camber=0.12,droop=0.02,kind=7)
    def extra(FE):
        # breeding plumes (蓑羽): lacy aigrettes from the back, draping over the tail
        for i in range(14):
            a=np.radians(-28+56*i/13);base=np.array([np.sin(a)*0.04,0.885,-0.0+np.cos(a)*0.01])
            d=np.array([np.sin(a)*0.3,-0.12,-1]);FE.card(base,d,[np.cos(a),0,0],0.36+0.04*np.sin(i*1.7),0.05,UV_PLUME,W*1.03,lambda p,t:{'root':1},camber=0.1,droop=0.13,nv=9,kind=8)
        # nape plumes
        for sx in (1,-1):FE.card([0.006*sx,1.49,0.25],[0.05*sx,-0.25,-1],[1,0,0],0.13,0.014,UV_PLUME,W,lambda p,t:{'head':1},camber=0.05,droop=0.25,nv=6,kind=8)
    bones=[('root',None,[0,0.79,-0.08],[0,0.81,0.06]),('chest','root',[0,0.81,0.06],[0,0.88,0.16]),
           *[('neck%d'%(i+1),'chest' if i==0 else 'neck%d'%i,N[i],N[i+1]) for i in range(6)],('head','neck6',N[6],[0,1.465,0.42]),
           ('tail','root',[0,0.77,-0.2],[0,0.725,-0.36])]
    for sx,n in ((1,'L'),(-1,'R')):
        Hh,A,Fp=legs[sx];bones+= [('tibia.'+n,'root',Hh,A),('tarsus.'+n,'tibia.'+n,A,Fp),('foot.'+n,'tarsus.'+n,Fp,[Fp[0],0.01,0.1])]
        Sx=[S[0]*sx,S[1],S[2]];E=[Sx[0]+0.15*sx,S[1],S[2]-0.02];Wr=[E[0]+0.17*sx,S[1],S[2]];Hn=[Wr[0]+0.1*sx,S[1],S[2]-0.01]
        bones+=[('humerus.'+n,'chest',Sx,E),('forearm.'+n,'humerus.'+n,E,Wr),('hand.'+n,'forearm.'+n,Wr,Hn)]
    partb={'body':['root','chest','neck1','tail','tibia.L','tibia.R'],'neck':['chest','neck1','neck2','neck3','neck4','neck5','neck6','head'],'head':['head','neck6'],'bill':['head'],
           'tail':['tail','root'],'thigh':['tibia.L','tibia.R','root'],'leg':['tibia.L','tarsus.L','tibia.R','tarsus.R'],'foot':['foot.L','foot.R','tarsus.L','tarsus.R']}
    bird_common('egret',B,bones,col,fmask,wing,tail,extra,meta=dict(partBones=partb,legLen=0.73,eye=dict(c=[0.024,1.484,0.29],r=0.0085,iris=[0.95,0.78,0.12],pupil=0.45),feathers='white'))

def heron():
    B=Body();tilt=np.radians(12)
    B.add('body','ell',([0,0.585,0.0],[0.105,0.125,0.245],rotx(-tilt)),0)
    B.add('body','ell',([0,0.63,0.135],[0.095,0.11,0.12]),0.05)
    B.add('body','ell',([0,0.56,-0.17],[0.08,0.07,0.12],rotx(-tilt*0.5)),0.05)
    B.add('tail','cone',([0,0.565,-0.24],[0,0.53,-0.33],0.035,0.014,(1.3,0.6)),0.03,flow=[0,-0.3,-1])
    N=[[0,0.69,0.17],[0,0.745,0.205],[0,0.785,0.2],[0,0.815,0.215],[0,0.835,0.235]];R=[0.062,0.055,0.05,0.047,0.045]
    for i in range(4):
        d=np.array(N[i])-np.array(N[i+1]);B.add('neck','cone',(N[i],N[i+1],R[i],R[i+1],(0.9,1.0)),0.06 if i==0 else 0.025,flow=list(d/np.linalg.norm(d)))
    B.add('head','ell',([0,0.845,0.258],[0.044,0.049,0.068],rotx(np.radians(-6))),0.035,flow=[0,0.1,-1])
    B.add('bill','cone',([0,0.838,0.305],[0,0.818,0.42],0.019,0.0025,(0.78,1.0)),0.01)
    legs={}
    for sx in (1,-1):
        Hh=[0.052*sx,0.52,0.0];A=[0.046*sx,0.27,-0.035];Fp=[0.045*sx,0.03,0.0]
        B.add('thigh','cone',(Hh,[0.05*sx,0.43,-0.02],0.03,0.016),0.04,flow=[0,-1,0])
        B.add('leg','cone',([0.05*sx,0.44,-0.02],A,0.015,0.011),0.01)
        B.add('leg','ell',(A,[0.013,0.014,0.014]),0.006)
        B.add('leg','cone',(A,Fp,0.011,0.009),0.006)
        for ang,L in ((-38,0.085),(0,0.098),(38,0.085),(180,0.045)):
            a=np.radians(ang)*sx;d=np.array([np.sin(a),0,np.cos(a)]);b0=np.array(Fp)+np.array([0,-0.012,0]);tip=b0+d*L;tip[1]=0.006
            B.add('foot','cone',(list(b0),list(tip),0.0068,0.0034),0.005)
        legs[sx]=(Hh,A,Fp)
    S=[0.085,0.67,0.075]
    def col(v,parts):
        c=np.ones((len(v),4));c[:,3]=0.75;y=v[:,1];x=np.abs(v[:,0]);z=v[:,2]
        pale=np.array([0.86,0.87,0.88]);dark=np.array([0.05,0.07,0.085])
        c[:,:3]=pale
        # black crown + mantle (back): top of the body forward of the tail, and the crown of the head
        bt=(parts=='body')&(y>0.585+0.06+(-z)*0.2-x*0.25)&(z>-0.18);c[bt,:3]=dark
        hd=(parts=='head')&(y>0.848-0.0+(0.3-z)*0.05)
        c[hd,:3]=dark
        fh=(parts=='head')&(z>0.30)&(y>0.85)&(x<0.015);c[fh,:3]=[0.92,0.92,0.92]   # white forehead
        nk=(parts=='neck')&(z<0.2)&(y>0.72);c[nk,:3]=dark*1.3
        c[parts=='tail',:3]=[0.45,0.48,0.52]
        c[(parts=='body')&(z<-0.17),:3]=[0.5,0.53,0.57]
        lo=(parts=='head')&(z>0.29)&(x>0.012)&(y<0.85);c[lo,:3]=[0.45,0.55,0.48]   # greenish lores
        c[parts=='bill',:3]=[0.03,0.03,0.035];c[parts=='bill',3]=0.3
        legm=np.isin(parts,['leg','foot'])|((parts=='thigh')&(y<0.45));c[legm,:3]=[0.78,0.66,0.22];c[legm,3]=0.5
        return c
    def fmask(v,parts):return np.isin(parts,['body','neck','head','tail','thigh']).astype(float)*np.where(v[:,1]<0.45,0,1)
    fold=fold_map(B,S,0.36,0.45,0.25,0.46)
    G=np.array([0.5,0.53,0.57]);Gd=np.array([0.43,0.46,0.5])
    def wing(FE):
        for sx in (1,-1):make_wing(FE,sx,[S[0]*sx,S[1],S[2]],(0.13,0,-0.02),(0.15,0,0.02),(0.09,0,-0.01),(0.22,0.05),(0.18,0.055),(0.16,0.058),Gd,G,G,fold=fold,cov_col=[G*1.05,G*1.08,G*1.1])
    def tail(FE):
        for i in range(10):
            a=np.radians(-34+68*i/9);d=np.array([np.sin(a)*0.5,-0.25,-np.cos(a)]);base=np.array([0,0.57,-0.24])
            FE.card(base+np.array([0,0.002*abs(i-4.5),0]),d,[np.cos(a),0,np.sin(a)*0.5],0.12,0.04,UV_FEATHER,G*0.95,lambda p,t:{'tail':1},camber=0.12,droop=0.02,kind=7)
    def extra(FE):
        for k,sx in enumerate((0.6,-0.4,0.0)):   # 2-3 long white nape plumes
            FE.card([0.005*sx,0.88,0.235],[0.08*sx,-0.32,-1],[1,0,0],0.2+0.025*k,0.012,UV_PLUME,np.array([0.97,0.97,0.96]),lambda p,t:{'head':1},camber=0.05,droop=0.22,nv=8,kind=8)
            FE.card([0.005*sx,0.88,0.235],[0.08*sx,-0.32,-1],[1,0,0],0.2+0.025*k,0.006,UV_FEATHER,np.array([0.97,0.97,0.96]),lambda p,t:{'head':1},camber=0.05,droop=0.22,nv=8,kind=8)
    bones=[('root',None,[0,0.58,-0.08],[0,0.6,0.06]),('chest','root',[0,0.6,0.06],[0,0.67,0.16]),
           *[('neck%d'%(i+1),'chest' if i==0 else 'neck%d'%i,N[i],N[i+1]) for i in range(4)],('head','neck4',N[4],[0,0.83,0.36]),('tail','root',[0,0.57,-0.2],[0,0.535,-0.33])]
    for sx,n in ((1,'L'),(-1,'R')):
        Hh,A,Fp=legs[sx];bones+= [('tibia.'+n,'root',Hh,A),('tarsus.'+n,'tibia.'+n,A,Fp),('foot.'+n,'tarsus.'+n,Fp,[Fp[0],0.01,0.09])]
        Sx=[S[0]*sx,S[1],S[2]];E=[Sx[0]+0.13*sx,S[1],S[2]-0.02];Wr=[E[0]+0.15*sx,S[1],S[2]];Hn=[Wr[0]+0.09*sx,S[1],S[2]-0.01]
        bones+=[('humerus.'+n,'chest',Sx,E),('forearm.'+n,'humerus.'+n,E,Wr),('hand.'+n,'forearm.'+n,Wr,Hn)]
    partb={'body':['root','chest','neck1','tail','tibia.L','tibia.R'],'neck':['chest','neck1','neck2','neck3','neck4','head'],'head':['head','neck4'],'bill':['head'],
           'tail':['tail','root'],'thigh':['tibia.L','tibia.R','root'],'leg':['tibia.L','tarsus.L','tibia.R','tarsus.R'],'foot':['foot.L','foot.R','tarsus.L','tarsus.R']}
    bird_common('heron',B,bones,col,fmask,wing,tail,extra,meta=dict(partBones=partb,legLen=0.52,eye=dict(c=[0.033,0.856,0.283],r=0.0115,iris=[0.85,0.05,0.04],pupil=0.42)))

def kingfisher():
    B=Body();tilt=np.radians(52)
    B.add('body','ell',([0,0.08,0.0],[0.033,0.04,0.064],rotx(-tilt)),0)
    B.add('body','ell',([0,0.098,0.022],[0.032,0.036,0.04]),0.02)
    B.add('neck','ell',([0,0.128,0.03],[0.03,0.03,0.032]),0.02,flow=[0,-1,-0.4])
    B.add('head','ell',([0,0.148,0.04],[0.033,0.031,0.04],rotx(np.radians(-5))),0.022,flow=[0,0.15,-1])
    B.add('bill','cone',([0,0.145,0.07],[0,0.137,0.158],0.0115,0.001,(0.72,1.0)),0.005)
    B.add('tail','cone',([0,0.045,-0.04],[0,0.012,-0.085],0.017,0.009,(1.4,0.55)),0.014,flow=[0,-0.6,-1])
    legs={}
    for sx in (1,-1):
        Hh=[0.013*sx,0.05,0.012];A=[0.013*sx,0.03,0.018];Fp=[0.013*sx,0.012,0.02]
        B.add('leg','cone',(Hh,A,0.0055,0.0042),0.004);B.add('leg','cone',(A,Fp,0.0042,0.0038),0.002)
        for ang,L in ((-25,0.022),(0,0.026),(20,0.024),(180,0.014)):
            a=np.radians(ang)*sx;d=np.array([np.sin(a),0,np.cos(a)]);b0=np.array(Fp);tip=b0+d*L;tip[1]=0.004
            B.add('foot','cone',(list(b0),list(tip),0.0032,0.002),0.002)
        legs[sx]=(Hh,A,Fp)
    S=[0.026,0.112,0.022]
    def col(v,parts):
        c=np.ones((len(v),4));c[:,3]=0.55;y=v[:,1];x=np.abs(v[:,0]);z=v[:,2]
        orange=np.array([0.86,0.38,0.1]);teal=np.array([0.04,0.33,0.42]);cyan=np.array([0.1,0.68,0.85]);white=np.array([0.95,0.93,0.86])
        c[:,:3]=orange
        # upperparts: teal-blue with a bright cyan stripe down the back/rump
        R=rotx(-tilt);q=(v-np.array([0,0.08,0.0]))@R            # body frame: q[:,1] = 'up' away from the belly
        up=(parts=='body')&(q[:,1]>-0.004+q[:,0]**2*4)
        c[up,:3]=teal;c[up&(x<0.011),:3]=cyan
        c[parts=='tail',:3]=teal*0.9
        hd=np.isin(parts,['head','neck'])
        crown=hd&(y>0.149+(z-0.04)*-0.05)
        bars=(np.sin(z*900+np.sin(x*400))>0.55)
        c[crown,:3]=np.where(bars[crown,None],[0.32,0.74,0.86],teal)
        # orange ear patch behind the eye, white throat + white neck patch, blue moustache stripe
        ear=hd&(y<0.15)&(y>0.132)&(z<0.05)&(z>0.0)&(x>0.018);c[ear,:3]=orange*1.05
        mou=hd&(y<0.136)&(y>0.124)&(z>0.03)&(x>0.012);c[mou,:3]=teal
        thr=hd&(y<0.124)&(z>0.035);c[thr,:3]=white
        npatch=hd&(y>0.118)&(y<0.142)&(z<0.012)&(z>-0.012)&(x>0.016);c[npatch,:3]=white
        c[(parts=='body')&(~up)&(z>0.03)&(y>0.105),:3]=orange*1.04
        c[parts=='bill',:3]=[0.03,0.03,0.035];c[parts=='bill',3]=0.28
        lb=(parts=='bill')&(v[:,1]<0.141)&(v[:,2]<0.12);c[lb,:3]=[0.55,0.12,0.06]     # reddish base of the lower mandible (female-ish touch)
        c[np.isin(parts,['leg','foot']),:3]=[0.85,0.22,0.12];c[np.isin(parts,['leg','foot']),3]=0.45
        return c
    def fmask(v,parts):return np.isin(parts,['body','neck','head','tail']).astype(float)
    fold=fold_map(B,S,0.095,0.55,0.8,0.16)
    T=np.array([0.05,0.38,0.47]);T2=np.array([0.07,0.45,0.52])
    def wing(FE):
        for sx in (1,-1):make_wing(FE,sx,[S[0]*sx,S[1],S[2]],(0.04,0,-0.006),(0.045,0,0.005),(0.03,0,-0.004),(0.07,0.017),(0.055,0.018),(0.05,0.019),T*0.85,T2,T2,fold=fold,nprim=9,nsec=10,
                                cov_col=[T2*1.15,np.array([0.12,0.55,0.62]),np.array([0.15,0.6,0.66])])
    def tail(FE):
        for i in range(8):
            a=np.radians(-18+36*i/7);d=np.array([np.sin(a)*0.4,-0.75,-0.66]);base=np.array([0,0.05,-0.035])
            FE.card(base,d,[np.cos(a),0,0],0.05,0.016,UV_FEATHER,np.array([0.05,0.3,0.42]),lambda p,t:{'tail':1},camber=0.12,droop=0.01,kind=7,nv=5,nu=3)
    bones=[('root',None,[0,0.06,-0.03],[0,0.09,0.01]),('chest','root',[0,0.09,0.01],[0,0.115,0.03]),('neck1','chest',[0,0.115,0.03],[0,0.135,0.036]),
           ('head','neck1',[0,0.135,0.036],[0,0.14,0.15]),('tail','root',[0,0.05,-0.035],[0,0.012,-0.085])]
    for sx,n in ((1,'L'),(-1,'R')):
        Hh,A,Fp=legs[sx];bones+=[('tibia.'+n,'root',Hh,A),('tarsus.'+n,'tibia.'+n,A,Fp),('foot.'+n,'tarsus.'+n,Fp,[Fp[0],0.004,0.04])]
        Sx=[S[0]*sx,S[1],S[2]];E=[Sx[0]+0.04*sx,S[1],S[2]-0.006];Wr=[E[0]+0.045*sx,S[1],S[2]-0.001];Hn=[Wr[0]+0.03*sx,S[1],S[2]-0.005]
        bones+=[('humerus.'+n,'chest',Sx,E),('forearm.'+n,'humerus.'+n,E,Wr),('hand.'+n,'forearm.'+n,Wr,Hn)]
    partb={'body':['root','chest','tail'],'neck':['chest','neck1','head'],'head':['head','neck1'],'bill':['head'],'tail':['tail','root'],
           'leg':['tibia.L','tarsus.L','tibia.R','tarsus.R'],'foot':['foot.L','foot.R','tarsus.L','tarsus.R']}
    bird_common('kingfisher',B,bones,col,fmask,wing,tail,None,vox=0.0011,meta=dict(partBones=partb,legLen=0.0,eye=dict(c=[0.026,0.152,0.058],r=0.0068,iris=[0.05,0.04,0.035],pupil=0.6)))

def grebe():
    B=Body()
    B.add('body','ell',([0,0.056,0.0],[0.075,0.064,0.098]),0)
    B.add('body','ell',([0,0.076,-0.058],[0.066,0.062,0.062]),0.04,flow=[0,0.2,-1])      # fluffy powder-puff rear
    B.add('body','ell',([0,0.062,0.07],[0.064,0.058,0.065]),0.04)
    B.add('neck','cone',([0,0.085,0.085],[0,0.132,0.108],0.034,0.028),0.035,flow=[0,-1,-0.3])
    B.add('head','ell',([0,0.153,0.122],[0.03,0.031,0.038],rotx(np.radians(-4))),0.02,flow=[0,0.15,-1])
    B.add('bill','cone',([0,0.148,0.152],[0,0.142,0.19],0.0088,0.0012,(0.78,1.0)),0.005)
    def col(v,parts):
        c=np.ones((len(v),4));c[:,3]=0.7;y=v[:,1];x=np.abs(v[:,0]);z=v[:,2]
        dark=np.array([0.13,0.095,0.07]);chest=np.array([0.52,0.19,0.09]);flank=np.array([0.33,0.24,0.16]);buff=np.array([0.62,0.52,0.4])
        c[:,:3]=flank
        c[(parts=='body')&(y>0.068+0.4*x**2*20),:3]=dark
        c[(parts=='body')&(z<-0.07),:3]=buff
        c[(parts=='body')&(z<-0.07)&(y>0.1),:3]=buff*0.75
        c[(parts=='body')&(y<0.02),:3]=[0.55,0.5,0.45]
        nk=np.isin(parts,['neck','head'])
        c[nk,:3]=chest
        c[nk&(y>0.148+(0.12-z)*0.12),:3]=dark          # dark crown / hind-neck
        c[nk&(z<0.095)&(y>0.11),:3]=dark
        c[(parts=='head')&(y<0.14)&(z>0.13),:3]=dark*1.2   # dark chin
        c[parts=='bill',:3]=[0.06,0.05,0.045];c[parts=='bill',3]=0.3
        gape=(parts=='bill')&(z<0.162)&(y<0.15);c[gape,:3]=[0.96,0.9,0.42]
        return c
    def fmask(v,parts):return np.isin(parts,['body','neck','head']).astype(float)
    S=[0.05,0.088,0.035]
    fold=fold_map(B,S,0.1,0.5,0.1,0.15)
    Bn=np.array([0.27,0.2,0.14])
    def wing(FE):
        for sx in (1,-1):make_wing(FE,sx,[S[0]*sx,S[1],S[2]],(0.04,0,-0.005),(0.045,0,0.004),(0.028,0,-0.004),(0.065,0.018),(0.05,0.019),(0.045,0.02),Bn,Bn*1.1,Bn,fold=fold,nprim=9,nsec=10)
    # flank plumage cards over the folded wing (the grebe's wings hide under its fluffed flanks)
    def extra(FE):
        for sx in (1,-1):
            for i in range(9):
                u=i/8;z=0.05-0.15*u;y=0.06+0.012*np.sin(np.pi*u);x=float(body_surface_x(B,np.array([y]),np.array([z]))[0])
                FE.card([sx*(x-0.004),y+0.012,z],[0,-0.25,-1],[0,1,0],0.05,0.035,UV_FEATHER,np.array([0.36,0.26,0.17]),lambda p,t:{'root':1},camber=-0.1,droop=-0.04,nv=4,nu=3,kind=6)
    bones=[('root',None,[0,0.055,-0.06],[0,0.06,0.05]),('chest','root',[0,0.06,0.05],[0,0.085,0.085]),('neck1','chest',[0,0.085,0.085],[0,0.132,0.108]),
           ('head','neck1',[0,0.132,0.108],[0,0.145,0.19])]
    for sx,n in ((1,'L'),(-1,'R')):
        Sx=[S[0]*sx,S[1],S[2]];E=[Sx[0]+0.04*sx,S[1],S[2]-0.005];Wr=[E[0]+0.045*sx,S[1],S[2]-0.001];Hn=[Wr[0]+0.028*sx,S[1],S[2]-0.005]
        bones+=[('humerus.'+n,'chest',Sx,E),('forearm.'+n,'humerus.'+n,E,Wr),('hand.'+n,'forearm.'+n,Wr,Hn)]
    partb={'body':['root','chest'],'neck':['chest','neck1','head'],'head':['head','neck1'],'bill':['head']}
    bird_common('grebe',B,bones,col,fmask,wing,None,extra,vox=0.0013,meta=dict(partBones=partb,legLen=0.0,eye=dict(c=[0.025,0.161,0.135],r=0.0065,iris=[0.92,0.84,0.38],pupil=0.4)))

# ------------------------------------------------------------------ TURTLE (中华草龟 Mauremys reevesii)
TB=0.25   # half carapace length
def tw(z):  # half width of the carapace outline at z (slightly wider behind)
    zz=np.clip(np.abs(z)/TB,0,1);return 0.182*(1-zz**2.6)**(1/2.6)*(1+0.05*np.clip(-z/TB,0,1))
def shell_plan(N=1024):
    """scute map in plan space: u = x/(2*0.2)+0.5, v = z/(2*TB*1.04)+0.5 -> label image, seam distance, ring field"""
    yy,xx=np.mgrid[0:N,0:N].astype(np.float64)/N
    x=(xx-0.5)*0.4;z=(0.5-yy)*2*TB*1.04            # image top = front (+z)
    w=tw(z)+1e-6;un=x/w;vn=z/TB;rho=np.sqrt(np.clip(np.abs(un),0,None)**2.6+np.clip(np.abs(vn),0,None)**2.6)**(1/2.6)
    lab=np.full((N,N),-1,int)
    # marginals: ring rho in [0.86, 1.0] split into 24 sectors + nuchal at the front
    ang=np.arctan2(un,vn)
    ring=(rho>0.855)&(rho<=1.0)
    sec=np.floor((ang+np.pi)/(2*np.pi)*24).astype(int)%24
    lab[ring]=100+sec[ring]
    nuchal=ring&(np.abs(ang)<np.pi/24*0.6);lab[nuchal]=99
    inner=rho<=0.855
    seeds=[(0,0.66),(0,0.34),(0,0.0),(0,-0.33),(0,-0.64)]+[(s*0.6,v) for s in (1,-1) for v in (0.52,0.18,-0.17,-0.5)]
    sw=[1.0]*5+[1.12]*8
    d=np.stack([np.hypot((un-sx)*0.95,(vn-sv)*1.25)/k for (sx,sv),k in zip(seeds,sw)],-1)
    li=np.argmin(d,-1);lab[inner]=li[inner]
    out=rho>1.0
    seam=np.zeros((N,N),bool)
    for dy,dx in ((0,1),(1,0)):
        a=lab;b=np.roll(lab,-dy,0) if dy else np.roll(lab,-dx,1);seam|=(a!=b)
    dist=ndimage.distance_transform_edt(~seam)/N   # in uv units
    return lab,dist,rho,un,vn,out,x,z
def turtle_textures():
    N=1024;lab,dist,rho,un,vn,out,x,z=shell_plan(N)
    rng=np.random.default_rng(3)
    # per-scute max distance -> normalised ring field (growth annuli follow the scute outline)
    lab2=np.where(lab<0,999,lab);ids=np.unique(lab2)
    mx=ndimage.maximum(dist,lab2,ids);mxm=dict(zip(ids,mx));M=np.vectorize(mxm.get)(lab2)
    rn=dist/np.maximum(M,1e-4)
    rings=0.5+0.5*np.sin(rn*np.pi*2*7+rng.random()*3)
    noise=ndimage.gaussian_filter(rng.random((N,N)),2.0);noise=(noise-noise.mean())/noise.std()
    big=ndimage.gaussian_filter(rng.random((N,N)),24);big=(big-big.mean())/big.std()
    base=np.array([0.085,0.066,0.034]);light=np.array([0.25,0.19,0.085]);seamc=np.array([0.025,0.02,0.012])
    t=np.clip(1-rn,0,1)**2.5*0.85+rings*0.12*(rn<0.75)
    C=base[None,None]*(1+0.12*big[...,None]+0.05*noise[...,None])+(light-base)[None,None]*t[...,None]
    keel=np.exp(-(un/0.06)**2)*(rho<0.86)+np.exp(-((np.abs(un)-0.6)/0.05)**2)*(rho<0.8)*0.5
    C=C*(1+0.25*keel[...,None])
    s=np.exp(-dist*N/2.2);C=C*(1-s[...,None])+seamc*s[...,None]
    # plastron (right half of the atlas): yellow with a big dark blotch on every scute
    pl_lab=(np.floor((vn+1)/2*6).astype(int)*2+(un>0)).clip(0,20)
    pseam=np.zeros((N,N),bool)
    for ax in (0,1): pseam|=pl_lab!=np.roll(pl_lab,1,ax)
    pd=ndimage.distance_transform_edt(~pseam)/N
    pl_id=np.unique(pl_lab);pmx=dict(zip(pl_id,ndimage.maximum(pd,pl_lab,pl_id)));pM=np.vectorize(pmx.get)(pl_lab);prn=pd/np.maximum(pM,1e-4)
    yel=np.array([0.62,0.5,0.22]);blot=np.array([0.12,0.08,0.04])
    pn=ndimage.gaussian_filter(rng.random((N,N)),10);pn=(pn-pn.mean())/pn.std()
    bl=np.clip((prn-0.38+0.18*pn)*5,0,1)
    P=yel*(1+0.08*noise[...,None])*(1-bl[...,None])+blot*bl[...,None]
    ps=np.exp(-pd*N/2.0);P=P*(1-ps[...,None])+np.array([0.2,0.15,0.07])*ps[...,None]
    # pack: left half carapace (x scaled into 0..0.5), right half plastron
    def half(A):return np.array(Image.fromarray((np.clip(A,0,1)**(1/2.2)*255).astype(np.uint8)).resize((N//2,N)))
    col=np.concatenate([half(C),half(P)],1)
    Image.fromarray(col).save(OUT+'/tex/turtle_shell_basecolor.png')
    # height -> normal; roughness (wet-ish, smoother on the worn ridges)
    h=-1.6*np.exp(-dist*N/2.5)+0.12*rings*(rn<0.8)+0.1*noise+0.3*np.clip(1-rn,0,1)
    hp=-1.2*np.exp(-pd*N/2.5)+0.08*noise
    def nmap(h,k):
        gy,gx=np.gradient(ndimage.gaussian_filter(h,0.8));n=np.stack([-gx*k,gy*k,np.ones_like(gx)],-1);n/=np.linalg.norm(n,axis=-1,keepdims=True);return n*0.5+0.5
    nrm=np.concatenate([half(nmap(h,6)**2.2),half(nmap(hp,6)**2.2)],1)
    Image.fromarray(nrm).save(OUT+'/tex/turtle_shell_normal.png')
    r=np.clip(0.42+0.12*noise-0.12*keel-0.08*t,0.15,0.8);rp=np.clip(0.55+0.08*noise,0.2,0.9)
    rr=np.concatenate([half(r**2.2),half(rp**2.2)],1)
    orm=np.stack([np.full_like(rr,255),rr,np.zeros_like(rr)],-1).astype(np.uint8)
    Image.fromarray(orm).save(OUT+'/tex/turtle_shell_orm.png')

def shell_mesh():
    """closed shell: carapace dome + rim lip + plastron with bridges. UV: carapace -> left half, plastron -> right half."""
    NR,NT=30,96;V=[];UV=[];F=[]
    H=0.1;yb=0.03   # plastron bottom
    def top(r,th):
        vn=np.cos(th)*r;un=np.sin(th)*r;z=vn*TB;x=un*tw(z)
        h=H*np.clip(1-r**2.2,0,1)**0.62
        h+=0.006*np.exp(-(x/0.02)**2)*(1-r)+0.004*np.exp(-((np.abs(x)-0.6*tw(z))/0.02)**2)*(1-r)
        if z<-0.12*TB: h+=0.012*np.clip((r-0.75)/0.25,0,1)*np.clip((-z-0.12*TB)/(0.88*TB),0,1)   # rear marginals flare up a bit
        y=yb+0.045+h-0.02*r**6
        # rear serration
        if z<0: x*=1+0.015*np.clip(r-0.9,0,1)*10*np.abs(np.sin(th*12))
        return np.array([x,y,z])
    def uvc(p):return ((p[0]/0.4+0.5)*0.5,(p[2]/(2*TB*1.04)+0.5))
    # marginal band r in [RM,1]: spread its texels evenly along the steep profile arc instead of the plan projection
    RM=0.855;rs=np.linspace(RM,1,64)
    def uvr(r,th):
        if r<=RM:return uvc(top(max(r,1e-4),th))
        P=np.array([top(x,th) for x in rs]);s=np.concatenate([[0],np.cumsum(np.linalg.norm(np.diff(P,axis=0),axis=1))]);s/=s[-1]
        rr=RM+(1-RM)*np.interp(r,rs,s);return uvc(top(rr,th))
    idx={}
    def add(p,uv):V.append(p);UV.append(uv);return len(V)-1
    # carapace (r from 0 to 1)
    for i in range(NR+1):
        r=i/NR
        for j in range(NT):
            th=j/NT*2*np.pi;p=top(max(r,1e-4),th);idx[('c',i,j)]=add(p,uvr(r,th))
    for i in range(NR):
        for j in range(NT):
            a=idx[('c',i,j)];b=idx[('c',i+1,j)];c=idx[('c',i+1,(j+1)%NT)];d=idx[('c',i,(j+1)%NT)];F+=[(a,d,c),(a,c,b)]
    # rim lip: curl under (3 rings), then underside going in to r=0.86 (dark underside of the marginals)
    rings=[(1.0,-0.012,1.004),(1.0,-0.022,0.99),(0.93,-0.024,0.93),(0.86,-0.018,0.86)]
    prev=[idx[('c',NR,j)] for j in range(NT)]
    for k,(rr,dy,sc) in enumerate(rings):
        cur=[]
        for j in range(NT):
            th=j/NT*2*np.pi;p=top(1.0,th).copy();p[0]*=sc;p[2]*=sc;p[1]+=dy;cur.append(add(p,uvc(p)))
        for j in range(NT):
            a=prev[j];b=cur[j];c=cur[(j+1)%NT];d=prev[(j+1)%NT];F+=[(a,d,c),(a,c,b)]
        prev=cur
    # plastron: flat oval plate (front + rear lobes shorter than the carapace), joined to the rim underside by side bridges
    def pl(r,th):
        vn=np.cos(th)*r;un=np.sin(th)*r;z=vn*TB*0.9;x=un*tw(z)*0.88
        if abs(z)>0.18: x*=0.9
        return np.array([x,yb+0.004*r*r,z+(-0.01 if z<0 else 0)])
    def uvp(p):return (0.5+(p[0]/0.4+0.5)*0.5,(p[2]/(2*TB*1.04)+0.5))
    NP=18;pid={}
    for i in range(NP+1):
        for j in range(NT):
            th=j/NT*2*np.pi;p=pl(max(i/NP,1e-4),th);pid[(i,j)]=add(p,uvp(p))
    for i in range(NP):
        for j in range(NT):
            a=pid[(i,j)];b=pid[(i+1,j)];c=pid[(i+1,(j+1)%NT)];d=pid[(i,(j+1)%NT)];F+=[(a,c,d),(a,b,c)]
    # plastron edge thickness ring
    top_ring=[]
    for j in range(NT):
        th=j/NT*2*np.pi;p=pl(1.0,th).copy();p[1]+=0.014;top_ring.append(add(p,uvp(p)))
    for j in range(NT):
        a=pid[(NP,j)];b=top_ring[j];c=top_ring[(j+1)%NT];d=pid[(NP,(j+1)%NT)];F+=[(a,c,b),(a,d,c)]
    # bridges: connect plastron top ring to the carapace underside ring at the sides (|sin th| large, both sides)
    for j in range(NT):
        th=j/NT*2*np.pi;th2=(j+1)/NT*2*np.pi
        if abs(np.sin(th))>0.86 and abs(np.sin(th2))>0.86:
            a=top_ring[j];b=top_ring[(j+1)%NT];c=prev[(j+1)%NT];d=prev[j];F+=[(a,b,c),(a,c,d)]
    return np.array(V,np.float32),np.array(F,np.int32)[:,::-1].copy(),np.array(UV,np.float32)   # winding above is inward -> flip to outward

def turtle():
    turtle_textures()
    sv,sf,suv=shell_mesh();print('shell',len(sv),'verts',len(sf),'tris',flush=True)
    B=Body()
    B.add('torso','ell',([0,0.075,0.0],[0.15,0.045,0.2]),0)
    B.add('neck','cone',([0,0.07,0.12],[0,0.078,0.265],0.036,0.03,(1.0,0.85)),0.04,flow=[0,0,-1])
    B.add('head','ell',([0,0.085,0.29],[0.031,0.028,0.043]),0.03,flow=[0,0,-1])
    B.add('head','cone',([0,0.083,0.31],[0,0.078,0.343],0.024,0.011,(1.0,0.82)),0.018)
    legs={}
    for sx in (1,-1):
        sh=[0.11*sx,0.07,0.13];el=[0.172*sx,0.048,0.172];wr=[0.198*sx,0.025,0.205];ft=[0.21*sx,0.012,0.232]
        B.add('fleg','cone',(sh,el,0.035,0.029,(1.0,0.75)),0.03,flow=[sx,0,0]);B.add('fleg','cone',(el,wr,0.029,0.023,(1.0,0.65)),0.012,flow=[sx*0.3,-0.3,0.9])
        B.add('fleg','ell',(ft,[0.03,0.011,0.032],roty(np.radians(-25*sx))),0.012)
        for k in range(5):
            a=np.radians(-50+25*k)*sx+np.radians(-20*sx);d=np.array([np.sin(a),-0.15,np.cos(a)]);b0=np.array(ft)+d*0.024;B.add('claw','cone',(list(b0),list(b0+d*0.022),0.0042,0.0008),0.003)
        hp=[0.105*sx,0.065,-0.14];kn=[0.17*sx,0.042,-0.168];an=[0.19*sx,0.02,-0.212];hf=[0.198*sx,0.011,-0.242]
        B.add('hleg','cone',(hp,kn,0.036,0.028,(1.0,0.72)),0.03,flow=[sx,0,0]);B.add('hleg','cone',(kn,an,0.028,0.02,(1.0,0.65)),0.012,flow=[0,-0.3,-1])
        B.add('hleg','ell',(hf,[0.03,0.01,0.038],roty(np.radians(18*sx))),0.012)
        for k in range(4):
            a=np.radians(180+35-23*k)*sx;d=np.array([np.sin(a)*sx*sx,-0.15,np.cos(a)]);b0=np.array(hf)+d*0.03;B.add('claw','cone',(list(b0),list(b0+d*0.018),0.0038,0.0008),0.003)
        legs[sx]=(sh,el,wr,ft,hp,kn,an,hf)
    B.add('tail','cone',([0,0.07,-0.19],[0,0.04,-0.3],0.022,0.004),0.02,flow=[0,0,1])
    t=time.time();v,f,lab=B.mesh(0.0019);print('turtle skin mc',len(v),len(f),'%.1fs'%(time.time()-t),flush=True)
    parts=np.array([B.P[i]['part'] for i in lab])
    c=np.ones((len(v),4));c[:,3]=0.5;y=v[:,1];x=v[:,0];z=v[:,2]
    base=np.array([0.17,0.18,0.12]);yel=np.array([0.55,0.58,0.22])
    c[:,:3]=base
    hn=np.isin(parts,['head','neck'])
    # yellow-green stripes running along the sides of the head and neck, lighter throat
    ph=(y-0.082+np.abs(x)*0.25)*260+np.sin(z*60)*0.8
    stripe=hn&(np.abs(np.sin(ph))<0.28)&(np.abs(x)>0.012)
    c[stripe,:3]=yel
    thr=hn&(y<0.068);c[thr,:3]=[0.5,0.48,0.28]
    c[hn&(y>0.1)&(np.abs(x)<0.014),:3]=base*0.8
    mouth=(parts=='head')&(z>0.3)&(np.abs(y-0.072+(z-0.3)*0.1)<0.0016);c[mouth,:3]=[0.05,0.05,0.03]
    c[np.isin(parts,['fleg','hleg']),:3]=base*1.05
    under=np.isin(parts,['fleg','hleg'])&(y<0.009);c[under,:3]=[0.3,0.28,0.16]
    c[parts=='claw',:3]=[0.62,0.55,0.38];c[parts=='claw',3]=0.35
    c[parts=='tail',:3]=base
    c[parts=='torso',:3]=[0.12,0.12,0.08]
    c=smooth_cols(v,f,c,6)
    fm=np.where(np.isin(parts,['fleg','hleg']),1.0,np.where(np.isin(parts,['neck','tail']),0.6,np.where(parts=='head',0.25,0.0)))
    fl=flow_dir(B,v,lab)
    bones=[('root',None,[0,0.08,-0.06],[0,0.08,0.06]),('neck1','root',[0,0.07,0.1],[0,0.074,0.19]),('neck2','neck1',[0,0.074,0.19],[0,0.08,0.255]),
           ('head','neck2',[0,0.08,0.255],[0,0.078,0.345]),('tail','root',[0,0.07,-0.18],[0,0.04,-0.3])]
    for sx,n in ((1,'L'),(-1,'R')):
        sh,el,wr,ft,hp,kn,an,hf=legs[sx]
        bones+=[('fl_up.'+n,'root',sh,el),('fl_lo.'+n,'fl_up.'+n,el,wr),('fl_ft.'+n,'fl_lo.'+n,wr,list(np.array(ft)+np.array([0.01*sx,0,0.03]))),
                ('hl_up.'+n,'root',hp,kn),('hl_lo.'+n,'hl_up.'+n,kn,an),('hl_ft.'+n,'hl_lo.'+n,an,list(np.array(hf)+np.array([0.005*sx,0,-0.035])))]
    partb={'torso':['root','neck1','fl_up.L','fl_up.R','hl_up.L','hl_up.R','tail'],'neck':['root','neck1','neck2','head'],'head':['head','neck2'],
           'fleg':['root','fl_up.L','fl_lo.L','fl_ft.L','fl_up.R','fl_lo.R','fl_ft.R'],'hleg':['root','hl_up.L','hl_lo.L','hl_ft.L','hl_up.R','hl_lo.R','hl_ft.R'],
           'claw':['fl_ft.L','fl_ft.R','hl_ft.L','hl_ft.R'],'tail':['tail','root']}
    np.savez_compressed(OUT+'/turtle.npz',v=v,f=f,col=c.astype(np.float32),fmask=fm.astype(np.float32),flow=fl.astype(np.float32),part=parts,sv=sv,sf=sf,suv=suv)
    json.dump(dict(bones=bones,meta=seat_eye(B,dict(partBones=partb,eye=dict(c=[0.0245,0.093,0.312],r=0.0078,iris=[0.62,0.6,0.22],pupil=0.5)),0.15)),open(OUT+'/turtle.json','w'),indent=1)

if __name__=='__main__':
    kinds=sys.argv[1:] or ['turtle','egret','heron','kingfisher','grebe']
    feather_atlas()
    for k in kinds: globals()[k]()
