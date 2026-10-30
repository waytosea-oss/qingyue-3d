# 青跃三维（凤凰岛 · 黑斑侧褶蛙）

- 在线预览（GitHub Pages）：https://waytosea-oss.github.io/qingyue-3d/
- 主入口：`qingyue-pond.html`（夜晚池塘 + 动作控制）；`qingyue-3d.html` 为角色展示页。
- 起点版本：v8（2026-10-29）；v9 在分支 `v9-features`。改动说明见 `CHANGELOG.md`。

## 协作方式
- 每次改动开一个分支并提 PR，PR 审过再合并到 `main`。
- `main` 合并后 GitHub Pages 自动更新预览。
- 测试：`src/test_pond.py`（v8 动作，29 项）、`src/test_v9.py`（v9 小地图 / 头灯 / 水下生物 / 昼夜天气 / 手机，41 项）、`src/test_v10.py`（v10 音效 / 镜头 / 操控 / 小地图图层 / 鸟 / 树，75 项）、`src/test_v11.py`（v11 精细动物，34 项），均用 Playwright + 本机 Chrome：`python src/test_v11.py http://127.0.0.1:<端口>/qingyue-pond.html`。
- v11 动物模型在 `animals/`（glb + 运行时骨骼驱动 `rig.js`），由 `src/animals_gen.py` 和 `src/animals_blender.py` 重新生成。
- 注意保留 `vendor/three/build/three.module.min.js`。
