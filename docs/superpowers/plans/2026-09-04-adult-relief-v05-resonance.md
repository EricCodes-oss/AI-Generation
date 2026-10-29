# 成年人的十级释怀 v05 共鸣重做 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重做四个语义弱段，交付与口播逐句形成动作共鸣的 v05 竖屏成片。

**Architecture:** v04 作为只读基线；v05 复制音频、主持人和已通过段落，仅替换第 2、3、4、7 级。用统一 FFmpeg 规格拼接，随后建立逐段语义审查和完整 QC 证据。

**Tech Stack:** Bilibili 真实素材、FFmpeg/ffprobe、JSON/Markdown 交付记录。

## Global Constraints

- 不覆盖 `output/adult-relief-10-levels-v04`。
- 插播全部为中国真实网络素材；无 AI、影视剧、字幕、水印、Logo 和原声。
- 主持人和音频沿用 v04；输出 1080x1920、25fps、H.264、yuv420p、AAC 48kHz 单声道。
- 语义硬门槛：第 3/4 级必须有可识别动作，第 2/7 级必须有明确关系分离或路线变化。

### Task 1: 建立 v05 基线

- [ ] 复制 v04 的音频、主持人、已通过段落和记录到 v05。
- [ ] 从候选库筛选第 2/3/4/7 级的新源区间，制作抽帧联系表。

### Task 2: 重剪四个弱段

- [ ] 以单一连续动作生成 02、03、04、07，统一为 1080x1920、25fps、无音轨。
- [ ] 复核四段与对应口播的动作、情绪和结尾落点，不通过则继续替换。

### Task 3: 合成与验收

- [ ] 拼接 v05 B-roll、v04 主持人和 master 音频。
- [ ] 运行 ffprobe、完整解码、黑帧、OCR、时长、音频相关性和 SHA-256 检查。
- [ ] 写入语义导演审查、最终 QC 和交付清单。
