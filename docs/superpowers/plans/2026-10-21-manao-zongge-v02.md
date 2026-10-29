# 《目瑙纵歌》热门视频主体版 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付一支以《目瑙纵歌》前奏和高潮为主体、使用高播放量热门舞蹈画面、主持人口播约20秒的9:16无字净版新闻视频。

**Architecture:** 重新生成极短开场和结尾数字人；中间插播由歌曲0秒前奏与241秒高潮拼成约50秒连续音乐，画面使用B站10万至33万播放量的中国语境热门视频，全部取连续原速区间并仅做去边缘水印的裁切和等比缩小居中。最终按25fps帧边界拼接，并进行冻帧、文字、水印、响度、人物与完整解码质检。

**Tech Stack:** Topview text2voice/avatar4、FFmpeg/FFprobe、Bilibili来源素材、SHA-256。

## Global Constraints

- 输出为1080×1920、25fps、H.264/AAC、9:16。
- 固定主持人SHA-256：`939324593eb718cd2a39be4c171f74178a6a48442f7e0d61afe8a875011e8a47`。
- 固定音色：未来科技解说，`cobra_design_20250717_162347_664524`，neutral，1.0×。
- 插播约50秒，先前奏再高潮；主持人总口播约20秒，插播为主体。
- 不得出现水印、标题、字幕、静帧、慢放、循环、放大或变焦。
- 插播仅使用中国人物与可验证的中国场景；不出现身份不明的外国人物。
- 用户交付直接列出 `video/final-clean.mp4` 与独立侧文件，不生成ZIP。

---

### Task 1: 锁定脚本与热门素材

**Files:**
- Create: `output/manual-news-2026-10-21-manao-zongge-v02/copy/opening.txt`
- Create: `output/manual-news-2026-10-21-manao-zongge-v02/copy/closing.txt`
- Create: `output/manual-news-2026-10-21-manao-zongge-v02/production/footage-ledger.json`

- [ ] **Step 1:** 将开场压缩为一个问题，将结尾压缩为旋律源头、2025年改编和爆火机制三项事实。
- [ ] **Step 2:** 只批准播放量可核验且能裁掉边缘水印的连续运动区间。
- [ ] **Step 3:** 联系表逐人检查中国语境、外国人物、标题、字幕和水印。

### Task 2: 生成短口播与数字人

**Files:**
- Create: `output/manual-news-2026-10-21-manao-zongge-v02/audio/parts/opening.mp3`
- Create: `output/manual-news-2026-10-21-manao-zongge-v02/audio/parts/closing.mp3`
- Create: `output/manual-news-2026-10-21-manao-zongge-v02/video/opening-avatar.mp4`
- Create: `output/manual-news-2026-10-21-manao-zongge-v02/video/closing-avatar.mp4`

- [ ] **Step 1:** 使用固定音色分别生成开场和结尾配音。
- [ ] **Step 2:** 使用固定主持人和同一Topview board生成两段avatar4视频，不加字幕。
- [ ] **Step 3:** 以精确帧数核对数字人视频、驱动音频时长与音画起点。

### Task 3: 构建前奏—高潮插播主体

**Files:**
- Create: `output/manual-news-2026-10-21-manao-zongge-v02/audio/parts/song-intro-climax.wav`
- Create: `output/manual-news-2026-10-21-manao-zongge-v02/media/approved/song-popular-visual.mp4`

- [ ] **Step 1:** 取歌曲0.00–14.00秒前奏与241.00–277.666秒高潮，以0.5秒交叉淡化连接。
- [ ] **Step 2:** 从`BV1U6Nv68EGm`、`BV1roNq64EXZ`和`BV1NkLJ6gEKY`选择不重叠的连续动作区间。
- [ ] **Step 3:** 原速裁掉边缘平台标识，保持源画幅，等比缩小居中到9:16黑底；不放大、不循环。
- [ ] **Step 4:** 插播视音频统一到精确25fps帧数。

### Task 4: 成片合成与自动质检

**Files:**
- Create: `output/manual-news-2026-10-21-manao-zongge-v02/video/final-clean.mp4`
- Create: `output/manual-news-2026-10-21-manao-zongge-v02/qc/final-qc-report.json`
- Create: `output/manual-news-2026-10-21-manao-zongge-v02/qc/sha256.txt`

- [ ] **Step 1:** 按“短开场—约50秒歌曲插播—短结尾”拼接视频和音频。
- [ ] **Step 2:** 归一化为约-16 LUFS，真峰值不高于-1.5 dBFS。
- [ ] **Step 3:** 完整解码并核对容器时长、帧数、分辨率、帧率和音轨。
- [ ] **Step 4:** 对插播执行冻帧、黑帧、长静音和逐秒OCR检查。
- [ ] **Step 5:** 导演联系表复核所有可见人物、运动连续性、裁切和主题表达。
- [ ] **Step 6:** 生成主持人稿、完整节目文字稿、来源台账、时间线、QC报告和SHA-256记录。

