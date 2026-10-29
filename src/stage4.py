exec(open('/Users/administrator/Tilo工作台/20261028-青跃三维/project/src/common.py').read())
import pickle
bpy.ops.wm.open_mainfile(filepath=BUILD+'stage3.blend')
rig=bpy.data.objects['Qingyue_Rig']; activate(rig); bpy.ops.object.mode_set(mode='POSE')
LIDAX={k:Vector(v) for k,v in pickle.load(open(BUILD+'lidax.pkl','rb')).items()}
BLINK=112
pbs=rig.pose.bones; ORDER=[b.name for b in rig.data.bones]
AX={'X':Vector((1,0,0)),'Y':Vector((0,1,0)),'Z':Vector((0,0,1))}
def upd(): bpy.context.view_layer.update()
def reset_pose():
    for pb in pbs:
        pb.rotation_mode='QUATERNION'; pb.rotation_quaternion=(1,0,0,0); pb.location=(0,0,0); pb.scale=(1,1,1)
def carry(pb):
    if not pb.parent: return Matrix.Identity(4)
    return pb.parent.matrix @ pb.parent.bone.matrix_local.inverted()
def apply_pose(P):
    reset_pose(); upd()
    for n in ORDER:
        if n not in P: continue
        spec=P[n]; pb=pbs[n]
        C=carry(pb); C3=C.to_3x3().normalized()
        M=pb.matrix.copy()
        for op in spec.get('r',[]):
            ax,deg=op; ax=AX[ax] if isinstance(ax,str) else Vector(ax)
            ax=(C3@ax).normalized(); h=M.translation.copy()
            R=Matrix.Translation(h)@Matrix.Rotation(math.radians(deg),4,ax)@Matrix.Translation(-h); M=R@M
        if 'waim' in spec: spec=dict(spec,aim=None)
        if 'aim' in spec:
            d=Vector(spec['waim']).normalized() if spec['aim'] is None else (C3@Vector(spec['aim'])).normalized(); cur=(M.to_3x3()@Vector((0,1,0))).normalized()
            q=cur.rotation_difference(d); h=M.translation.copy()
            M=Matrix.Translation(h)@q.to_matrix().to_4x4()@Matrix.Translation(-h)@M
            if 'twist' in spec:
                h=M.translation.copy(); M=Matrix.Translation(h)@Matrix.Rotation(math.radians(spec['twist']),4,d)@Matrix.Translation(-h)@M
        if 'l' in spec: M=Matrix.Translation(C3@Vector(spec['l']))@M
        pb.matrix=M; upd()
        if 's' in spec: pb.scale=spec['s']; upd()
    if '_g' in P: ground(P['_g'],P.get('_gh',0))
    if '_gs' in P:   # airborne: place the body (spine root) at an exact height -> clean parabola
        r=pbs['root']; M=r.matrix.copy(); M.translation.z+=P['_gs']-pbs['spine'].head.z; r.matrix=M; upd()
FOOT=[b for b in ORDER if b.startswith(('toe','foot','shin'))]
HANDS=[b for b in ORDER if b.startswith(('finger','hand'))]
CLEAR={'toe':0.017,'foo':0.032,'shi':0.045,'fin':0.012,'han':0.026}
def ground(h,hands=0):
    """shift the whole rig vertically so the lowest foot/toe (and optionally hand) surface sits at height h (0 = on the pad)"""
    lo=min(min(pbs[b].tail.z,pbs[b].head.z)-CLEAR[b[:3]] for b in FOOT+(HANDS if hands else []))
    r=pbs['root']; M=r.matrix.copy(); M.translation.z+=h-lo; r.matrix=M; upd()
def blink(on=1.0): return {'lid.L':{'r':[(LIDAX['L'],BLINK*on)]},'lid.R':{'r':[(LIDAX['R'],BLINK*on)]}}
def merge(*ds):
    o={}
    for d in ds:
        for k,v in d.items():
            if not isinstance(v,dict): o[k]=v; continue
            o.setdefault(k,{}); 
            for kk,vv in v.items():
                if kk=='r': o[k]['r']=o[k].get('r',[])+vv
                else: o[k][kk]=vv
    return o
def action_fcurves(act):
    if hasattr(act,'fcurves'): return list(act.fcurves)       # Blender < 5
    out=[]
    for ly in act.layers:
        for st in ly.strips:
            for cb in st.channelbags: out+=list(cb.fcurves)
    return out
def make_action(name,keys,cyclic=False):
    act=bpy.data.actions.new(name); act.use_fake_user=True; rig.animation_data_create(); rig.animation_data.action=act
    for f in sorted(keys):
        apply_pose(keys[f])
        for pb in pbs:
            pb.keyframe_insert('rotation_quaternion',frame=f,group=pb.name); pb.keyframe_insert('location',frame=f,group=pb.name); pb.keyframe_insert('scale',frame=f,group=pb.name)
    for fc in action_fcurves(act):
        for kp in fc.keyframe_points: kp.interpolation='BEZIER'; kp.easing='AUTO'
    tr=rig.animation_data.nla_tracks.new(); tr.name=name; st=tr.strips.new(name,int(min(keys)),act); tr.mute=True
    rig.animation_data.action=None
    print('action',name,len(keys))
s=lambda n:1 if n.endswith('L') else -1
def armsup(a=1.0):
    P={}
    for n in 'LR':
        sg=1 if n=='L' else -1
        P['upper_arm.'+n]={'aim':(0.85*sg,-0.25,0.45*a+0.1)}; P['forearm.'+n]={'aim':(0.6*sg,-0.25,0.8)}; P['hand.'+n]={'aim':(0.4*sg,-0.2,0.9)}   # v6: wider, clear of the bigger crown
    return P
def armsfwd():
    P={}
    for n in 'LR':
        sg=1 if n=='L' else -1
        P['upper_arm.'+n]={'aim':(0.3*sg,-0.8,-0.35)}; P['forearm.'+n]={'aim':(0.1*sg,-0.6,-0.9)}; P['hand.'+n]={'aim':(0.0,-1,-0.2)}
    return P
def legs_ext(k=1.0):
    P={}
    for n in 'LR':
        sg=1 if n=='L' else -1
        P['thigh.'+n]={'aim':(0.45*sg,0.65*k-0.2*(1-k),-0.8)}; P['shin.'+n]={'aim':(0.22*sg,1.0*k,-0.75)}; P['foot.'+n]={'aim':(0.08*sg,1,-0.15)}
    return P
def squash(sx,sz,lz=0.0,ly=0.0,extra=None):
    P={'root':{'s':(sx,sx,sz),'l':(0,ly,lz)}}
    return P
# ---------------- actions
F=30
# sit_hug: rest with gentle breathing
TILT={'head':{'r':[('Y',6),('Z',-5)]},'neck':{'r':[('Y',2)]}}     # v5: head rests a little tilted - asymmetric, alive
make_action('sit_hug',{1:TILT,30:merge(squash(1.012,0.99),TILT,{'head':{'r':[('Y',2)]}}),60:TILT})
# idle
idle={1:{},
 20:merge(squash(1.01,0.992),{'head':{'r':[('Z',6),('Y',-3)]},'throat':{'s':(1.12,1.12,1.12)}}),
 34:merge({'head':{'r':[('Z',6),('Y',-3)]}},blink(1)),
 38:{'head':{'r':[('Z',6),('Y',-3)]}},
 60:merge(squash(1.01,0.992),{'head':{'r':[('Z',-5),('Y',3)]},'throat':{'s':(1.1,1.1,1.1)},'eye.L':{'r':[('Z',-8)]},'eye.R':{'r':[('Z',-8)]}}),
 90:merge({'head':{'r':[('Z',-4),('X',-4)]}}),
 96:merge({'head':{'r':[('Z',-2),('X',-2)]}},blink(1)),
 100:{'head':{'r':[('Z',-1)]}},
 120:{}}
idle={f:merge(TILT,v) for f,v in idle.items()}
make_action('idle',idle)
# ================= frog locomotion (real frog leap mechanics, cartoon timing) =================
# real frogs: crouch -> explosive hind-leg extension, body pitched nose-up along the take-off line,
# forelimbs swept back in flight -> legs fold under at the apex -> body pitches nose-down,
# forelimbs reach forward and touch first -> belly/legs absorb (squash) -> rebound -> settle.
def lean(sp=0,hd=0): return {'spine':{'r':[('X',sp)]},'head':{'r':[('X',hd)]}}
def sq(sx,sz): return {'root':{'s':(sx,sx,sz)}}
def pitch(a): return {'root':{'r':[('X',a)]}}           # +a = nose down, -a = nose up
def G(h,hands=0): return {'_g':h,'_gh':hands}
def AIR(h): return {'_gs':h}
def fwd(y): return {'root':{'l':(0,y,0)}}
def per(fn):
    P={}
    for n in 'LR':
        sg=1 if n=='L' else -1
        for k,v in fn(sg).items(): P[k+'.'+n]=v
    return P
# world-space limb targets ('waim'): exact regardless of how far the body is pitched
W=lambda f: per(lambda sg:{k:{'waim':tuple(c*(sg if i==0 else 1) for i,c in enumerate(v))} for k,v in f.items()})
legs_push =W({'thigh':(0.30,0.45,-0.85),'shin':(0.14,0.62,-0.78),'foot':(0.06,0.85,-0.52)})   # toes still on the pad
legs_trail=W({'thigh':(0.36,0.52,-0.78),'shin':(0.16,0.95,-0.30),'foot':(0.06,0.55,-0.83)})   # extended behind, knees softly bent (round, not stretched)
legs_pull =W({'thigh':(0.32,-0.62,-0.62),'shin':(0.16,0.72,-0.6),'foot':(0.06,-0.35,-0.93)})   # knees bent, folding under for landing
arms_plant=W({'upper_arm':(0.35,-0.5,-0.8),'forearm':(0.08,-0.65,-0.75),'hand':(0.05,-1,-0.25)})
arms_swept=W({'upper_arm':(0.45,0.45,-0.75),'forearm':(0.22,0.85,-0.45),'hand':(0.1,1,-0.1)})  # tucked back along the body
arms_reach=W({'upper_arm':(0.32,-0.55,-0.78),'forearm':(0.12,-0.35,-0.93),'hand':(0.04,-0.85,-0.5),
              'finger1':(0.55,-1,-0.35),'finger2':(0.2,-1,-0.35),'finger3':(-0.15,-1,-0.35),'finger4':(-0.45,-1,-0.35)})
arms_absorb=W({'upper_arm':(0.38,-0.25,-0.9),'forearm':(0.1,0.05,-1),'hand':(0.04,-1,-0.1)})
R_lift=lambda: {'upper_arm.R':{'waim':(-0.22,-0.9,-0.38)},'forearm.R':{'waim':(0.62,-0.62,0.30)},'hand.R':{'waim':(0.75,-0.4,0.1)}}   # right forearm lifted clear above the left
look=lambda body_pitch: {'head':{'r':[('X',-body_pitch*0.75)]}}       # keep the eyes on the horizon
# v5 leap: body pitched near-horizontal in the air (15-25 deg from horizontal), hind legs stretched back,
#     forelimbs reaching forward/down; lands hands-first, absorbs, then folds back into the hug
legs_fly=W({'thigh':(0.30,0.88,-0.36),'shin':(0.14,0.98,-0.12),'foot':(0.05,1.0,0.1)})
arms_fly=W({'upper_arm':(0.66,0.70,-0.28),'forearm':(0.40,0.90,-0.16),'hand':(0.22,1.0,-0.05)})   # v6: tucked back but clear of the vest sides          # tucked back along the belly
arms_fly_reach=W({'upper_arm':(0.36,-0.82,-0.44),'forearm':(0.14,-0.88,-0.45),'hand':(0.05,-0.78,-0.62),
                  'finger1':(0.55,-0.8,-0.4),'finger2':(0.2,-0.9,-0.4),'finger3':(-0.15,-0.9,-0.4),'finger4':(-0.45,-0.8,-0.4)})   # reaching forward for the pad
lookf=lambda p:{'head':{'r':[('X',-p*0.5)]},'neck':{'r':[('X',-p*0.1)]}}   # v6: less head tip-back (keeps the back collar free)   # keep the eyes on the flight path
jump={1:G(0),
 3:merge(R_lift(),G(0)),                                                         # right arm (on top) leaves first
 5:merge(sq(1.07,0.88),pitch(10),look(0),arms_plant,G(0)),                       # crouch, hands planted
 8:merge(sq(1.12,0.80),pitch(16),look(4),arms_plant,G(0),blink(0.25)),           # loaded
 11:merge(sq(0.97,1.04),pitch(55),lookf(55),legs_push,arms_fly,G(0)),          # thrust - toes leave last
 15:merge(sq(1.03,0.97),pitch(70),lookf(70),legs_fly,arms_fly,AIR(0.92)),      # flying: near-horizontal, legs stretched back
 20:merge(sq(1.02,0.98),pitch(68),lookf(66),legs_fly,arms_fly_reach,AIR(0.98)),      # apex: forelimbs come forward
 25:merge(pitch(74),lookf(70),legs_pull,arms_fly_reach,AIR(0.74)),                    # nose-down, forelimbs reaching for the pad
 28:merge(pitch(55),lookf(48),legs_pull,arms_absorb,G(0,1)),                      # hands touch first
 31:merge(sq(1.12,0.84),pitch(18),look(8),arms_absorb,G(0),blink(0.4)),          # belly/legs absorb - squash
 36:merge(sq(0.97,1.04),pitch(-3),look(-2),G(0)),                                # rebound
 40:merge(sq(1.01,0.99),R_lift(),G(0)),                                          # left arm settles, right still lifted
 46:merge(TILT,G(0)),
 50:merge(TILT,G(0))}
make_action('jump',jump)
# ---- hop forward: same mechanics, lower/shorter arc, travels 0.35 along -Y (the page re-roots the frog at the end)
hop={1:G(0),
 4:merge(sq(1.05,0.92),pitch(12),look(2),arms_plant,G(0)),
 7:merge(fwd(-0.03),sq(0.97,1.04),pitch(50),lookf(50),legs_push,arms_fly,G(0)),
 11:merge(fwd(-0.13),sq(1.02,0.98),pitch(64),lookf(64),legs_fly,arms_fly,AIR(0.80)),
 15:merge(fwd(-0.23),pitch(64),lookf(62),legs_fly,arms_fly_reach,AIR(0.82)),
 19:merge(fwd(-0.31),pitch(70),lookf(66),legs_pull,arms_fly_reach,AIR(0.64)),
 22:merge(fwd(-0.35),pitch(50),lookf(44),arms_absorb,G(0,1)),
 25:merge(fwd(-0.35),sq(1.1,0.85),pitch(12),look(6),arms_absorb,G(0)),
 30:merge(fwd(-0.35),sq(0.98,1.03),pitch(-2),G(0)),
 34:merge(fwd(-0.35),R_lift(),G(0)),
 39:merge(fwd(-0.35),TILT,G(0))}
make_action('hop_forward',hop)
# ---- wave: right arm out to the side, palm forward, wrist waves, fingers spread with soft curl
def wavearm(a,f=0.0):
    sa=math.sin(math.radians(a))
    P={'upper_arm.R':{'waim':(-0.95,-0.28,0.12)},                 # out to the side, elbow level with the chin
       'forearm.R':{'waim':(-0.18+0.55*sa,-0.22,1.0)},            # forearm up, swinging side to side
       'hand.R':{'waim':(-0.12+0.75*sa,-0.30,1.0)},               # wrist follows a little further (drag)
       'head':{'r':[('Y',6),('Z',-10),('X',-4)]},'chest':{'r':[('Y',5)]},'neck':{'r':[('Z',-4)]}}
    for i,fx in enumerate((-0.42,-0.15,0.12,0.36)):                 # fingers fanned, slight forward curl (palm to viewer)
        P['finger%d.R'%(i+1)]={'waim':(fx+0.8*sa,-0.30-f,1.0)}
    return P
wave={1:{},8:wavearm(-8,0.3),13:wavearm(0),18:wavearm(26),24:wavearm(-22),30:wavearm(26),36:wavearm(-22),42:wavearm(18),48:merge(wavearm(0,0.2),blink(1)),51:wavearm(0,0.2),62:{}}
make_action('wave',wave)
# ---- talk loop: moderate, capped jaw (max 8 deg); the page adds lip-sync visemes on top (also capped)
def tk(j,h=0,t=1.0): return {'jaw':{'r':[('X',min(j,22))]},'head':{'r':[('X',-h)]}}   # v8: talking opens the jaw up to ~22 deg (still jaw-only)   # v7: talk = jaw up/down (<=8 deg) + gentle nod only; no head roll, no throat scaling
talk={1:tk(0),5:tk(18,2),9:tk(5,0),13:tk(14,-1),17:tk(3,1),21:tk(22,3),26:tk(7,0),30:tk(16,-2),35:tk(4,1),40:tk(20,2),44:tk(4,0),48:tk(0)}
make_action('talk',talk)
# ---- croak: the BIG mouth opens by tipping the head UP (cartoon frog) while the jaw drops at most 16 deg
#      relative to the head -> the chin never swings down into the crossed arms
JAW_MAX=26   # v4: arms move out of the way during the croak, so the performance can open wider
arms_knees=W({'upper_arm':(0.9,-0.32,-0.12),'forearm':(0.55,-0.62,0.32),'hand':(0.45,-0.55,0.55),
              'finger1':(0.75,-0.45,0.45),'finger2':(0.5,-0.55,0.62),'finger3':(0.25,-0.6,0.7),'finger4':(0.0,-0.6,0.75)})   # arms flung open to the sides, palms up - chin completely free
L_knee={k:v for k,v in arms_knees.items() if k.endswith('.L')}
SAC_FULL=1/0.06   # vsac bone scale that inflates the (deflated-modelled) sac to full size
def ck(head,jaw,th,ex=None):
    sac=1+(SAC_FULL-1)*max(0.0,(th-1.0)/0.55)          # th 1.0 -> deflated, 1.55 -> full balloon (about head width)
    return merge({'head':{'r':[('X',-head)]},'neck':{'r':[('X',-head*0.3)]},'chest':{'r':[('X',-head*0.2)]},'jaw':{'r':[('X',min(jaw,JAW_MAX))]},
                  'throat':{'s':(1+0.12*(th-1),)*3},'vsac':{'s':(sac,sac,sac)}},ex or {})   # v8: the balloon does the inflating, the throat skin only stretches a little
croak={1:{},
 4:merge(ck(2,0,1.02),R_lift()),                          # right arm (on top) leaves first
 8:merge(ck(9,0,1.2),arms_knees),                          # both arms down on the knees, chest open
 13:merge(ck(18,26,1.5),arms_knees),                       # big call: head up + wide jaw
 17:merge(ck(14,6,1.18),arms_knees),
 21:merge(ck(20,26,1.55),arms_knees),                      # second call
 26:merge(ck(14,4,1.12),arms_knees),
 31:merge(ck(6,0,1.04),arms_knees),
 35:merge(ck(3,0,1.0),L_knee,R_lift(),blink(1)),           # left arm settles first, right arm hovering
 40:merge(ck(1,0,1.0),R_lift()),
 46:{},50:{}}
make_action('croak',croak)
# happy spin
spin={1:G(0)}
for i,f in enumerate([6,12,18,24,30,36]):
    ang=[0,0,120,240,360,360][i]
    h=[0,0.12,0.30,0.30,0.10,0][i]
    sqv=[(1.06,0.9),(0.97,1.05),(1,1.02),(1,1.02),(1,1.0),(1.08,0.88)][i]
    P=merge({'root':{'s':(sqv[0],sqv[0],sqv[1]),'r':[('Z',ang)]}},armsup(1.0) if 0<i<5 else {},legs_ext(0.4) if 1<i<4 else {},{'head':{'r':[('X',-10 if 0<i<5 else 6)]}},G(h))
    spin[f]=P
spin[44]=merge(armsup(0.8),{'head':{'r':[('Y',10)]}},blink(0.85),G(0)); spin[50]=merge(armsup(0.8),{'head':{'r':[('Y',-10)]}},blink(0.85),G(0)); spin[60]=G(0)
make_action('happy_spin',spin)
# look around
def look(yaw,pitch=0,eye=0): return {'neck':{'r':[('Z',yaw*0.3)]},'head':{'r':[('Z',yaw*0.7),('X',-pitch)]},'eye.L':{'r':[('Z',eye)]},'eye.R':{'r':[('Z',eye)]}}
la={1:{},12:look(0,0,18),24:look(38,5,10),44:look(38,5,10),50:merge(look(30,5,0),blink(1)),54:look(25,5,-15),66:look(-38,3,-10),84:look(-38,3,-10),96:look(0,-6,0),110:{}}
make_action('look_around',la)
# sleep
def slp(b): return merge({'head':{'r':[('X',5+b*2),('Y',11),('Z',4)]},'neck':{'r':[('X',2)]},'root':{'s':(1+0.015*b,1+0.015*b,1-0.01*b)},'throat':{'s':(1+0.12*b,)*3}},blink(1))
make_action('sleep',{1:slp(0),40:slp(1),80:slp(0),120:slp(1),160:slp(0)})
# ---- v8 swim: frog breaststroke cycle (body horizontal; both legs kick together, both arms stroke together)
#      glide -> arms pull out & back while knees draw up wide -> arms tuck -> legs kick back (whip) + arms shoot forward -> glide
SWP=76
sw_glide=merge(W({'thigh':(0.16,0.96,-0.22),'shin':(0.08,1.0,-0.08),'foot':(0.04,1.0,0.06),
                  'upper_arm':(0.22,-0.96,-0.16),'forearm':(0.1,-1.0,-0.06),'hand':(0.04,-1.0,0.0)}))
sw_pull =merge(W({'thigh':(0.42,0.66,-0.55),'shin':(0.22,0.92,-0.26),'foot':(0.14,0.95,0.0),
                  'upper_arm':(0.86,-0.32,-0.38),'forearm':(0.62,0.2,-0.62),'hand':(0.42,0.38,-0.72)}))
sw_tuck =merge(W({'thigh':(0.86,-0.08,-0.46),'shin':(0.32,0.9,-0.3),'foot':(0.45,0.8,0.0),
                  'upper_arm':(0.46,-0.24,-0.85),'forearm':(-0.18,-0.72,-0.6),'hand':(-0.08,-0.9,-0.3)}))
sw_kick =merge(W({'thigh':(0.55,0.8,-0.25),'shin':(0.45,0.9,-0.05),'foot':(0.22,1.0,0.1),
                  'upper_arm':(0.3,-0.9,-0.28),'forearm':(0.15,-1.0,-0.12),'hand':(0.06,-1.0,-0.05)}))
def SW(p,ex=None,sqv=(1,1)): return merge(pitch(SWP),lookf(SWP),sq(*sqv),p,AIR(0.30),ex or {})
make_action('swim',{1:SW(sw_glide),9:SW(sw_pull),15:SW(sw_tuck,sqv=(1.02,0.98)),21:SW(sw_kick,sqv=(0.98,1.03)),28:SW(sw_glide),33:SW(sw_glide)})
reset_pose(); bpy.ops.object.mode_set(mode='OBJECT')
rig.animation_data.action=None
bpy.context.scene.render.fps=30
bpy.ops.wm.save_as_mainfile(filepath=BUILD+'stage4.blend')
print('STAGE4 OK')
