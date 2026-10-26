# BV1UTpU6GEhk Reference Replica Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a verified 1080x1920 clean replica of `BV1UTpU6GEhk` with the reference spoken copy, project-default host and voice, and clean continuously moving inserts that preserve the reference shot order.

**Architecture:** Use the repository Bilibili downloader for a validated reference, recover the transcript and shot map through ASR/OCR/frame analysis, then acquire and approve clean same-source inserts before generation. Generate one locked narration master and matching project-default avatar, assemble with FFmpeg, and retain machine plus director QC evidence beside the direct MP4 handoff.

**Tech Stack:** `avatar_pipeline.bilibili`, FFmpeg/FFprobe, Faster-Whisper, OCR, Giggle TTS, Giggle/Topview avatar video, Python 3, JSON, SHA-256.

## Global Constraints

- Reference BVID is `BV1UTpU6GEhk`; never use browser acquisition until all recorded non-browser fallbacks fail.
- Spoken copy must match the recoverable reference speech without dropped, reordered, or rewritten sentences.
- Host is `host-c2-pro-candidate-2-final`; voice is `未来科技解说` / `cobra_design_20250717_162347_664524`, neutral, normal speed.
- Final output is 1080x1920 at 25 fps, H.264/yuv420p with AAC 48 kHz mono audio.
- No final frame may contain the reference presenter, subtitles, titles, platform marks, account marks, logos, or watermarks.
- Inserts use continuous normal-speed motion only; no freeze, loop, repeated frames, slow motion, enlargement, zoom, or pan-and-scan.
- Landscape inserts are proportionally centered with black space above and below.
- Every visible person and setting must pass the China-context and identity gates defined in `AGENTS.md`.
- Deliver direct files only; do not create a ZIP or other archive.

---

### Task 1: Acquire and validate the reference

**Files:**
- Create: `output/bilibili-replica-BV1UTpU6GEhk-v01/source/reference.mp4`
- Create: `output/bilibili-replica-BV1UTpU6GEhk-v01/source/download-report.json`
- Create: `output/bilibili-replica-BV1UTpU6GEhk-v01/source/ffprobe.json`

**Interfaces:**
- Consumes: the user-supplied watch-later URL.
- Produces: a validated local audio/video reference plus source provenance for analysis.

- [ ] Run `PYTHONPATH=src .venv/bin/python -m avatar_pipeline.bilibili '<URL>' --output-dir 'output/bilibili-replica-BV1UTpU6GEhk-v01/source'` once in a new directory.
- [ ] Verify the report records each attempted method, selected BVID/CID, validated streams, duration, and SHA-256.
- [ ] Run `ffprobe -v error -show_streams -show_format -of json` and a complete `ffmpeg -v error -i reference.mp4 -f null -` decode; stop only on a documented access/rights restriction or exhausted fallback.

### Task 2: Recover exact speech and reference structure

**Files:**
- Create: `output/bilibili-replica-BV1UTpU6GEhk-v01/copy/presenter-only-script.txt`
- Create: `output/bilibili-replica-BV1UTpU6GEhk-v01/copy/full-program-transcript.txt`
- Create: `output/bilibili-replica-BV1UTpU6GEhk-v01/production/reference-transcript.json`
- Create: `output/bilibili-replica-BV1UTpU6GEhk-v01/production/reference-shot-map.json`
- Create: `output/bilibili-replica-BV1UTpU6GEhk-v01/qc/reference-contact-sheets/`

**Interfaces:**
- Consumes: the validated reference from Task 1.
- Produces: locked TTS text plus timecoded presenter/insert boundaries and visual descriptions.

- [ ] Extract reference PCM audio and transcribe it with the strongest locally available Chinese Whisper model, keeping word/segment timestamps.
- [ ] Sample at least every 0.5 seconds around caption and scene changes; use OCR and targeted listening to correct recognition errors and exclude non-spoken overlays.
- [ ] Record every sentence with start/end times, speaker role, visual type, confidence, and evidence; resolve uncertain words before generation.
- [ ] Normalize only punctuation and unambiguous numeral readings, then assert the two text deliverables match the locked spoken content exactly.

### Task 3: Acquire and approve clean inserts

**Files:**
- Create: `output/bilibili-replica-BV1UTpU6GEhk-v01/media/candidates/`
- Create: `output/bilibili-replica-BV1UTpU6GEhk-v01/media/approved/`
- Create: `output/bilibili-replica-BV1UTpU6GEhk-v01/production/footage-ledger.json`
- Create: `output/bilibili-replica-BV1UTpU6GEhk-v01/production/shot-selection.json`

**Interfaces:**
- Consumes: each insert beat and visual fingerprint from Task 2.
- Produces: one or more approved normal-speed source intervals per insert beat.

- [ ] Identify likely original sources through visual details, titles, named people/works, platform search, and frame similarity; prefer the exact clean source.
- [ ] Download multiple public candidates where necessary and record source page, hash, resolution, duration, and acquisition method.
- [ ] Generate dense full-interval contact sheets and reject any candidate containing reference presenter, text, mark, watermark, foreign/unverified person, wrong setting, poor detail, or weak semantic match.
- [ ] Record for each approved interval `china_context_verified=true`, `foreign_person_detected=false`, resolved `people_identity_check`, playback speed `1.0`, scale `<=1.0`, no crop/zoom/freeze/loop, and director approval.

### Task 4: Generate locked narration and project-default avatar

**Files:**
- Create: `output/bilibili-replica-BV1UTpU6GEhk-v01/audio/master-voiceover.wav`
- Create: `output/bilibili-replica-BV1UTpU6GEhk-v01/video/anchor.mp4`
- Create: `output/bilibili-replica-BV1UTpU6GEhk-v01/production/tts-result.json`
- Create: `output/bilibili-replica-BV1UTpU6GEhk-v01/production/avatar-result.json`

**Interfaces:**
- Consumes: exact locked text, fixed voice ID, and host reference whose SHA-256 is `939324593eb718cd2a39be4c171f74178a6a48442f7e0d61afe8a875011e8a47`.
- Produces: the sole final speech master and a fresh lip-synced host track.

- [ ] Verify the host image hash and submit the full locked script to the fixed voice at normal speed and neutral emotion.
- [ ] Download, normalize, and probe the finished audio; compare its ASR/listening result sentence-by-sentence against the locked transcript.
- [ ] Submit the verified audio with the locked host image to the avatar service and poll continuously to completion.
- [ ] Download and review the complete avatar for identity, facial stability, mouth motion, lip sync, full ending, and absence of generated overlays.

### Task 5: Assemble the clean master

**Files:**
- Create: `output/bilibili-replica-BV1UTpU6GEhk-v01/production/timeline.json`
- Create: `output/bilibili-replica-BV1UTpU6GEhk-v01/production/render.sh`
- Create: `output/bilibili-replica-BV1UTpU6GEhk-v01/video/final-clean.mp4`

**Interfaces:**
- Consumes: the final speech master, avatar track, and approved inserts.
- Produces: a continuous reference-ordered clean master ending exactly with the narration.

- [ ] Map the reference presenter/insert order onto TTS sentence timestamps without changing the spoken sequence.
- [ ] Build a contiguous timeline with exact source intervals and 1.0 playback speed; center landscape footage at native-or-downscaled size on black 1080x1920 canvas.
- [ ] Render H.264/yuv420p at 25 fps with the sole narration master as AAC 48 kHz mono; never use source audio or overwrite another run.
- [ ] Verify every transition, first/last frame, sentence boundary, and final audio/video duration before QC.

### Task 6: Run automatic and director QC, then hand off

**Files:**
- Create: `output/bilibili-replica-BV1UTpU6GEhk-v01/qc/ffprobe.json`
- Create: `output/bilibili-replica-BV1UTpU6GEhk-v01/qc/decode-errors.log`
- Create: `output/bilibili-replica-BV1UTpU6GEhk-v01/qc/blackdetect.log`
- Create: `output/bilibili-replica-BV1UTpU6GEhk-v01/qc/freezedetect.log`
- Create: `output/bilibili-replica-BV1UTpU6GEhk-v01/qc/silencedetect.log`
- Create: `output/bilibili-replica-BV1UTpU6GEhk-v01/qc/qc-report.json`
- Create: `output/bilibili-replica-BV1UTpU6GEhk-v01/qc/final-clean.sha256`

**Interfaces:**
- Consumes: `video/final-clean.mp4`, the master audio, transcripts, timeline, and footage ledger.
- Produces: a pass/fail evidence package and direct user-facing files.

- [ ] Run complete decode, stream/specification, duration/frame-count, audio alignment/correlation, black/silence/freeze, and exact duplicate-frame checks.
- [ ] Generate full-program and per-insert dense contact sheets; inspect all frames for text, logos, watermarks, reference presenter, people identity, China context, framing, scale, and motion.
- [ ] Transcribe final audio and compare with the locked transcript; verify no missing phrase and a complete ending.
- [ ] Repair and repeat any failed gate. When all checks pass, write the SHA-256 and `qc-report.json` with `overall_status: passed`, then deliver the MP4 and requested sidecars directly.
