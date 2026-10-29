# 休息习惯参考复刻实施计划

**Goal:** 使用 BV1i1mLB9E5w 完整台词制作默认主持人与音色的净版新闻视频。

**Architecture:** 复用已验证制作脚本，单独建立 tmp/bv1i1-production 与 output/manual-news-2026-10-14-rest-habits-v01，禁止覆盖旧节目。按自然配音时长选择中国语境动态镜头，FFmpeg 合成并完成技术和导演检查。

**Tech Stack:** Whisper、Apple Vision、Giggle TTS、Topview avatar4、FFmpeg。

## Global Constraints

1080×1920，25fps；默认 host 哈希 939324593eb718cd2a39be4c171f74178a6a48442f7e0d61afe8a875011e8a47；音色 cobra_design_20250717_162347_664524；插播正常速度、不放大、不定格、不循环；无字净版。

- [x] 下载参考片；原声和逐秒画面校对五段台词，保存原始识别记录和脚本审查。
- [x] 编写 tmp/bv1i1-production/produce.py 并提交五段默认配音。
- [ ] 执行 python3 tmp/bv1i1-production/produce.py collect_tts，五段 WAV 完成；核对生成发音。
- [ ] 执行 python3 tmp/bv1i1-production/produce.py avatar_submit，随后 avatar_collect，核验首尾文件完整解码。
- [ ] 筛选三种习惯相同动作的清晰中国资料，审核每一可识别人物、裁切是否丢失关键行为、字幕水印、是否保持正常运动；写入 footage-ledger.json。
- [ ] 按生成语音逐句对应动态镜头，制作 audio/master-voiceover.wav、timeline.json 和完整节目稿。
- [ ] 渲染 video/candidate-clean.mp4，完整解码、音频母版比对、全镜联系表、5Hz OCR、全帧动态、主持人闪烁检查，失败即自主修复。
- [ ] 验证 video/final-clean.mp4、稿件、来源记录、QC 和哈希；manifest 通过后直接交付。

执行方式：当前会话连续完成，无常规确认；检查既有文件与媒体为本任务验证，不添加镜像实现的单元测试，不修改公共流程。
