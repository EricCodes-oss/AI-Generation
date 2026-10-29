# 饭后口渴参考片制作计划

**Goal:** 使用默认主持人与音色制作BV1smmxBAEbQ参考片，完整呈现用户批准的事实核查稿，洁净插播可验证。

**Architecture:** 独立制作目录，复用已验证TTS、Topview Avatar4与FFmpeg流程。原声转写与OCR校对全文；医学说法核验后锁定稿件。既有全过程授权覆盖普通制作步骤，重大事实冲突按AGENTS.md处理。

**Tech Stack:** Python、FFmpeg、Whisper、Apple Vision、Giggle TTS、Topview Avatar4。

**Editorial decision:** 用户在核查稿及采用确认问题后回复“继续”，已授权采用提议的事实核查版全文；不再执行有事实冲突的逐字参考稿。默认主持人、音色、结构与高清洁净素材要求继续有效。

- [x] 下载高清原片，原声转写，逐0.5秒OCR与每帧人物扫描。
- [x] 保存参考原文转写，医学资料、冲突核查与可审阅处理方案；院名转写简写差异已注明，未锁定制作稿。
- [x] 提取无标题水印及原主持人的中国语境食物细节、原片动画，并复核动态与包装残留。
- [x] 医学事实冲突解决后锁定最终口播，默认音色TTS与主持人开场结尾生成。
- [x] 合成、全部节目台词、解码/音轨/口型/人物/OCR/动态/帧一致性验证及导演复核。
- [x] 哈希和直接final-clean.mp4交付文件验证。

**Verified output:** `output/manual-news-2026-10-11-food-thirst-v01/video/final-clean.mp4`，44.24秒，1080×1920，25fps，1106帧。全部质检通过；直接文件交付，不创建ZIP。
