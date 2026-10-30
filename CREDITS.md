# 素材来源与授权（CREDITS）

## 音频
- **背景音乐与全部音效均由浏览器 Web Audio 在运行时程序合成**（振荡器、噪声、滤波器、包络），仓库中没有任何外部音乐或音效文件，也没有使用第三方素材。
  包括：跳跃 / 落地 / 溅水 / 划水、雨 / 风 / 雷、虫鸣、蛙鸣合唱、鸟鸣、蝉鸣、鱼吐泡、乌龟入水、白鹭 / 夜鹭 / 翠鸟 / 小䴙䴘叫声、翅膀拍打，以及白天 / 夜晚 / 雷雨三种情绪的背景音乐。
- 说话语音（`tts/*.mp3`）由 `src/gen_tts.py` 调用 Microsoft Edge TTS（音色 zh-CN-XiaoyiNeural）生成，仅用于本项目的语音朗读。

## 代码库
- three.js r170（`vendor/three/`），MIT License，https://github.com/mrdoob/three.js — 许可证见 `vendor/three/LICENSE`。

## 模型、贴图、场景
- 青跃角色、贴图、背心、藤冠由 `src/` 中的 Blender / Python 脚本程序生成。
- 池塘场景、植物、鱼、天空、天气效果均在 `qingyue-pond.html` 中程序生成，无外部模型或贴图素材。
- v11 精细动物（`animals/turtle.glb`、`egret.glb`、`heron.glb`、`kingfisher.glb`、`grebe.glb`）：乌龟、白鹭、夜鹭、翠鸟、小䴙䴘的网格、骨骼、羽毛卡片、龟甲盾片贴图、羽毛贴图图集，以及烘焙出的颜色 / 法线 / 粗糙度贴图，全部由本仓库脚本生成：
  - `src/animals_gen.py`（Python：numpy、scipy、scikit-image、Pillow，按 SDF 建模并用 marching cubes 生成网格，程序绘制龟甲与羽毛贴图）；
  - `src/animals_blender.py`（Blender 5.2：减面、UV、Cycles 烘焙、绑定骨骼、导出 glb，贴图为 WebP）。
  - 没有使用任何第三方模型、扫描数据或照片贴图。动物的动作由 `animals/rig.js` 在运行时按程序驱动骨骼，没有外部动画数据。
  - `?animals=v10` 仍可切回 v10 的程序几何体动物。
