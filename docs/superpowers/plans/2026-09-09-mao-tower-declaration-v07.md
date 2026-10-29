# Mao Tower Declaration V07 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve the approved presenter copy while replacing the weak first insert and adding an authentic Tiananmen-tower declaration clip with audible historical speech.

**Architecture:** Reuse the locked V06 presenter opening and closing. Select clean frames and original audio from newly downloaded high-resolution archival footage, produce vertical insert masters, then concatenate sequentially without any presenter/insert audio overlap.

**Tech Stack:** FFmpeg, ffprobe, yt-dlp, Python/Pillow for contact sheets.

## Global Constraints

- Presenter remains `host-c2-pro-candidate-2-final`.
- Voice remains `未来科技解说` / `cobra_design_20250717_162347_664524`, neutral, speed 1.1.
- Presenter copy remains unchanged.
- Inserts contain no presenter, burned subtitles, editorial title, platform watermark, mask, or AI-generated footage.
- The tower declaration retains the historical source audio; presenter audio must not overlap insert audio.
- Deliver only the final MP4; do not create a ZIP.

---

### Task 1: Locate and approve archival source windows

**Files:**
- Inspect: `output/manual-news-2026-09-09-mao-50th-v06/media/sources/search/dqIyfWbxnJc.mp4`
- Create: `output/manual-news-2026-09-09-mao-50th-v07/qc/source-contact.jpg`

- [ ] Extract contact sheets at short intervals and identify the exact tower-declaration window.
- [ ] Verify the chosen frames contain no burned subtitles, editorial title, or watermark.
- [ ] Verify the selected audio contains the historical declaration rather than a modern narrator.

### Task 2: Build revised vertical inserts and timeline

**Files:**
- Create: `output/manual-news-2026-09-09-mao-50th-v07/media/approved/insert-*.mp4`
- Create: `output/manual-news-2026-09-09-mao-50th-v07/production/timeline.json`
- Create: `output/manual-news-2026-09-09-mao-50th-v07/production/render.sh`

- [ ] Replace the first insert with a stronger, complete archival Mao shot.
- [ ] Add the declaration shot at the emotional midpoint and keep its original audio intelligible.
- [ ] Preserve the existing presenter opening and closing without regeneration.
- [ ] Render sequential audio/video segments with no overlap or gaps.

### Task 3: Verify and deliver

**Files:**
- Create: `output/manual-news-2026-09-09-mao-50th-v07/video/final-clean.mp4`
- Create: `output/manual-news-2026-09-09-mao-50th-v07/qc/contact-sheet-final.jpg`
- Create: `output/manual-news-2026-09-09-mao-50th-v07/production/final-qc-report.json`

- [ ] Decode the entire MP4 with FFmpeg and require exit code 0.
- [ ] Assert 1080x1920, 25fps, H.264/AAC, 48kHz mono, and zero subtitle/data streams.
- [ ] Run silence, freeze, visual contact-sheet, host identity, and timeline-boundary checks.
- [ ] Deliver only `video/final-clean.mp4`.
