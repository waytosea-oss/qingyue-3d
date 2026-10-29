import numpy as np,sys,time
from skimage import measure
sys.path.insert(0,'.'); import sdf
VOX=0.0038
def mc(group,lo,hi):
    lo=np.array(lo);hi=np.array(hi);n=np.ceil((hi-lo)/VOX).astype(int)+1
    xs=[lo[i]+np.arange(n[i])*VOX for i in range(3)]
    vol=np.zeros(n,np.float32)
    X,Y=np.meshgrid(xs[0],xs[1],indexing='ij')
    for k,z in enumerate(xs[2]):
        p=np.stack([X,Y,np.full_like(X,z)],-1); vol[:,:,k]=sdf.sdf(p,group)
    edge=max(vol[0].min(),vol[-1].min(),vol[:,0].min(),vol[:,-1].min(),vol[:,:,0].min(),vol[:,:,-1].min())
    assert min(vol[0].min(),vol[-1].min(),vol[:,0].min(),vol[:,-1].min(),vol[:,:,0].min(),vol[:,:,-1].min())>0, group+': surface touches the bounding box -> open mesh'
    v,f,_,_=measure.marching_cubes(vol,0.0,spacing=(VOX,)*3)
    return v+lo,f[:,::-1]
t=time.time();out={}
for g,lo,hi in [('body',[-0.44,-0.52,-0.07],[0.44,0.44,1.0]),('armL',[-0.22,-0.62,0.16],[0.40,0.05,0.62]),('armR',[-0.40,-0.62,0.16],[0.22,0.05,0.62])]:
    v,f=mc(g,lo,hi); out[g+'_v']=v;out[g+'_f']=f;print(g,len(v),len(f),time.time()-t,flush=True)
np.savez('../build/mesh.npz',**out)
