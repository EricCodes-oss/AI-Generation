# 许家印恒大案购房者结尾 V3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 生成一版增加烂尾楼、房屋交付和损失追偿视角的许家印恒大案 V3 新闻成片。

**Architecture:** 继承 V2 的权威事实、开场、原声和插播素材，仅重做后半段口播、主音频、数字人和最终时间线。权威原声结束后始终使用主持人画面。

**Tech Stack:** Giggle TTS，Topview avatar4，FFmpeg，avatar_pipeline V5 QC。

## Global Constraints

- 不得将一审表述为终审生效。
- 不得承诺所有购房者将获得足额退赔或立即交房。
- 不新增字幕、标题、Logo、来源条和背景音乐。
- 原声插播无倒放、循环和重复填充。
- 后半段主持人声音必须对应主持人画面。

---

### Task 1: 创建 V3 文案和事实记录

**Files:**
- Create: `output/manual-news-2026-08-20-许家印恒大案一审宣判-v03/`
- Modify: `copy/voiceover.txt`
- Modify: `production/fact-evidence.json`
- Modify: `production/script-review.json`

- [x] 复用 V2 的权威事实、开场和原声。
- [x] 将方案A文案写入后半段，并增加“不承诺具体退赔”的禁止扩大项。
- [x] 执行稿件事实边界检查，预期一审、退赔优先和未公布时间表三项均可追溯。

### Task 2: 重做后半段 TTS 和完整主音频

**Files:**
- Create: `audio/parts/closing.mp3`
- Create: `audio/parts/closing.wav`
- Create: `audio/master-voiceover.wav`
- Modify: `production/tts-tasks.json`

- [x] 使用 `cobra_design_20250717_162347_664524` 和 `neutral` 生成新收尾。
- [x] 按“开场 + 0.2秒停顿 + 36.04秒原声 + 0.2秒停顿 + 新收尾”合成 48kHz mono PCM 主音频。
- [x] 用 `ffprobe` 记录新时长和 SHA-256。

### Task 3: 重做数字人与成片

**Files:**
- Create: `video/anchor.mp4`
- Create: `production/timeline.json`
- Create: `production/render.sh`
- Create: `video/final-clean.mp4`

- [x] 使用锁定主持人图片和新主音频提交 Topview avatar4。
- [x] 设置时间线：开场主持人、36.04秒权威原声插播、剩余全部主持人。
- [x] 渲染 1080x1920、25fps、H.264 + AAC 48kHz mono 净版成片。
- [x] 验证原声结束后不存在插播画面。

### Task 4: 重做逐字稿、QC 和交付

**Files:**
- Create: `copy/full-program-transcript.txt`
- Create: `qc/final-qc-report.json`
- Create: `qc/director-review.json`
- Create: `production/delivery-manifest.json`

- [x] 生成包含全部权威原声的完整节目逐字稿。
- [x] 生成 ffprobe、黑帧、静音、解码、音频相关性和审核接触表证据。
- [x] 执行十项导演复审，重点验证购房者表述的事实边界和后半段声画对齐。
- [x] 仅在状态为 `ready_to_deliver` 且全部硬门通过后交付。
