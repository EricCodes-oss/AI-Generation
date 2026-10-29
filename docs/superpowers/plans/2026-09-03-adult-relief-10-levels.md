# 成年人的十级释怀视频 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 生成一条无字幕、无标题、无水印可读文字的竖屏真实素材口播视频。

**Architecture:** 使用现有主持人开场/收尾资产，中间以 FFmpeg 生成十段经裁切审查的真实网络素材；用 Giggle TTS 生成连续主持人口播，再以统一时间线合成最终 MP4。

**Tech Stack:** FFmpeg、ffprobe、Giggle TTS、现有主持人 MP4、Bilibili/Douyin 真实素材、JSON/Markdown 交付记录。

## Global Constraints

- 成片不添加字幕、标题、等级文字、贴纸、Logo 或来源条。
- 插播素材必须是真实网络视频，禁止 AI 生成。
- 插播素材内不得出现可读字幕、标题、账号名、水印、平台标识或时间戳。
- 插播原声静音，只保留主持人口播。
- 口播采用凝练、克制、具有文学质感的主流媒体播报风格。

### Task 1: 固化口播与来源记录

**Files:**
- Modify: `output/adult-relief-10-levels-v02/copy/voiceover.txt`
- Create: `output/adult-relief-10-levels-v02/copy/full-program-transcript.txt`
- Create: `output/adult-relief-10-levels-v02/copy/source-links.txt`

- [ ] 写入已审核口播稿，并保持固定开头两句。
- [ ] 记录每个真实网络素材的来源 URL、文件路径、使用时间段和文字清除方式。

### Task 2: 生成主持人口播

**Files:**
- Create: `output/adult-relief-10-levels-v02/audio/master.wav`

- [ ] 使用项目固定音色“未来科技解说”、neutral、speed 1.08 生成连续口播。
- [ ] 运行 ffprobe 检查音频采样率、声道与时长。

### Task 3: 制作无文字真实素材片段

**Files:**
- Create: `output/adult-relief-10-levels-v02/media/segments/01.mp4` 至 `10.mp4`
- Create: `output/adult-relief-10-levels-v02/media/approved/broll-10-levels.mp4`

- [ ] 对每段素材只保留与口播动作对应的画面中心区域。
- [ ] 不使用任何带有无法去除的文字画面。
- [ ] 每段静音并统一为 1080×1920、25fps。
- [ ] 生成 contact sheet，人工确认无可读文字。

### Task 4: 合成与交付

**Files:**
- Create: `output/adult-relief-10-levels-v02/video/final-clean.mp4`
- Create: `output/adult-relief-10-levels-v02/production/timeline.json`
- Create: `output/adult-relief-10-levels-v02/production/delivery-manifest.json`
- Create: `output/adult-relief-10-levels-v02/qc/*`

- [ ] 合成主持人开头、十段插播和主持人结尾。
- [ ] 确认没有任何绘制文字滤镜。
- [ ] 合并连续口播并检查是否存在黑帧、明显静音或解码错误。
- [ ] 输出所有 QC 报告与 SHA256。
