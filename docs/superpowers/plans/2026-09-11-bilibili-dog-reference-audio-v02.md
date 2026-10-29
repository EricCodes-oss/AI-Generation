# Bilibili Dog Reference-Audio Replica v02 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rebuild BV1JegH6dE92 with the exact reference insert montage and source audio, remove visual overlays, and replace the presenter copy with concise news analysis.

**Architecture:** Extract the reference video into a cleaned insert master, retaining its original audio and sequence. Generate one presenter-only voice track for an analytical opening and closing, drive the fixed host asset, then concatenate host opening + cleaned reference insert + host closing while mixing only the host voice in presenter sections and reference audio in the insert section.

**Tech Stack:** FFmpeg, ffprobe, Whisper CLI, Topview Avatar4, Giggle TTS, Python JSON/QC scripts.

## Global Constraints

- Insert visuals must come from `tmp/BV1JegH6dE92-reference.mp4`; no AI-generated replacement footage.
- Insert audio must come from the reference video and remain audible.
- Remove subtitles, titles, logos, watermarks, stickers, and UI overlays from inserted visuals.
- Presenter opening and closing must analyze the real-life behavior/news angle, not recap the reference clip.
- Final canvas is 1080×1920 at 25 fps; insert image is single, centered, with pure black bars above and below.

### Task 1: Rewrite analytical presenter copy

**Files:**
- Create: `output/bilibili-replica-BV1JegH6dE92-v02/copy/presenter-only-script.txt`
- Create: `output/bilibili-replica-BV1JegH6dE92-v02/copy/full-program-transcript.txt`

- [ ] Write opening and closing that frame the dog encounter as behavior feedback, conflict escalation, and a public-safety issue; avoid “有一个视频/我们来看”等元叙述。
- [ ] Include a full-program transcript marking the reference insert as source audio retained.
- [ ] Verify no sentence is a plain scene-by-scene recap.

### Task 2: Build cleaned reference insert

**Files:**
- Create: `tmp/BV1JegH6dE92-reference-clean.py`
- Create: `output/bilibili-replica-BV1JegH6dE92-v02/media/approved/reference-insert-clean.mp4`

- [ ] Use the reference video as the only visual source.
- [ ] Crop/reframe the 480×852 source to exclude the top Bilibili mark and lower subtitle band; preserve the central dog action and original clip order.
- [ ] Keep the reference audio stream unchanged and verify it is present.
- [ ] Render a contact sheet for manual overlay review.

### Task 3: Generate presenter voice and host video

**Files:**
- Create: `output/bilibili-replica-BV1JegH6dE92-v02/audio/master-presenter.wav`
- Create: `output/bilibili-replica-BV1JegH6dE92-v02/video/avatar-presenter.mp4`

- [ ] Submit the rewritten presenter copy to the fixed voice `cobra_design_20250717_162347_664524`.
- [ ] Drive `host-c2-pro-candidate-2-final` with the resulting presenter audio.
- [ ] Verify host video duration matches presenter audio.

### Task 4: Compose and QC

**Files:**
- Create: `output/bilibili-replica-BV1JegH6dE92-v02/production/render.sh`
- Create: `output/bilibili-replica-BV1JegH6dE92-v02/video/final-clean.mp4`
- Create: `output/bilibili-replica-BV1JegH6dE92-v02/qc/*`

- [ ] Concatenate presenter opening, full cleaned reference insert, and presenter closing.
- [ ] Mix presenter audio only in host sections and reference source audio only in insert section.
- [ ] Verify 1080×1920/25fps, single video + single audio stream, complete decode, audio continuity, overlay absence, and transcript coverage.
- [ ] Write `production/delivery-manifest.json` with `ready_to_deliver` only after every check passes.
