# 成年人的十级释怀 v04 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付一条插播全部为中国真实网络素材、无任何文字、主持人口型逐句同步的 v04 竖屏成片。

**Architecture:** v04 复用已经确认的口播音频与精确时间线，但建立独立素材、数字人和 QC 目录。中国网络原片先进入候选库，经来源、人物、清晰度、文字和语义五项筛选后再裁切；主持人按自然句切分音频并以标准 avatar4 分段生成，最后由 FFmpeg 统一拼接和验收。

**Tech Stack:** FFmpeg/ffprobe、Topview avatar4、Bilibili/中国原创平台真实素材、Faster-Whisper 时间戳、PaddleOCR/Tesseract、JSON/Markdown 交付记录。

## Global Constraints

- 保留 `output/adult-relief-10-levels-v03`，所有新产物写入 `output/adult-relief-10-levels-v04`。
- 十段插播只使用中国平台或中国原创作者的真实网络素材，禁止 AI 生成和影视剧素材。
- 人物镜头只能出现可确认的中国人；无法确认时改用国内无人场景。
- 最终画面不得出现字幕、标题、账号名、水印、平台 Logo、时间戳或其他可读文字。
- 插播原声全部移除，只保留现有主持人口播。
- 主持人必须使用标准 `avatar4` 和实际音频驱动，不得使用 `avatar4Fast` 或重新 TTS。
- 输出为 `1080x1920`、25fps、H.264、yuv420p、AAC 48kHz 单声道。

---

### Task 1: 固化 v04 工作区和输入

**Files:**
- Create: `output/adult-relief-10-levels-v04/copy/voiceover.txt`
- Create: `output/adult-relief-10-levels-v04/copy/full-program-transcript.txt`
- Create: `output/adult-relief-10-levels-v04/audio/opening-full.wav`
- Create: `output/adult-relief-10-levels-v04/audio/closing-full.wav`
- Create: `output/adult-relief-10-levels-v04/audio/master.wav`
- Create: `output/adult-relief-10-levels-v04/production/timeline.json`

**Interfaces:**
- Consumes: v03 已确认口播、音频和 ASR 时间线。
- Produces: v04 唯一的内容、音频和时间基准。

- [ ] **Step 1: 复制已确认输入到独立目录**

Run: `mkdir -p output/adult-relief-10-levels-v04/{audio,copy,media/{avatar,candidates,approved,segments},production,qc,video} && cp output/adult-relief-10-levels-v03/copy/{voiceover.txt,full-program-transcript.txt} output/adult-relief-10-levels-v04/copy/ && cp output/adult-relief-10-levels-v03/audio/{opening-full.wav,closing-full.wav} output/adult-relief-10-levels-v04/audio/ && cp output/adult-relief-10-levels-v02/audio/master.wav output/adult-relief-10-levels-v04/audio/master.wav && cp output/adult-relief-10-levels-v03/production/timeline.json output/adult-relief-10-levels-v04/production/timeline.json`

Expected: 五个基准文件存在，v03 文件未改变。

- [ ] **Step 2: 验证音频时长与格式**

Run: `ffprobe -v error -show_entries format=duration:stream=sample_rate,channels -of json output/adult-relief-10-levels-v04/audio/opening-full.wav output/adult-relief-10-levels-v04/audio/closing-full.wav`

Expected: 开场约 21.92 秒、结尾约 20.148 秒，48kHz 单声道。

### Task 2: 筛选中国真实网络素材

**Files:**
- Create: `output/adult-relief-10-levels-v04/production/footage-ledger.json`
- Create: `output/adult-relief-10-levels-v04/production/shot-selection.json`
- Create: `output/adult-relief-10-levels-v04/media/candidates/*.mp4`

**Interfaces:**
- Consumes: 十级画面映射和公开来源元数据。
- Produces: 每一级一个或多个已批准原片及其精确使用区间。

- [ ] **Step 1: 搜索并下载候选原片**

对每一级至少保存两个中国来源候选；台账必须包含 `level`、`platform`、`url`、`author`、`title`、`published_at`、`downloaded_at`、`local_file`、`source_in`、`source_out`、`narrative_match`、`people_check`、`text_check` 和 `rights_note`。

- [ ] **Step 2: 生成候选联系表**

Run: `for candidate_file in output/adult-relief-10-levels-v04/media/candidates/*.mp4; do candidate_name="${candidate_file##*/}"; ffmpeg -hide_banner -loglevel error -y -i "$candidate_file" -vf "fps=1/2,scale=270:-2,tile=4x4" -frames:v 1 "output/adult-relief-10-levels-v04/qc/${candidate_name%.mp4}-sheet.jpg"; done`

Expected: 每条候选均有覆盖选用区间的清晰抽帧，可人工检查人物、文字和叙事动作。

- [ ] **Step 3: 执行五项准入检查**

逐条确认来源为中国平台/中国原创、人物为中国人或无人、清晰度不低于可用 720p、画面无可读文字、动作与对应口播直接相关。不合格候选不进入 `shot-selection.json`。

### Task 3: 生成高精度主持人

**Files:**
- Create: `output/adult-relief-10-levels-v04/audio/avatar-parts/*.wav`
- Create: `output/adult-relief-10-levels-v04/media/avatar/parts/*.mp4`
- Create: `output/adult-relief-10-levels-v04/media/avatar/opening-sync.mp4`
- Create: `output/adult-relief-10-levels-v04/media/avatar/closing-sync.mp4`
- Create: `output/adult-relief-10-levels-v04/production/avatar-tasks.json`

**Interfaces:**
- Consumes: 已确认主持人肖像、开场和结尾实际 WAV。
- Produces: 与每个源音频句段一一对应的标准 avatar4 视频。

- [ ] **Step 1: 按自然停顿切分实际音频**

使用 silencedetect 和 ASR 句界确定切点，每段保留原始采样，不改变语速、音高或内容。

- [ ] **Step 2: 提交标准 avatar4 音频驱动任务**

Run: `for part_file in output/adult-relief-10-levels-v04/audio/avatar-parts/*.wav; do part_name="${part_file##*/}"; python /Users/liuweidong/.codex/skills/topviewai-skill/scripts/avatar4.py run --image output/adult-relief-10-levels-v03/media/avatar/host-portrait-cn.jpg --audio "$part_file" --mode avatar4 --board-id 6a8396054d1840c5bc7e6eb7129271d0 --output "output/adult-relief-10-levels-v04/media/avatar/parts/${part_name%.wav}.mp4" --timeout 1200; done`

Expected: 每段任务状态为 success；命令不包含 `--caption`、`--text` 或 `--voice`。

- [ ] **Step 3: 无缝拼接句段**

将视频按对应 WAV 的精确时长裁齐，在原静音切点拼接为 `opening-sync.mp4` 和 `closing-sync.mp4`，最终节目仍使用原始口播总音轨。

### Task 4: 制作十段无字插播

**Files:**
- Create: `output/adult-relief-10-levels-v04/media/segments/01.mp4` through `10.mp4`
- Create: `output/adult-relief-10-levels-v04/media/approved/broll-10-levels-cn.mp4`
- Create: `output/adult-relief-10-levels-v04/production/build_video.sh`

**Interfaces:**
- Consumes: `shot-selection.json` 的原片、入点、出点和 v03 精确时长。
- Produces: 总长 81.88 秒、无原声、无文字的十段中国素材。

- [ ] **Step 1: 裁切并统一十段规格**

每段使用 `scale/crop` 或模糊背景加清晰前景构图，主体不得被破坏；编码为 1080x1920、25fps、H.264、yuv420p，并删除音轨。

- [ ] **Step 2: 校验逐段时长**

Expected durations: `9.26, 7.84, 6.30, 7.06, 7.42, 9.16, 8.82, 9.32, 8.20, 8.50` seconds，容差不超过一帧。

- [ ] **Step 3: 生成十级联系表并复核**

Run: `ffmpeg -hide_banner -loglevel error -i output/adult-relief-10-levels-v04/media/approved/broll-10-levels-cn.mp4 -vf "fps=1/4,scale=270:480,tile=5x5" -frames:v 1 output/adult-relief-10-levels-v04/qc/broll-contact.jpg`

Expected: 十级语义匹配，无外国人，无字幕、标题、水印、Logo 或时间戳。

### Task 5: 口型专项检查与修复

**Files:**
- Create: `output/adult-relief-10-levels-v04/qc/lipsync-opening-slow.mp4`
- Create: `output/adult-relief-10-levels-v04/qc/lipsync-closing-slow.mp4`
- Create: `output/adult-relief-10-levels-v04/qc/avatar-audio-alignment.json`
- Create: `output/adult-relief-10-levels-v04/qc/lipsync-review.json`

**Interfaces:**
- Consumes: 拼接后的主持人视频和原始 WAV。
- Produces: 可复核的波形偏移与逐句视觉检查记录。

- [ ] **Step 1: 检查源音频与主持人视频音频的相关偏移**

提取生成视频音频并与对应源 WAV 进行归一化互相关，记录峰值偏移和相关度；容差为一帧（40ms）。

- [ ] **Step 2: 制作嘴部区域慢放检查视频**

Run: `ffmpeg -hide_banner -loglevel error -y -i output/adult-relief-10-levels-v04/media/avatar/opening-sync.mp4 -filter_complex "[0:v]crop=420:300:330:560,scale=1080:-2,setpts=2*PTS[v];[0:a]atempo=0.5[a]" -map "[v]" -map "[a]" output/adult-relief-10-levels-v04/qc/lipsync-opening-slow.mp4 && ffmpeg -hide_banner -loglevel error -y -i output/adult-relief-10-levels-v04/media/avatar/closing-sync.mp4 -filter_complex "[0:v]crop=420:300:330:560,scale=1080:-2,setpts=2*PTS[v];[0:a]atempo=0.5[a]" -map "[v]" -map "[a]" output/adult-relief-10-levels-v04/qc/lipsync-closing-slow.mp4`

Expected: 0.5 倍速视频覆盖完整开场/结尾，可看清嘴唇闭合和张开时点。

- [ ] **Step 3: 逐句人工审查**

`lipsync-review.json` 对每句记录 `source_start`、`source_end`、`onset`、`pause`、`closed_lip`、`plosive`、`result`。任何一句失败时仅重新生成该句并重复 Steps 1-3。

### Task 6: 合成、全量 QC 与交付

**Files:**
- Create: `output/adult-relief-10-levels-v04/video/final-clean.mp4`
- Create: `output/adult-relief-10-levels-v04/qc/final-probe.json`
- Create: `output/adult-relief-10-levels-v04/qc/final-qc-report.json`
- Create: `output/adult-relief-10-levels-v04/qc/director-review.json`
- Create: `output/adult-relief-10-levels-v04/production/delivery-manifest.json`
- Create: `output/adult-relief-10-levels-v04/copy/source-links.txt`

**Interfaces:**
- Consumes: 通过审核的主持人、十级插播、现有完整口播音轨。
- Produces: 可交付的 v04 成片和完整证据包。

- [ ] **Step 1: 合成无文字成片**

按 `opening -> ten levels -> closing` 拼接画面，映射原始连续口播音轨；不使用任何 drawtext、subtitles、overlay Logo 或贴纸滤镜。

- [ ] **Step 2: 执行技术 QC**

运行 ffprobe、blackdetect、silencedetect、完整解码、逐段时长、音频格式、总时长、OCR 抽帧和 SHA-256 检查。

- [ ] **Step 3: 执行导演 QC**

完整观看开场、十段边界和结尾；逐项确认中国来源、中国人物/无人场景、画面语义、无文字和口型同步。

- [ ] **Step 4: 写入交付记录**

`delivery-manifest.json` 记录成片路径、字节数、时长、编解码规格、校验和、十段来源和全部 QC 结论。
