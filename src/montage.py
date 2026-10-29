# montage.py out.png in1.png in2.png ...  (grid, 3 per row)
import sys
from PIL import Image
out=sys.argv[1]; ims=[Image.open(f).convert('RGB') for f in sys.argv[2:]]
n=int(sys.argv[0] and 3); h=max(i.height for i in ims); w=max(i.width for i in ims)
cols=min(n,len(ims)); rows=(len(ims)+cols-1)//cols
M=Image.new('RGB',(w*cols,h*rows),(255,255,255))
for k,i in enumerate(ims): M.paste(i,((k%cols)*w,(k//cols)*h))
M.save(out)
