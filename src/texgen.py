import numpy as np
from scipy.spatial import cKDTree
from scipy import ndimage
from PIL import Image
B='/Users/administrator/Tilo工作台/20261028-青跃三维/project/build/'; T='/Users/administrator/Tilo工作台/20261028-青跃三维/project/textures/'
pos=np.load(B+'bake_pos.npy'); nrm=np.load(B+'bake_nrm.npy'); msk=np.load(B+'bake_mask.npy'); ao=np.load(B+'bake_ao.npy')[...,0]
cov=(pos[...,3]>0.5)&(np.linalg.norm(pos[...,:3],axis=-1)>1e-4)   # v8: edge texels flagged covered but never filled (pos=0) are NOT valid -> refilled from the island interior
H,W=cov.shape
P=pos[...,:3][cov]; Nn=nrm[...,:3][cov]; M=msk[...,:4][cov]; AO=ao[cov]
P0=np.load(B+'bake_pos0.npy')[...,:3][cov]          # pre-lip-close position of every texel
belly,mouth,tymp,tips=M.T
import sys; sys.path.insert(0,'/Users/administrator/Tilo工作台/20261028-青跃三维/project/src'); import sdf as _sd
sdf_zm=lambda Q:_sd.zm(Q[:,0],Q[:,1])
VD=np.load(B+'verts.npz'); V=VD['V'];VN=VD['N']
rng=np.random.default_rng(7)
_vt=cKDTree(VD['V']); _dd,_ni=_vt.query(P,k=4); _ww=1/(_dd+1e-5); _ww/=_ww.sum(1,keepdims=True)
vint=lambda a:(a[_ni]*_ww).sum(1)
MT=vint(VD['tongue']); RAWT=vint(VD['raw']); FACET=vint(VD['face'])
tips=vint(VD['tips'])   # (bake alpha channel is coverage, not the tips mask)
S=lambda t:np.clip(t,0,1)**2*(3-2*np.clip(t,0,1))
def srgb(c): return (np.array(c)/255.)**2.2
# smooth noise via sum of random waves
def wnoise(p,freq,n=12,seed=1):
    r=np.random.default_rng(seed); out=np.zeros(len(p))
    for i in range(n):
        d=r.normal(size=3); d/=np.linalg.norm(d); f=freq*r.uniform(0.7,1.3)
        out+=np.sin(p@d*f*2*np.pi+r.uniform(0,6.28))
    return out/np.sqrt(n/2)
# --- spots: fewer, larger, soft-edged olive blotches
vb=VD['vb']; face=VD['face']; raw=VD['raw']
# exact per-texel mouth classification from the SDF (no vertex interpolation -> no zig-zag lip edges)
near_m=(_sd.mouth_vol(P0)<0.06)&(np.abs(P0[:,2]-_sd.zm(P0[:,0],P0[:,1]))<0.09)&(mouth>0.001)|((_sd.mouth_vol(P0)<0.0)&(np.abs(P0[:,2]-_sd.zm(P0[:,0],P0[:,1]))<0.06))
RAW0=np.zeros(len(P)); RAW0[near_m]=_sd.body_raw(P0[near_m])
inside=S((-RAW0-0.0010)/0.0035)*near_m          # mouth cavity walls (smooth 3.5 mm rim blend)
_miss=(mouth>0.9)&(inside<0.5); print('interior texels missed by the SDF test:',int(_miss.sum()),'of',int((mouth>0.9).sum()))
inside=np.maximum(inside,S((mouth-0.85)/0.1))      # v5: deep interior per baked mask too (no stray skin-coloured lines inside the mouth)
qt=np.linalg.norm((P0-np.array(_sd.TONGUE[0]))/np.array(_sd.TONGUE[1]),axis=-1)
MT=S((1.12-qt)/0.25)*inside
hd=vb=='head'
vbs=vb.astype(str)
limb_small=np.char.startswith(vbs,'finger')|np.char.startswith(vbs,'toe')|np.char.startswith(vbs,'hand')
w=(1-VD['belly'])*np.where(hd,0.0,1.0)*(1-VD['tymp'])*(1-VD['tips'])*(1-VD['mouth'])*np.where(limb_small,0.15,1)
w*=(VD['V'][:,2]>0.02)
cand=rng.permutation(len(V)); centers=[];radii=[]
for i in cand:
    if rng.random()>w[i]**2: continue
    v=V[i]
    r=rng.uniform(0.032,0.05)
    if vb[i].startswith(('upper_arm','forearm')): r=rng.uniform(0.024,0.034)
    if limb_small[i]: r=rng.uniform(0.012,0.016)
    if any(np.linalg.norm(v-c)<(r+rr)*1.1+0.03 for c,rr in zip(centers,radii)): continue
    centers.append(v);radii.append(r)
    if len(centers)>=62: break
print('spots',len(centers))
sub=[];subr=[]
for c,r in zip(centers,radii):
    k=rng.integers(1,3)
    for j in range(k):
        o=rng.normal(size=3)*r*0.3; sub.append(c+o*(j>0)); subr.append(r*(rng.uniform(0.6,0.85) if j else 1.0))
sub=np.array(sub);subr=np.array(subr)
tr=cKDTree(sub); d,idx=tr.query(P,k=4)
wob=wnoise(P,30,seed=3)*0.12
spot=np.max(S((subr[idx]*(1+wob[:,None])-d)/0.018+0.25),axis=1)
spot*=(1-belly)**2*(1-tymp)*(1-mouth)
import sys; sys.path.insert(0,'/Users/administrator/Tilo工作台/20261028-青跃三维/project/src'); import sdf as _s
# head-top spots (between / behind the eyes) like the artwork
hs=[]
for sx in (1,-1):
    hs+= [[0.09*sx,0.00,1.0],[0.19*sx,0.07,0.93],[0.05*sx,0.12,0.96],[0.27*sx,0.14,0.80],[0.13*sx,0.20,0.88],[0.22*sx,0.24,0.70],[0.30*sx,-0.02,0.70]]
hs+= [[0,0.05,1.02],[0.0,-0.08,0.99],[0.0,0.20,0.93]]
hs=[[x,y-0.10,z+_s.HZ] for x,y,z in hs]
hc=_s.project(np.array(hs,float)+np.array([0,0,0.1]),_s.body_raw)
hr=np.array([0.026,0.024,0.022,0.026,0.024,0.026,0.020]*2+[0.024,0.02,0.024])
dh=np.linalg.norm(P[:,None,:]-hc[None],axis=-1)
wb=wnoise(P,35,seed=21)*0.15
hsp=np.max(S((hr[None]*(1+wb[:,None])-dh)/0.014+0.2),axis=1)
# tympanum: big round dark-olive patch behind each eye
tc=_s.project(np.array([_s.TYMP(1),_s.TYMP(-1)])+np.array([[0.1,0,0],[-0.1,0,0]]),_s.body_raw)
dt=np.min(np.linalg.norm(P[:,None,:]-tc[None],axis=-1),axis=1)
tymp=S((0.054-dt)/0.016)*(1-inside)
spot=np.maximum(spot,hsp*(1-tymp)*(1-belly))
fc=[];fr=[]
for i in rng.permutation(len(V)):
    if rng.random()>w[i]**1.5*0.9: continue
    v=V[i]; r=rng.uniform(0.010,0.019)*(0.6 if limb_small[i] else 1)
    if any(np.linalg.norm(v-c)<(r+rr)+0.02 for c,rr in zip(centers,radii)): continue
    if any(np.linalg.norm(v-c)<(r+rr)*1.3+0.018 for c,rr in zip(fc,fr)): continue
    fc.append(v); fr.append(r)
    if len(fc)>=140: break
print('fine spots',len(fc))
fc=np.array(fc); fr=np.array(fr); d2,i2=cKDTree(fc).query(P,k=2)
fsp=np.max(S((fr[i2]*(1+0.15*wnoise(P,45,seed=8))[:,None]-d2)/0.009+0.2),axis=1)*(1-belly)**2*(1-tymp)*(1-mouth)
spot=np.maximum(spot,fsp*0.85)
# --- base color (fresh yellow-green, warm cream belly/jaw)
g_base=srgb([150,182,62]); g_top=srgb([166,194,72]); g_side=srgb([126,156,52]); cream=srgb([242,230,164]); snout=srgb([186,204,100])   # v4: warmer, fresher yellow-green (artwork)
spotc=srgb([100,118,50]); tympc=srgb([84,100,46]); tipc=srgb([222,220,160])
up=np.clip(Nn[:,2],-1,1); nv=wnoise(P,9,seed=5)
col=g_base[None]*(1+0.05*nv[:,None])
col=col+(g_top-g_base)[None]*np.clip(up,0,1)[:,None]*0.8
col=col+(g_side-g_base)[None]*np.clip(-up*0.8+0.3,0,1)[:,None]*0.6
fz=FACET*S((P[:,2]-sdf_zm(P)-0.004)/0.02)
col=col*(1-fz[:,None]*0.7)+snout[None]*fz[:,None]*0.7
col=col*(1-belly[:,None])+cream[None]*(1+0.03*nv[:,None])*belly[:,None]
col=col*(1-tips[:,None]*0.6)+tipc[None]*tips[:,None]*0.6
sc=spotc[None]*(1+0.10*wnoise(P,14,seed=9)[:,None])
col=col*(1-spot[:,None]*0.78)+sc*spot[:,None]*0.78
tc_=tympc[None]*(1+0.08*wnoise(P,25,seed=4)[:,None])
col=col*(1-tymp[:,None]*0.9)+tc_*tymp[:,None]*0.9
# lip line: soft darker green just at the opening (geometry provides the dark gap)
upper=S((P0[:,2]-_sd.zm(P0[:,0],P0[:,1]))/0.003)            # v5: green lip line only on the (green) upper lip
ml=S(1-np.abs(P0[:,2]-_sd.zm(P0[:,0],P0[:,1]))/0.012)*near_m*(1-inside)*S((0.01-_sd.mouth_vol(P0))/0.03)*upper
col=col*(1-ml[:,None]*0.35)+srgb([92,112,46])[None]*ml[:,None]*0.35
# v5: soft pink-cream lip rim band (both lips) -> no seam line when the mouth opens wide
rb=S(1-np.abs(RAW0+0.0012)/0.0045)*near_m*S((0.02-_sd.mouth_vol(P0))/0.04)*S(1-np.abs(P0[:,2]-_sd.zm(P0[:,0],P0[:,1]))/0.012)   # only at the slit
col=col*(1-0.6*rb[:,None])+srgb([214,150,128])[None]*0.6*rb[:,None]
# mouth interior: pink lips -> deep red-brown throat, pink tongue
dep=np.clip((-RAW0-0.004)/0.07,0,1)
rimc=srgb([196,104,98]); midc=srgb([120,42,44]); deepc=srgb([40,12,16])   # v8: dark inner cavity
mo=rimc[None]*(1-S(dep/0.25)[:,None])+midc[None]*S(dep/0.25)[:,None]
mo=mo*(1-S((dep-0.4)/0.6)[:,None])+deepc[None]*S((dep-0.4)/0.6)[:,None]
roof=(P0[:,2]>_sd.zm(P0[:,0],P0[:,1]))*S((dep-0.15)/0.2)
mo=mo*(1-0.08*roof[:,None]*(0.5+0.5*np.sin(P0[:,1]*260))[:,None])   # soft palate ridges
tg=MT[:,None]
groove=S(1-np.abs(P0[:,0])/0.012)*tg[:,0]
tcol=srgb([196,96,96])[None]*(1+0.04*wnoise(P0,30,seed=17)[:,None])
mo=mo*(1-tg)+tcol*tg; mo=mo*(1-0.18*groove[:,None])
col=col*(1-inside[:,None])+mo*inside[:,None]
# soft dark socket line where the eyeball meets the skin dome
for sx in (1,-1):
    de=np.linalg.norm(P-_s.eye_c(sx),axis=-1)-_s.EYE_R
    sock=S(1-np.abs(de-0.004)/0.012)*(1-inside)
    col=col*(1-0.35*sock[:,None])+srgb([70,92,40])[None]*0.35*sock[:,None]
col*= (0.80+0.20*np.clip(AO,0,1))[:,None]
# --- height for very soft bumps (smooth cartoon skin, slight pebbling on the back)
tb=cKDTree(V[rng.choice(len(V),4000,replace=False)])
dd,_=tb.query(P)
h=S((0.012-dd)/0.012)*0.06*(1-belly)*(1-inside)+spot*0.02+0.02*wnoise(P,40,seed=11)
rough=0.40+0.05*wnoise(P,15,seed=13)+spot*0.05+belly*0.06+inside*0.18   # matte inner mouth (no streaky wet highlights)
def img(vals,ch):
    a=np.zeros((H,W,ch),np.float32); a[cov]=vals.reshape(len(P),ch); return a
# v8: texels within 2 px of a UV-island border are only partially covered by their triangles (bad AO / mixed masks)
#     -> they showed as thin jagged 'cracks' on the cream jaw. Refill them (and the gutter) from the island interior.
_core=ndimage.binary_erosion(cov,iterations=2)
_core=np.where(ndimage.binary_dilation(_core,iterations=2)&cov|~cov,_core,cov)   # keep tiny islands that erosion would delete
def dilate(a):
    _,ind=ndimage.distance_transform_edt(~_core,return_indices=True)
    return a[ind[0],ind[1]]
C=dilate(img(np.clip(col,0,1),3)); R=dilate(img(np.clip(rough,0.05,1),1))[...,0]; Hh=dilate(img(h,1))[...,0]
Hh=ndimage.gaussian_filter(Hh,1.6)
gy,gx=np.gradient(Hh); s=2.0
# v5: no false creases - flat normals inside the mouth and along UV-island borders (gradients across islands are meaningless)
_inside_img=dilate(img(inside,1))[...,0]
_core=ndimage.binary_erosion(cov,iterations=3)
_flat=np.clip(1-_inside_img*1.5,0,1)*_core
gx=gx*_flat; gy=gy*_flat
nm=np.stack([-gx*s,-gy*s,np.ones_like(Hh)],-1); nm/=np.linalg.norm(nm,axis=-1,keepdims=True)
# blender image pixels are bottom-up; flip for PNG
fl=lambda a:a[::-1]
Image.fromarray((fl(C)**(1/2.2)*255+0.5).clip(0,255).astype(np.uint8)).save(T+'qingyue_basecolor.png')
Image.fromarray((fl(R)*255).astype(np.uint8)).save(T+'qingyue_roughness.png')
nmn=fl(nm); nmn[...,1]*=1  # gx along u, gy along v (v up in blender -> after flip consistent)
Image.fromarray(((nmn*0.5+0.5)*255).astype(np.uint8)).save(T+'qingyue_normal.png')
print('tex ok')
