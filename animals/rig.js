// v11 精细动物 · runtime rig for animals/*.glb (built by src/animals_gen.py + src/animals_blender.py).
// Model space of every glb: Y up, +Z = forward (head), +X = the animal's left ('.L' bones). Origin = between the feet (birds) / under the plastron (turtle).
// Bones are driven procedurally: every frame the rig is reset to the rest pose, then rotations are applied about MODEL-space axes
// (converted through each bone's rest frame), so the pose code never depends on Blender's bone rolls.
// Shared by qingyue-pond.html and src/animals_view.html (pose tuning).
import * as THREE from 'three';

export const KINDS=['turtle','egret','heron','kingfisher','grebe'];
const AX={x:new THREE.Vector3(1,0,0),y:new THREE.Vector3(0,1,0),z:new THREE.Vector3(0,0,1)};
const _q=new THREE.Quaternion(),_q2=new THREE.Quaternion(),_v=new THREE.Vector3();
const NECK={egret:['neck1','neck2','neck3','neck4','neck5','neck6','head'],heron:['neck1','neck2','neck3','neck4','head'],kingfisher:['neck1','head'],grebe:['neck1','head'],turtle:['neck1','neck2','head']};
// how a neck pose spreads over the chain (pitch / yaw weights) and the S-fold used to pull the head in (retract) or stretch it out (extend)
const NW={egret:[0.3,0.2,0.15,0.12,0.1,0.08,0.05],heron:[0.35,0.25,0.2,0.12,0.08],kingfisher:[0.6,0.4],grebe:[0.6,0.4],turtle:[0.4,0.35,0.25]};
const NRET={egret:[0.75,-1.25,-0.55,0.35,0.7,0.45,-0.1],heron:[0.45,-0.95,-0.35,0.55,0.3],kingfisher:[0.25,-0.25],grebe:[0.35,-0.3],turtle:[0,0,0]};
const NEXT={egret:[0.15,0.5,0.35,-0.05,-0.35,-0.45,-0.1],heron:[0.35,0.75,0.25,-0.5,-0.55],kingfisher:[0.1,0.1],grebe:[0.25,0.1],turtle:[0,0,0]};

// ---------------------------------------------------------------- loading + materials
export async function loadAnimals(loader,base,opt={}){
  const out={};
  await Promise.all(KINDS.map(k=>loader.loadAsync(base+k+'.glb').then(g=>{out[k]=prep(k,g,opt)}).catch(e=>{out[k]={error:String(e)}})));
  return out}
function prep(k,g,opt){
  const root=g.scene,info={tris:0,lod0:0,lod1:0,meshes:[],textures:{}},wet=[];
  root.traverse(o=>{if(!o.isMesh)return;const m=o.material,n=o.name,t=o.geometry.index.count/3;info.tris+=t;info.meshes.push({name:n,tris:t,skinned:!!o.isSkinnedMesh,morphs:Object.keys(o.morphTargetDictionary||{})});
    if(/_LOD1$/.test(n))info.lod1+=t;else info.lod0+=t;
    for(const s of ['map','normalMap','roughnessMap'])if(m[s]&&m[s].image)info.textures[m[s].image.width+'x'+m[s].image.height+' '+s+' '+m.name]=1;
    o.castShadow=!opt.mobile;o.receiveShadow=true;
    if(/_feather/.test(m.name)){m.alphaTest=0.45;m.transparent=false;m.depthWrite=true;m.side=THREE.DoubleSide;m.envMapIntensity=0.45;m.roughness=1;
      o.customDepthMaterial=new THREE.MeshDepthMaterial({depthPacking:THREE.RGBADepthPacking,map:m.map,alphaTest:0.45});wet.push({m,r:1,c:m.color.clone(),feather:1})}
    else if(/_eye$/.test(m.name)){const e=new THREE.MeshPhysicalMaterial({name:m.name,vertexColors:true,roughness:0.06,clearcoat:1,clearcoatRoughness:0.02,envMapIntensity:1.6});o.material=e}
    else if(m.name==='turtle_shell'){const s=new THREE.MeshPhysicalMaterial({name:m.name,map:m.map,normalMap:m.normalMap,normalScale:m.normalScale.clone(),roughnessMap:m.roughnessMap,roughness:1,metalness:0,
        clearcoat:0.3,clearcoatRoughness:0.38,envMapIntensity:0.9});if(opt.rim)opt.rim(s,0.12);o.material=s;wet.push({m:s,r:1,cc:0.3,shell:1})}
    else{m.envMapIntensity=k==='turtle'?0.8:0.55;m.roughness=1;if(opt.rim)opt.rim(m,k==='turtle'?0.1:0.14);wet.push({m,r:1})}});
  root.updateMatrixWorld(true);
  return{kind:k,root,info,wet}}

// one independent, posable instance (shared geometry / materials; own skeleton + morph weights)
export function instance(src){
  const c=src.root.clone(true),bones={};c.traverse(o=>{if(o.isBone)bones[o.name]=o});
  const I={kind:src.kind,root:c,bones,rest:new Map(),lod0:[],lod1:[],feathers:[],eyes:[],shell:[],lod:0};
  c.traverse(o=>{if(o.isSkinnedMesh){const sk=o.skeleton;o.bind(new THREE.Skeleton(sk.bones.map(b=>bones[b.name]),sk.boneInverses.map(m=>m.clone())),o.bindMatrix.clone())}
    if(!o.isMesh)return;const n=o.name;
    if(/_LOD1$/.test(n))I.lod1.push(o);else if(/_body$|_shell$/.test(n))I.lod0.push(o);
    if(/_feathers$/.test(n))I.feathers.push(o);if(/_eyes$/.test(n))I.eyes.push(o)});
  c.updateMatrixWorld(true);
  for(const b of Object.values(bones)){const wq=b.getWorldQuaternion(new THREE.Quaternion()),pq=b.parent.getWorldQuaternion(new THREE.Quaternion());
    I.rest.set(b,{q0:b.quaternion.clone(),p0:b.position.clone(),s0:b.scale.clone(),wq,wqi:wq.clone().invert(),pqi:pq.invert(),wp:b.getWorldPosition(new THREE.Vector3())})}
  setLod(I,0);return I}
export function setLod(I,l){if(I.lod===l&&I._lodSet)return;I.lod=l;I._lodSet=true;for(const o of I.lod0)o.visible=l===0;for(const o of I.lod1)o.visible=l===1}
export const bone=(I,n)=>I.bones[n]||I.bones[n.replace('.','')];
export function reset(I){for(const [b,r] of I.rest){b.quaternion.copy(r.q0);b.position.copy(r.p0);b.scale.copy(r.s0)}}
export function rot(I,n,ax,a){if(!a)return;const b=bone(I,n);if(!b)return;const r=I.rest.get(b);_q.setFromAxisAngle(AX[ax]||ax,a);_q2.copy(r.wqi).multiply(_q).multiply(r.wq);b.quaternion.multiply(_q2)}
export function move(I,n,dx,dy,dz){const b=bone(I,n);if(!b)return;_v.set(dx,dy,dz).applyQuaternion(I.rest.get(b).pqi);b.position.add(_v)}
// attach an object to a bone at a MODEL-space point / orientation (rest pose)
export function attach(I,n,obj,p,q){const b=bone(I,n),r=I.rest.get(b);obj.position.copy(p).sub(r.wp).applyQuaternion(r.wqi);obj.quaternion.copy(r.wqi).multiply(q||new THREE.Quaternion());b.add(obj);return obj}
// wet look (rain / storm / just surfaced): darker, glossier
export function wetness(src,w){for(const e of src.wet){if(e.shell){e.m.clearcoat=0.3+0.6*w;e.m.clearcoatRoughness=0.38-0.3*w}else if(e.feather){e.m.color.copy(e.c).multiplyScalar(1-0.12*w)}else{e.m.roughness=1-0.35*w}}}

// ---------------------------------------------------------------- birds
// P: {fold 0..1, wing:{a,f,h,sweep} (flap angles), neck:{pitch,yaw,ext,ret,roll}, crouch 0..1, legs:[{swing,bend},{...}] (L,R), trail 0..1 (legs back in flight),
//     reach 0..1 (legs forward to land), tail, bob}
export function poseBird(I,P){
  reset(I);const k=I.kind,N=NECK[k],w=NW[k],re=NRET[k],ex=NEXT[k],nk=P.neck||{};
  for(const m of I.feathers)m.morphTargetInfluences[0]=P.fold??1;
  // neck chain
  for(let i=0;i<N.length;i++){rot(I,N[i],'x',(nk.pitch||0)*w[i]+(nk.ret||0)*re[i]+(nk.ext||0)*ex[i]);rot(I,N[i],'y',(nk.yaw||0)*w[i])}
  if(nk.roll)rot(I,'head','z',nk.roll);if(nk.tilt)rot(I,'head','x',nk.tilt);
  // wings (both mirrored): a = up/down about the body axis, f/h = lagging forearm / hand, sweep = hand pulled back on the upstroke
  const W=P.wing;if(W){for(const s of [1,-1]){const n=s>0?'.L':'.R';rot(I,'humerus'+n,'z',s*W.a);rot(I,'forearm'+n,'z',s*(W.f||0));rot(I,'hand'+n,'z',s*(W.h||0));
    if(W.sweep)rot(I,'hand'+n,'y',-s*W.sweep);if(W.fwd)rot(I,'humerus'+n,'y',s*W.fwd)}}
  // legs: crouch bends the intertarsal joint forward, trail swings them back in flight, reach forward before touch-down, swing / bend = stepping
  const c=P.crouch||0,tr=P.trail||0,rc=P.reach||0;
  for(let i=0;i<2;i++){const n=i?'.R':'.L',L=(P.legs&&P.legs[i])||{};
    rot(I,'tibia'+n,'x',0.55*c+1.25*tr-0.55*rc+(L.swing||0));rot(I,'tarsus'+n,'x',-1.1*c+0.25*tr+0.35*rc-(L.bend||0));rot(I,'foot'+n,'x',0.55*c+0.6*tr+(L.bend||0)*0.6)}
  if(P.tail)rot(I,'tail','x',P.tail);
  if(P.bodyPitch)rot(I,'root','x',P.bodyPitch)}

// ---------------------------------------------------------------- turtle
// P: {ret 0..1 (head + limbs in), neck:{pitch,yaw}, legs:[{swing,lift,bend}] x4 (fl.L, fl.R, hl.L, hl.R), tail, splay 0..1 (basking: hind legs stretched back)}
export function poseTurtle(I,P){
  reset(I);const r=P.ret||0,nk=P.neck||{};
  move(I,'neck1',0,-0.012*r,-0.085*r);rot(I,'neck1','x',0.35*r);rot(I,'head','x',-0.3*r);
  for(let i=0;i<3;i++){rot(I,NECK.turtle[i],'x',(nk.pitch||0)*NW.turtle[i]);rot(I,NECK.turtle[i],'y',(nk.yaw||0)*NW.turtle[i])}
  const names=[['fl','.L',1],['fl','.R',-1],['hl','.L',1],['hl','.R',-1]];
  names.forEach(([p,n,s],i)=>{const L=(P.legs&&P.legs[i])||{},front=p==='fl',sp=P.splay||0;
    rot(I,p+'_up'+n,'y',L.swing||0);rot(I,p+'_up'+n,'z',(L.lift||0)+s*0.12*sp);rot(I,p+'_lo'+n,'y',L.bend||0);
    if(!front&&sp)rot(I,p+'_up'+n,'y',-s*0.65*sp);if(!front&&sp)rot(I,p+'_ft'+n,'x',0.5*sp);
    if(r){const b=bone(I,p+'_up'+n);b.scale.setScalar(1-0.4*r);move(I,p+'_up'+n,-s*0.035*r,0.004*r,(front?-0.03:0.03)*r)}});
  if(P.tail)rot(I,'tail','y',P.tail)}
