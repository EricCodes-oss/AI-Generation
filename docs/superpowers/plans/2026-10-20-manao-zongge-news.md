# 《目瑙纵歌》爆红背景新闻视频制作计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 制作默认主持人讲解《目瑙纵歌》由来与爆红原因、高潮段配少数民族舞蹈和打击乐实拍的无字净版新闻视频。

**Architecture:** 先以国家民委转载报道建立事实包，再从公开来源筛选歌曲高潮和无覆盖文字的中国现场实拍，生成默认音色和数字人，最后用 FFmpeg 在 9:16 画布中顺序合成。所有来源、时间线、视觉硬门和自动 QC 以 JSON/TXT 旁路记录。

**Tech Stack:** Python、Giggle/Topview 语音与数字人接口、yt-dlp、FFmpeg/ffprobe、Apple Vision OCR/人脸检测。

## Global Constraints

- 输出为 1080×1920、25fps、H.264、AAC 48kHz mono。
- 主持人参考图 SHA-256 必须为 `939324593eb718cd2a39be4c171f74178a6a48442f7e0d61afe8a875011e8a47`。
- 音色必须为 `未来科技解说`，ID `cobra_design_20250717_162347_664524`，neutral、1.0×。
- 插播只保留歌曲高潮，不用主持人口播覆盖歌曲高潮。
- 插播不得出现水印、账号标识、标题、字幕、静止帧、循环、倒放、慢放、放大或变焦。
- 人物与场景必须核验为中国少数民族活动或明确中国语境，身份不明的候选不得采用。
- 横屏镜头等比缩小居中并保留黑边，不裁切放大。
- 不生成 ZIP，直接交付视频和独立旁路文件。

---

### Task 1: 事实包、创意锁与脚本

**Files:**
- Create: `output/manual-news-2026-10-20-manao-zongge-v01/production/fact-evidence.json`
- Create: `output/manual-news-2026-10-20-manao-zongge-v01/production/creative-lock.json`
- Create: `output/manual-news-2026-10-20-manao-zongge-v01/copy/title.txt`
- Create: `output/manual-news-2026-10-20-manao-zongge-v01/copy/voiceover.txt`
- Create: `output/manual-news-2026-10-20-manao-zongge-v01/production/script-review.json`

- [ ] 保存两篇国家民委来源、可核事实、数字、时间线和禁止断言。
- [ ] 写成“听过旋律—追溯 1991—解释 2026 爆红—文化判断”的两段主持人口播。
- [ ] 检查每句事实可追溯、开头直接、结尾有判断、无空泛看画面转场。

### Task 2: 高潮和实拍素材筛选

**Files:**
- Create: `output/manual-news-2026-10-20-manao-zongge-v01/media/source/`
- Create: `output/manual-news-2026-10-20-manao-zongge-v01/media/approved/`
- Create: `output/manual-news-2026-10-20-manao-zongge-v01/production/footage-ledger.json`
- Create: `output/manual-news-2026-10-20-manao-zongge-v01/qc/broll-contact-sheet.jpg`

- [ ] 下载歌曲与云南德宏目瑙纵歌现场候选，记录 URL、下载时间和 SHA-256。
- [ ] 通过波形、歌词语义和听感确认 24—32 秒高潮自然乐句。
- [ ] 为每个现场候选制作逐秒联系表，拒绝水印、标题、字幕、身份不明或静态镜头。
- [ ] 对批准镜头运行 `freezedetect=n=-50dB:d=0.4`，只保留连续运动、1.0 倍速、原构图镜头。

### Task 3: 默认 TTS 与数字人

**Files:**
- Create: `output/manual-news-2026-10-20-manao-zongge-v01/audio/presenter-only.wav`
- Create: `output/manual-news-2026-10-20-manao-zongge-v01/video/presenter-master-avatar.mp4`
- Create: `output/manual-news-2026-10-20-manao-zongge-v01/production/generation-tasks.json`

- [ ] 使用锁定音色生成主持人口播，核对专名“目瑙纵歌、石勒干、甄臻、德宏”。
- [ ] 使用锁定主持人图和当前音频生成数字人，保存任务 ID。
- [ ] 验证主持人身份哈希、音画时长和嘴部运动，不复用旧口型。

### Task 4: 音频母版、时间线与成片

**Files:**
- Create: `output/manual-news-2026-10-20-manao-zongge-v01/audio/master-program.wav`
- Create: `output/manual-news-2026-10-20-manao-zongge-v01/production/timeline.json`
- Create: `output/manual-news-2026-10-20-manao-zongge-v01/copy/presenter-only-script.txt`
- Create: `output/manual-news-2026-10-20-manao-zongge-v01/copy/full-program-transcript.txt`
- Create: `output/manual-news-2026-10-20-manao-zongge-v01/video/final-clean.mp4`

- [ ] 顺序拼接主持人开场、歌曲高潮和主持人结尾的批准音频母版。
- [ ] 在高潮自然乐句边界安排连续实拍镜头，横屏素材等比居中，禁止缩放动画。
- [ ] 以 1080×1920、25fps、H.264、AAC 48kHz mono 渲染净版。

### Task 5: 自动 QC 与导演复核

**Files:**
- Create: `output/manual-news-2026-10-20-manao-zongge-v01/qc/final-contact-sheet.jpg`
- Create: `output/manual-news-2026-10-20-manao-zongge-v01/qc/final-qc-report.json`
- Create: `output/manual-news-2026-10-20-manao-zongge-v01/qc/sha256.txt`
- Create: `output/manual-news-2026-10-20-manao-zongge-v01/copy/source-ledger.txt`

- [ ] 完整解码并校验分辨率、帧率、编码、音频格式、帧数和时长。
- [ ] 运行黑帧、长静音、逐镜冻结、OCR、水印/标题/字幕和音频相关度检查。
- [ ] 人工查看全片、边界和插播联系表，确认人物、中国语境、鼓舞同步和无放大。
- [ ] 仅在所有硬门通过后写入 SHA-256 并直接交付文件路径。
