# v11b: embroidered round patch for the vest = 启格科普 seal, option C (Tilo picked 2026-10-30)
#   deep-green disc RGB(52,84,44) + cream RGB(240,232,198) 启格印章标 and 「启格科普」, single-colour embroidery look, no red.
#   The artwork is the finished 512x512 PNG Tilo approved (src/art/qingyue_vest_badge_qige_C.png), so this script just copies it
#   (same size / layout as the old v6 leaf + 凤凰岛科普 patch, so the badge UVs are unchanged).
import os, shutil
HERE=os.path.dirname(os.path.abspath(__file__))
SRC=os.path.join(HERE,'art','qingyue_vest_badge_qige_C.png')
TEX='/Users/administrator/Tilo工作台/20261028-青跃三维/project/textures/'
REPO=os.path.dirname(HERE)
for dst in (TEX, os.path.join(REPO,'textures')+'/', os.path.join(REPO,'fbx','qingyue.fbm')+'/'):
    if os.path.isdir(dst): shutil.copyfile(SRC, dst+'qingyue_vest_badge.png')
print('badge ok (启格科普 seal, option C)')
