#!/bin/zsh
# 全流程重建：SDF 网格 → 组装/烘焙 → 贴图 → 材质/骨骼/形变 → 动作 → 导出
# 依赖：Blender 5.2（/opt/homebrew/bin/blender），Python venv（numpy scipy scikit-image pillow）
set -e
cd "$(dirname "$0")"
PY=${PY:-../../.venv/bin/python}
B=${B:-/opt/homebrew/bin/blender}
mkdir -p ../build
$PY build_mesh.py
$B -b --python stage2.py 2>&1 | grep -E "Traceback|Error|OK|tris"
$PY texgen.py
$B -b --python stage3.py 2>&1 | grep -E "Traceback|Error:|OK|tris|CROWN" | cut -c1-120
$PY vest_badge.py
cp -n vest_data/*.npy ../build/ 2>/dev/null || true   # v6 vest sweep mask + searched pocket layout (reproducible build)
$B -b --python stage3v.py 2>&1 | grep -E "Traceback|Error|VEST|OK"          # v6 vest (uses build/armsweep.npy + vest_layout.npy when present)
$B -b --python stage4.py 2>&1 | grep -E "Traceback|Error:|OK|action"
$B -b --python armsweep.py 2>&1 | grep -E "Traceback|SWEEP OK"   # optional refresh of the body-part sweep for the vest
$B -b --python check_v6.py -- ../build/stage4.blend ../build/check_v6_report.txt 2>&1 | grep -E "WORST"
$B -b --python export.py 2>&1 | grep -E "Traceback|Error:|OK"
$B -b --python check_v7_mouth.py -- ../qingyue.blend v7 ../check_v7_mouth_report.txt 2>&1 | grep -E "RESULT"   # v7 talk mouth: corners must not move sideways
$PY gen_tts.py   # v7 Edge TTS (pip install edge-tts); regenerates only lines whose text/voice changed
