# TASK v11b：马甲徽章改成「启格科普」+ 启格印章新标（2026-10-30，Tilo 已选定方案 C）

## 要做的事（只改这一处，别的都不动）
1. 青蛙背后马甲上的圆形绣章，文字从「凤凰岛科普」改成「启格科普」，图案换成启格印章新标。
2. 成品贴图 Tilo 已经选定（方案 C：深绿底 + 米白印章与文字，单色刺绣感，不用红色，因为红色和青蛙的绿放在一起很难看）：
   /Users/administrator/Tilo工作台/20261028-青跃三维/qingyue_vest_badge_qige_C.png （512×512，和旧 badge 同尺寸同版式）
3. 用这张图替换：
   - textures/qingyue_vest_badge.png
   - fbx/qingyue.fbm/qingyue_vest_badge.png
   - qingyue.glb 里嵌入的 badge 贴图（重新导出或直接替换 glb 内的图像，保证页面上马甲显示新章；保持原有 UV、法线/粗糙度、刺绣质感、尺寸位置不变）
   - 如果 qingyue-3d.html 或其它页面也用到这张 badge，一并生效
4. 更新 src/vest_badge.py：改成生成方案 C（深绿圆章 RGB(52,84,44)、米白 RGB(240,232,198) 的印章与「启格科普」），注释里写明用的是启格印章标；或改成直接拷贝上面那张 png，二选一，保证脚本重跑出来是新章。
5. 不改页面底部提示文字（#hint 里的「凤凰岛科普 IP」先不动）。不改任何动物、操作、声音。

## 验收
- 本地起服务（python3 -m http.server 18977），用 playwright 截图：青蛙背面近景（白天 + 夜晚头灯各一张），能清楚看到马甲上是深绿「启格科普」印章，没有红色、没有「凤凰岛」字样。截图放 screens-v11b/。
- 跑 src/test_pond.py、test_v9、test_v10、test_v11，全部通过（软件渲染慢导致的超时不算）。报告 txt 不要放仓库根目录，放 screens-v11b/ 里。
- CHANGELOG 加 v11b 一小段。
- 推送到分支 v11b-qige-badge，不要推 main、不要合并。
- 完成后把 /Users/administrator/Tilo工作台/20261028-青跃三维/STATUS.txt 写成 DONE_V11B（附提交号、截图路径、测试结果）；卡住就写 BLOCKED_V11B 和原因。

## 偏好备忘
- 模型用 Opus 5.5；所有说明用中文。
- 青跃配色是绿系，品牌元素尽量不用红色。
