# 青跃 procedural SDF model (frog faces -Y, Z up, sitting height ~1.0)
import numpy as np
def smin(a,b,k):
    if k<=0: return np.minimum(a,b)
    h=np.clip(0.5+0.5*(b-a)/k,0,1); return b*(1-h)+a*h-k*h*(1-h)
def ssub(d1,d2,k):
    h=np.clip(0.5-0.5*(d1+d2)/k,0,1); return d1*(1-h)+(-d2)*h+k*h*(1-h)
def ell(p,c,r):
    q=(p-np.asarray(c))/np.asarray(r); k0=np.linalg.norm(q,axis=-1)
    k1=np.linalg.norm(q/np.asarray(r),axis=-1)+1e-9; return k0*(k0-1)/k1
def cone(p,a,b,ra,rb):
    a=np.asarray(a,float);b=np.asarray(b,float);ab=b-a
    t=np.clip(((p-a)@ab)/(ab@ab),0,1)
    return np.linalg.norm(p-(a+t[...,None]*ab),axis=-1)-(ra+(rb-ra)*t)
def sph(p,c,r): return np.linalg.norm(p-np.asarray(c),axis=-1)-r

HZ=-0.07   # v4: whole head lowered (curled-up hug pose, artwork silhouette)
def zm(x,y):  # mouth line height (smile curve)
    return 0.650+HZ+0.50*x*x+0.10*np.clip(y+0.05,0,None)
EYE_R=0.108
def eye_c(s): return np.array([0.226*s,-0.152,0.884+HZ])
DOME=lambda s:[0.200*s,-0.098,0.874+HZ]
TYMP=lambda s:np.array([0.335*s,0.03,0.785+HZ])

P=[]  # (group, bone, kind, args, k)
def add(g,b,kind,args,k): P.append((g,b,kind,args,k))
# torso
add('body','TORSO','ell',([0,0.07,0.265],[0.285,0.245,0.255]),0)      # v4: rounder, wider, lower
add('body','hips','ell',([0,0.08,0.16],[0.30,0.26,0.16]),0.08)
add('body','hips','ell',([0,0.15,0.15],[0.24,0.16,0.15]),0.06)
add('body','chest','ell',([0,-0.02,0.355],[0.21,0.18,0.14]),0.08)  # belly front
# head
add('body','head','ell',([0,-0.03,0.75+HZ],[0.355,0.30,0.225]),0.12)
add('body','head','ell',([0,-0.16,0.735+HZ],[0.29,0.19,0.165]),0.09)   # snout
add('body','head','ell',([0,-0.165,0.632+HZ],[0.30,0.20,0.10]),0.09)  # chin/throat
for s in (1,-1):
    add('body','head','sph',(DOME(s),0.130),0.07)
    add('body','head','sph',(list(TYMP(s)+np.array([-0.012*s,0,0])),0.045),0.05)  # tympanum bump
# legs
for s,n in ((1,'L'),(-1,'R')):
    # v4 hug pose: fat thighs folded forward (nearly level), knees up against the chest, short shins, feet tucked
    hip=[0.175*s,0.05,0.165]; knee=[0.165*s,-0.255,0.305]; ank=[0.155*s,-0.12,0.065]; mt=[0.17*s,-0.245,0.03]
    add('body','thigh.'+n,'cone',(hip,knee,0.155,0.112),0.07)
    add('body','shin.'+n,'cone',(knee,ank,0.088,0.056),0.03)
    add('body','foot.'+n,'cone',(ank,mt,0.04,0.03),0.03)
    angs=[-38,-18,0,16,34]; lens=[0.085,0.11,0.13,0.12,0.09]
    for i,(a,L) in enumerate(zip(angs,lens)):
        a=np.radians(a)*s; d=np.array([np.sin(a)*s*-1*-1, -np.cos(a), 0.0])
        d=np.array([np.sin(a),-np.cos(a),0])
        b0=np.array(mt)+np.array([ (i-2)*0.012*s,0,-0.005]); tip=b0+d*L; tip[2]=0.02
        add('body','toe%d.%s'%(i+1,n),'cone',(list(b0),list(tip),0.015,0.0095),0.012)
        add('body','toe%d.%s'%(i+1,n),'ell',(list(tip),[0.016,0.016,0.012]),0.007)
# arms (separate meshes). right arm (-X) on top
# v4: forearms crossed and resting on the knees, just under the chin
# v5: arms wrap AROUND the front of the knees (elbows outside the knees, forearms crossing in front of the
#     knee-caps, right forearm + hand lying over the left, hands draped on the opposite knee)
ARM={'L':dict(sh=[0.225,-0.06,0.44],el=[0.30,-0.355,0.35],wr=[-0.065,-0.455,0.335],z=0.34),
     'R':dict(sh=[-0.225,-0.06,0.455],el=[-0.30,-0.36,0.40],wr=[0.065,-0.47,0.405],z=0.37)}
for n,A in ARM.items():
    g='arm'+n; s=1 if n=='L' else -1
    add(g,'chest','sph',(list(np.array(A['sh'])+[ -0.04*s,0.03,0]),0.06),0)
    add(g,'upper_arm.'+n,'cone',(A['sh'],A['el'],0.066,0.058),0.04)
    add(g,'forearm.'+n,'cone',(A['el'],A['wr'],0.056,0.044),0.03)
    hand=np.array(A['wr'])+np.array([-0.045*s,-0.005,0.0])
    add(g,'hand.'+n,'ell',(list(hand),[0.045,0.035,0.028]),0.025)
    for i in range(4):
        b0=hand+np.array([-0.02*s,-0.025+0.017*i*-1+0.025,0.0])
        b0=hand+np.array([-0.025*s,-0.03+0.02*i,0.005])
        d=np.array([-0.2*s,-0.2+0.11*i,-1.0]); d/=np.linalg.norm(d)
        L=[0.064,0.075,0.07,0.055][i]; tip=b0+d*L
        add(g,'finger%d.%s'%(i+1,n),'cone',(list(b0),list(tip),0.0125,0.009),0.01)
        add(g,'finger%d.%s'%(i+1,n),'ell',(list(tip),[0.0135,0.0135,0.011]),0.006)

def prim_d(p,pr):
    g,b,kind,args,k=pr
    return {'ell':ell,'sph':sph,'cone':cone}[kind](p,*args)

def body_raw(p,group='body'):
    d=None
    for pr in P:
        if pr[0]!=group: continue
        di=prim_d(p,pr); d=di if d is None else smin(d,di,pr[4])
    return d

def project(pts,f,it=30):
    pts=np.array(pts,float); e=1e-3
    for _ in range(it):
        d=f(pts); g=np.stack([(f(pts+np.eye(3)[i]*e)-d)/e for i in range(3)],-1)
        g/=np.linalg.norm(g,axis=-1,keepdims=True)+1e-9; pts=pts-d[:,None]*g
    return pts

_ridge=None
def ridges():
    global _ridge
    if _ridge is None:
        segs=[]
        for s in (1,-1):
            g=np.array([[0.21*s,0.02,0.88+HZ],[0.24*s,0.12,0.78+HZ],[0.225*s,0.21,0.56],[0.22*s,0.27,0.42],[0.20*s,0.31,0.28],[0.16*s,0.31,0.17]])
            t=np.linspace(0,len(g)-1,36); gi=np.stack([np.interp(t,np.arange(len(g)),g[:,k]) for k in range(3)],-1)
            segs.append(project(project(gi,body_raw)-0.002*0,body_raw))   # dense so the fold hugs the concave neck
        _ridge=segs
    return _ridge
_nos=None
def nostrils():
    global _nos
    if _nos is None: _nos=project(np.array([[0.05,-0.35,0.775+HZ],[-0.05,-0.35,0.775+HZ]]),body_raw)   # cached (was recomputed on every sdf() call)
    return _nos

# ---- real mouth: thin slit along the smile line that opens into a hollow cavity + tongue
MOUTH_C=[0,-0.16,0.655+HZ]; MOUTH_R=[0.325,0.26,0.16]
SLIT_HW=0.0065   # half gap at the lips (closed afterwards by lip_close() on the mesh)
def mouth_vol(p): return ell(p,MOUTH_C,MOUTH_R)
def cavity(p,raw):
    z=p[...,2]; zl=zm(p[...,0],p[...,1])
    depth=np.clip(-raw-0.012,0,0.06)
    hw=SLIT_HW+0.55*depth                      # thin at the lips, roomy inside
    c=np.maximum(np.abs(z-zl)-hw,mouth_vol(p))
    # v5: the cavity may only open to the outside at the lip slit; elsewhere it stays >=12 mm under the skin
    #     (it used to break through the thin throat behind the chin -> red slit / 'inner lip seam')
    return np.maximum(c,np.minimum(raw+0.012,np.abs(z-zl)-SLIT_HW-0.003))
TONGUE=([0,-0.115,0.612+HZ],[0.135,0.165,0.03])
def sdf(p,group='body'):
    d=body_raw(p,group)
    if group!='body': return d
    raw=d
    for seg in ridges():
        for a,b in zip(seg[:-1],seg[1:]): d=smin(d,cone(p,a,b,0.006,0.006),0.02)
    d=ssub(d,cavity(p,raw),0.0075)                         # rounded lip rim
    tg=np.maximum(ell(p,*TONGUE),raw+0.03)                 # tongue stays deep inside
    tg=ssub(tg,ell(p,[0,TONGUE[0][1]-0.02,TONGUE[0][2]+TONGUE[1][2]],[0.008,0.12,0.012]),0.006)  # midline groove
    d=smin(d,tg,0.014)
    for n in nostrils(): d=ssub(d,sph(p,n,0.008),0.005)
    return d
def lip_close(V,raw):
    """squeeze the lip gap (which marching cubes needs to be wide) down to a thin line"""
    z=V[:,2]; zl=zm(V[:,0],V[:,1]); g=np.abs(z-zl)
    S_=lambda t:np.clip(t,0,1)**2*(3-2*np.clip(t,0,1))
    near=S_((0.03-mouth_vol(V))/0.03)
    shrink=(SLIT_HW-0.0012)*S_((0.034-g)/0.026)*near*S_((raw+0.016)/0.010)   # v8: squeeze only the outer lip rim, never the roof/floor inside (that folded the palate)
    return np.stack([V[:,0],V[:,1],z-np.sign(z-zl)*shrink],-1)
