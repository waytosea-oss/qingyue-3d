# 素材来源与授权（CREDITS）

## 音频
- **背景音乐与全部音效均由浏览器 Web Audio 在运行时程序合成**（振荡器、噪声、滤波器、包络），仓库中没有任何外部音乐或音效文件，也没有使用第三方素材。
  包括：跳跃 / 落地 / 溅水 / 划水、雨 / 风 / 雷、虫鸣、蛙鸣合唱、鸟鸣、蝉鸣、鱼吐泡、乌龟入水、白鹭 / 夜鹭 / 翠鸟 / 小䴙䴘叫声、翅膀拍打，以及白天 / 夜晚 / 雷雨三种情绪的背景音乐。
- 说话语音（`tts/*.mp3`）由 `src/gen_tts.py` 调用 Microsoft Edge TTS（音色 zh-CN-XiaoyiNeural）生成，仅用于本项目的语音朗读。

## 代码库
- three.js r170（`vendor/three/`），MIT License，https://github.com/mrdoob/three.js — 许可证见 `vendor/three/LICENSE`。

## 模型、贴图、场景
- 青跃角色、贴图、背心、藤冠由 `src/` 中的 Blender / Python 脚本程序生成。
- 池塘场景、植物、鱼、乌龟、鸟、天空、天气效果均在 `qingyue-pond.html` 中程序生成，无外部模型或贴图素材。
