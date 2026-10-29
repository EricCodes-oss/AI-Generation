# Bilibili 野猪与老牛视频新闻 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a 50—56 second 9:16 V5 clean news video about the unverified Bilibili clip `BV1dmtW6vEmt`, with presenter narration and text-free source-video inserts.

**Architecture:** Build an isolated run directory under `output/` containing source evidence, copy, voice audio, presenter segments, cleaned inserts, timeline, render script, and QC evidence. Generate the presenter with the project-fixed host and voice, remove source audio, crop/mask all baked-in text from inserts, then concatenate presenter and inserts into a single silent-text master.

**Tech Stack:** Python 3, Topview Avatar4/TTS or existing project generation wrapper, FFmpeg/ffprobe, JSON manifests, local QC contact sheets.

## Global Constraints

- Output is 1080×1920, 25fps, H.264 video with AAC 48kHz mono audio.
- Full video has no added subtitles, titles, source bars, logo, music, or source audio.
- Insert clips must not contain readable baked-in titles, subtitles, stickers, or comment text.
- Facts are limited to visible content and Bilibili metadata; no location, date, identity, or real-event causality is asserted.
- Final run must include automatic probe/QC and two-pass director review records.

---

### Task 1: Create run inputs and editorial copy

**Files:**
- Create: `output/manual-news-2026-09-02-bilibili-wild-boar-cow-v01/production/run-manifest.json`
- Create: `output/manual-news-2026-09-02-bilibili-wild-boar-cow-v01/copy/voiceover.txt`
- Create: `output/manual-news-2026-09-02-bilibili-wild-boar-cow-v01/copy/full-program-transcript.txt`
- Create: `output/manual-news-2026-09-02-bilibili-wild-boar-cow-v01/copy/source-links.txt`

- [ ] Save the fetched Bilibili metadata and source MP4 into `media/source/`, recording URL, capture time, SHA-256, duration, and visible-content notes.
- [ ] Write a short authoritative script that calls the item a circulating unverified clip, distinguishes the real-looking yard footage from later animation/AI imagery, and ends with a verification reminder.
- [ ] Mark the insert as silent in the full transcript and prohibit any overlay text.

### Task 2: Prepare text-free insert clips

**Files:**
- Create: `media/approved/insert-yard-clean.mp4`
- Create: `media/approved/insert-yard-clean-contact.jpg`
- Create: `production/insert-cleaning.json`

- [ ] Select continuous yard segments only; exclude animated frames where possible.
- [ ] Remove source audio and use crop/masks that eliminate every readable baked-in title/subtitle/comment region.
- [ ] Probe the cleaned clips and inspect contact sheets at 1 fps before compositing.

### Task 3: Generate presenter narration segments

**Files:**
- Create: `audio/presenter-opening.wav`
- Create: `audio/presenter-analysis.wav`
- Create: `audio/presenter-close.wav`
- Create: `media/approved/host-opening.mp4`
- Create: `media/approved/host-analysis.mp4`
- Create: `media/approved/host-close.mp4`

- [ ] Use the fixed project host image and `未来科技解说` voice; render three segments matching the script blocks.
- [ ] Verify each segment duration and that no caption style or generated text is enabled.
- [ ] If remote generation is unavailable, preserve the same timing contract and report the blocking error rather than silently using mismatched legacy host footage.

### Task 4: Render timeline and package

**Files:**
- Create: `production/timeline.json`
- Create: `production/render.sh`
- Create: `video/final-clean.mp4`

- [ ] Concatenate presenter and cleaned insert segments in the approved order, pad only with intentional silence, and encode the V5 master.
- [ ] Ensure no text filter, subtitle stream, source audio, music, or logo enters the final render.
- [ ] Record segment boundaries, source hashes, and render parameters.

### Task 5: Automatic QC and director review

**Files:**
- Create: `qc/final-probe.json`
- Create: `qc/contact-sheet-final.jpg`
- Create: `qc/final-qc-report.json`
- Create: `qc/director-review.json`
- Create: `qc/sha256.txt`

- [ ] Run ffprobe checks for duration, dimensions, frame rate, codecs, audio sample rate/channels, and stream count.
- [ ] Inspect contact sheets for text remnants, presenter identity continuity, insert relevance, and complete ending.
- [ ] Run a second review pass after any repair; only then expose the final MP4 path.
