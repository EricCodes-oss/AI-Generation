# 小孩哥“通透不分年龄”混剪实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 使用用户确认的主持人口播、无覆盖文字的小孩哥连续原声画面和默认主持人，制作并交付一条通过硬质检的 9:16 无字净版视频。

**Architecture:** 先锁定逐字主持稿、参考原声转录和来源证据，再从中国平台寻找同一人物、同一场景、同一段表达的无水印原片，拒绝用模糊、放大或静帧遮掩覆盖文字。主持人开头和结尾分别生成默认音色与数字人，中间完整保留小孩哥连续原声，最后由 FFmpeg 顺序合成并生成逐镜 QC 旁路记录。

**Tech Stack:** Python、Giggle TTS、Topview/Giggle 数字人接口、FFmpeg/ffprobe、Whisper、Apple Vision OCR。

## Global Constraints

- 主持人口播逐字使用用户在 2026-10-22 确认的开头和结尾；`▎【小孩哥原声】` 只作结构标记，不参与 TTS。
- 主持人和音色使用项目默认值：`host-c2-pro-candidate-2-final`、`未来科技解说`、`cobra_design_20250717_162347_664524`。
- 中间插播连续保留小孩哥原声，不出现参考主持人、标题、字幕、水印、平台角标或账号标识。
- 插播必须为同一小孩哥、同一场景和同一段表达，不用相似人物或库存画面替代。
- 插播保持 1.0 倍正常速度和连续真实运动，不添加静止帧、循环、倒放、慢放、放大、推拉或缩放动画。
- 输出为 1080×1920、25fps、H.264、AAC 48kHz 单声道；无字幕、标题、Logo、音乐。
- 对每位可见人物核验中国语境，记录 `china_context_verified`、`foreign_person_detected` 和 `people_identity_check`。
- 不创建 ZIP；直接交付 `video/final-clean.mp4` 与独立旁路文件。

---

### Task 1: 锁定脚本、参考转录与生产记录

**Files:**
- Create: `output/manual-news-2026-10-21-child-insight-v01/copy/presenter-only-script.txt`
- Create: `output/manual-news-2026-10-21-child-insight-v01/copy/reference-source-transcript.txt`
- Create: `output/manual-news-2026-10-21-child-insight-v01/copy/source-links.txt`
- Create: `output/manual-news-2026-10-21-child-insight-v01/production/creative-lock.json`
- Create: `output/manual-news-2026-10-21-child-insight-v01/production/script-review.json`

**Interfaces:**
- Consumes: `tmp/user-ref-BV13r5Q6TELS/reference.mp4`、用户确认的两段主持人口播。
- Produces: 两段逐字主持稿、带时间码的参考原声转录、锁定的创意契约。

- [ ] **Step 1: 将主持人口播从草稿提升为锁定稿**

开头逐字为：`有这样一个“小孩哥”，年纪不大，说起人生却比不少成年人还通透。有些道理，有人走过半生才慢慢明白，他却早早就想清楚了。`

结尾逐字为：`年纪虽小，活得却明白。原来，看懂人生从来不分年龄：有人活了一辈子，依然糊里糊涂；有人年纪轻轻，心里早已透亮。`

- [ ] **Step 2: 用 Whisper 结果和参考画面烧录字幕交叉校准小孩哥原声**

Run: `ffmpeg -v error -i tmp/user-ref-BV13r5Q6TELS/reference.mp4 -f null -`

Expected: exit code `0`，参考片完整解码，时长约 `36.18` 秒。

- [ ] **Step 3: 校验稿件边界**

Run: `rg -n '有一个视频|这个视频|我们一起来看|接下来请看|看完这段视频' output/manual-news-2026-10-21-child-insight-v01/copy/presenter-only-script.txt`

Expected: 无输出，退出码 `1`。

### Task 2: 获取并批准同源无字原片

**Files:**
- Create: `output/manual-news-2026-10-21-child-insight-v01/research/source-search.json`
- Create: `output/manual-news-2026-10-21-child-insight-v01/media/source/reference-original.mp4`
- Create: `output/manual-news-2026-10-21-child-insight-v01/media/source/source-clean-candidate.mp4`
- Create: `output/manual-news-2026-10-21-child-insight-v01/media/approved/insert-child-clean.mp4`
- Create: `output/manual-news-2026-10-21-child-insight-v01/production/footage-ledger.json`
- Create: `output/manual-news-2026-10-21-child-insight-v01/qc/insert-contact-sheet.jpg`
- Create: `output/manual-news-2026-10-21-child-insight-v01/qc/insert-freezedetect.log`

**Interfaces:**
- Consumes: 参考标题、发布说明、逐字原声、人物外观和夜间户外背景。
- Produces: 与参考一致、无覆盖文字、含原声、1.0 倍速的连续批准插播。

- [ ] **Step 1: 用完整引语、发布时间线索和“内蒙古”检索中国平台同源原片**

检索词必须包含：`人生逆袭发展的顺序 首先你得行`、`说你行的人得行 小孩`、`小孩哥 人生逆袭 内蒙古`。记录每个候选 URL、发布者、发布时间、分辨率、时长和同源判断。

- [ ] **Step 2: 下载最高可用清晰度并核验同源身份**

批准条件：同一小孩哥、同一衣着、同一夜间背景、同一连续发言、口型与原声同步；任何一项不一致即拒绝。

- [ ] **Step 3: 逐秒检查全部画面覆盖和人物**

Run: `ffmpeg -y -v error -i output/manual-news-2026-10-21-child-insight-v01/media/source/source-clean-candidate.mp4 -vf "fps=2,scale=270:480,tile=6x12" -frames:v 1 output/manual-news-2026-10-21-child-insight-v01/qc/insert-contact-sheet.jpg`

Expected: 联系表覆盖全段；不存在标题、字幕、水印、Logo、平台角标、账号标识或外国人物。

- [ ] **Step 4: 验证连续运动、正常速度和原始构图**

Run: `ffmpeg -v warning -i output/manual-news-2026-10-21-child-insight-v01/media/approved/insert-child-clean.mp4 -vf "freezedetect=n=-50dB:d=0.4" -an -f null - 2> output/manual-news-2026-10-21-child-insight-v01/qc/insert-freezedetect.log`

Expected: 日志中无 `freeze_start`；台账记录 `playback_speed=1.0`、`zoom_added=false`、`freeze_frames_added=false`、`loop=false`。

### Task 3: 生成默认 TTS 与主持人视频

**Files:**
- Create: `output/manual-news-2026-10-21-child-insight-v01/audio/opening.wav`
- Create: `output/manual-news-2026-10-21-child-insight-v01/audio/closing.wav`
- Create: `output/manual-news-2026-10-21-child-insight-v01/video/opening-avatar.mp4`
- Create: `output/manual-news-2026-10-21-child-insight-v01/video/closing-avatar.mp4`
- Create: `output/manual-news-2026-10-21-child-insight-v01/production/generation-tasks.json`

**Interfaces:**
- Consumes: Task 1 的两段锁定稿、默认音色 ID、默认主持人图。
- Produces: 48kHz 单声道开场和结尾音频，以及分别匹配口型的开场和结尾数字人视频。

- [ ] **Step 1: 分别生成开头和结尾 TTS**

要求：`未来科技解说`、neutral、1.0×；引号不读作“引号”，冒号和分号只控制停顿。

- [ ] **Step 2: 标准化音频并完整解码**

Run: `ffmpeg -v error -i output/manual-news-2026-10-21-child-insight-v01/audio/opening.wav -f null - && ffmpeg -v error -i output/manual-news-2026-10-21-child-insight-v01/audio/closing.wav -f null -`

Expected: 两条命令均退出 `0`，采样率 `48000`、声道数 `1`。

- [ ] **Step 3: 分别驱动默认主持人并校验身份与时长**

要求：主持人参考图 SHA-256 为 `939324593eb718cd2a39be4c171f74178a6a48442f7e0d61afe8a875011e8a47`；主持人视频与对应音频时长差不超过 `0.12` 秒。

### Task 4: 建立完整音频、时间线与成片

**Files:**
- Create: `output/manual-news-2026-10-21-child-insight-v01/audio/master-program.wav`
- Create: `output/manual-news-2026-10-21-child-insight-v01/production/timeline.json`
- Create: `output/manual-news-2026-10-21-child-insight-v01/production/program-transcript.json`
- Create: `output/manual-news-2026-10-21-child-insight-v01/copy/full-program-transcript.txt`
- Create: `output/manual-news-2026-10-21-child-insight-v01/production/render.sh`
- Create: `output/manual-news-2026-10-21-child-insight-v01/video/final-clean.mp4`

**Interfaces:**
- Consumes: 开场数字人、批准插播、结尾数字人及三段已批准音频。
- Produces: 主持人开场 → 小孩哥连续原声 → 主持人结尾的唯一最终母版。

- [ ] **Step 1: 将三段音频响度标准化后顺序拼接为完整节目母版**

目标：主持人约 `-16 LUFS`，插播原声以对白清楚且不过载为准，峰值不高于 `-1 dBTP`。

- [ ] **Step 2: 建立精确到帧的时间线和完整节目转录**

时间线只允许三段一级结构；插播保持完整连续，不切成静态填充，不循环。

- [ ] **Step 3: 渲染无字净版**

Run: `bash output/manual-news-2026-10-21-child-insight-v01/production/render.sh`

Expected: 生成 `video/final-clean.mp4`，编码为 H.264、1080×1920、25fps；音频为 AAC、48000Hz、mono。

### Task 5: 自动 QC、导演 QC 与直接交付

**Files:**
- Create: `output/manual-news-2026-10-21-child-insight-v01/qc/final-probe.json`
- Create: `output/manual-news-2026-10-21-child-insight-v01/qc/final-contact-sheet.jpg`
- Create: `output/manual-news-2026-10-21-child-insight-v01/qc/final-freezedetect.log`
- Create: `output/manual-news-2026-10-21-child-insight-v01/qc/final-blackdetect.log`
- Create: `output/manual-news-2026-10-21-child-insight-v01/qc/final-silencedetect.log`
- Create: `output/manual-news-2026-10-21-child-insight-v01/qc/final-qc-report.json`
- Create: `output/manual-news-2026-10-21-child-insight-v01/qc/director-review.json`
- Create: `output/manual-news-2026-10-21-child-insight-v01/qc/sha256.txt`
- Create: `output/manual-news-2026-10-21-child-insight-v01/production/delivery-manifest.json`

**Interfaces:**
- Consumes: `video/final-clean.mp4`、时间线、完整节目转录、素材台账。
- Produces: 自动与人工质检证据，以及只在全部硬门通过后标记为 `ready_to_deliver` 的交付清单。

- [ ] **Step 1: 完整解码并核对技术规格**

Run: `ffmpeg -v error -i output/manual-news-2026-10-21-child-insight-v01/video/final-clean.mp4 -f null -`

Expected: 退出 `0`，无解码错误；单视频流和单音频流。

- [ ] **Step 2: 运行冻结、黑帧、静音和逐秒联系表检查**

硬失败：任何插播静帧、放大、缩放动画、循环、覆盖文字、外国人物、未核验人物身份、主持人未回场或结尾不完整。

- [ ] **Step 3: 完成两遍导演审核**

第一遍无声检查构图、运动、文字和人物；第二遍有声检查原声完整性、口型、响度、转场和语义节奏。

- [ ] **Step 4: 写入 SHA-256 和交付状态**

Run: `shasum -a 256 output/manual-news-2026-10-21-child-insight-v01/video/final-clean.mp4 > output/manual-news-2026-10-21-child-insight-v01/qc/sha256.txt`

Expected: `production/delivery-manifest.json` 的 `status` 为 `ready_to_deliver`，直接列出最终视频和旁路文件，不包含 ZIP。
