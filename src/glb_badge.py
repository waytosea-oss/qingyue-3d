# v11b: swap the embedded vest badge image inside qingyue.glb without re-exporting
# (mesh, UVs, skin, animations, normal/roughness maps and every other texture stay byte-identical).
# usage: python glb_badge.py [../qingyue.glb] [../textures/qingyue_vest_badge.png]
import sys, os, io, json, struct
from PIL import Image
HERE=os.path.dirname(os.path.abspath(__file__))
GLB=sys.argv[1] if len(sys.argv)>1 else os.path.join(HERE,'..','qingyue.glb')
PNG=sys.argv[2] if len(sys.argv)>2 else os.path.join(HERE,'..','textures','qingyue_vest_badge.png')
b=open(GLB,'rb').read()
jl=struct.unpack('<I',b[12:16])[0]; j=json.loads(b[20:20+jl]); p=20+jl
bl,bt=struct.unpack('<II',b[p:p+8]); assert bt==0x004E4942; binb=bytearray(b[p+8:p+8+bl])
ii=[i for i,im in enumerate(j['images']) if im.get('name')=='qingyue_vest_badge']; assert len(ii)==1
im=j['images'][ii[0]]; vi=im['bufferView']; v=j['bufferViews'][vi]
old=Image.open(io.BytesIO(bytes(binb[v['byteOffset']:v['byteOffset']+v['byteLength']])))
new=Image.open(PNG).convert('RGB'); assert new.size==old.size, (new.size, old.size)
buf=io.BytesIO(); new.save(buf,'JPEG',quality=95); data=buf.getvalue(); im['mimeType']='image/jpeg'
pad=(-len(data))%4; oldspan=v['byteLength']+((-v['byteLength'])%4)
o=v['byteOffset']; binb[o:o+oldspan]=data+b'\0'*pad
delta=len(data)+pad-oldspan   # multiple of 4 -> later views keep their alignment
for k,w in enumerate(j['bufferViews']):
    if k!=vi and w.get('buffer',0)==0 and w['byteOffset']>o: w['byteOffset']+=delta
v['byteLength']=len(data); j['buffers'][0]['byteLength']=len(binb)
js=json.dumps(j,separators=(',',':'),ensure_ascii=False).encode(); js+=b' '*((-len(js))%4)
out=struct.pack('<III',0x46546C67,2,12+8+len(js)+8+len(binb))+struct.pack('<II',len(js),0x4E4F534A)+js+struct.pack('<II',len(binb),0x004E4942)+bytes(binb)
open(GLB,'wb').write(out)
print('glb badge replaced: view %d %d -> %d bytes, glb %d bytes'%(vi,oldspan,len(data),len(out)))
