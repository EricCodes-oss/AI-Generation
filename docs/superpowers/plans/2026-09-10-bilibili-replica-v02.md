# Bilibili Reference Replica V02 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a separately packaged V02 replica of `BV14ZbA6wE6K` with the complete reference copy, the locked project host and voice, and high-quality sentence-matched inserts containing no foreign people, text, logos, or watermarks.

**Architecture:** Build a source ledger before editing, search and audit several web candidates per semantic beat, then use AI generation only for beats that cannot pass the footage gates. Generate a new full-copy voice track and talking head, derive the insert timing from the voice track, assemble a clean 720×1280 programme with muted inserts, and package machine and director QC evidence beside the final MP4.

**Tech Stack:** Bilibili and public-web search, `yt-dlp`, `ffmpeg`, `ffprobe`, Python 3, Pillow, EasyOCR or Tesseract when available, Whisper.cpp, Giggle TTS, Topview Avatar4.

## Global Constraints

- Keep `output/bilibili-replica-BV14ZbA6wE6K-v01/` unchanged.
- Host image is `tmp/host-v12-c2-pro/candidate2.png`; host ID is `host-c2-pro-candidate-2-final`.
- Voice is `未来科技解说`, ID `cobra_design_20250717_162347_664524`, emotion `neutral`, target speed `1.1`.
- The spoken copy is exactly the transcript locked in `docs/superpowers/specs/2026-09-10-bilibili-replica-v02-design.md`.
- No inserted frame may contain subtitles, titles, labels, logos, channel marks, or watermarks.
- No inserted frame may contain a foreign person; use recognizably Chinese people or non-human detail shots only.
- Insert source audio is never used.
- Prefer 1080p or higher sources and reject candidates that require aggressive enlargement or narrow cropping.
- AI-generated insert footage is allowed only after the ledger records that suitable web candidates failed the gates.
- The final programme contains no added subtitles, title cards, lower thirds, stickers, logos, or watermarks.

---

### Task 1: Establish the V02 production package and locked transcript

**Files:**
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/copy/presenter-only-script.txt`
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/copy/full-program-transcript.txt`
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/production/run-manifest.json`
- Create: `tmp/bilibili-replica-v02-2026-09-10/package_v02.py`

**Interfaces:**
- Consumes: the exact transcript from the V02 design specification.
- Produces: UTF-8 transcript files and a manifest consumed by TTS, editing, and QC.

- [ ] **Step 1: Create the V02 directory tree without touching V01**

Run:

```bash
mkdir -p output/bilibili-replica-BV14ZbA6wE6K-v02/{audio,copy,media/{candidates,approved},production,qc,video} tmp/bilibili-replica-v02-2026-09-10
```

Expected: every listed directory exists and `git status --short output/bilibili-replica-BV14ZbA6wE6K-v01` is unchanged.

- [ ] **Step 2: Write the exact transcript and manifest generator**

Create `tmp/bilibili-replica-v02-2026-09-10/package_v02.py` with one `LOCKED_SCRIPT` constant containing the specification text verbatim, and write both transcript files from that constant. The manifest must record the reference BVID, fixed host and voice IDs, `script_policy: exact_reference_transcript`, and `insert_source_audio_used: false`.

- [ ] **Step 3: Verify the V01-missing tail is present**

Run:

```bash
rg -F '真正的诊断需要由专业医生，通过标准化智力测验和适应性行为评估等科学手段来完成。' output/bilibili-replica-BV14ZbA6wE6K-v02/copy/*.txt
rg -F '转发提醒身边人，自查别对号入座，有困扰找医生。' output/bilibili-replica-BV14ZbA6wE6K-v02/copy/*.txt
```

Expected: both sentences appear in both transcript files.

### Task 2: Search, download, and audit sentence-matched web footage

**Files:**
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/production/search-queries.json`
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/production/footage-ledger.json`
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/media/candidates/<beat>-<candidate>.mp4`
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/qc/candidate-contact-sheets/<beat>-<candidate>.jpg`
- Create: `tmp/bilibili-replica-v02-2026-09-10/audit_candidates.py`

**Interfaces:**
- Consumes: the six required visual beats from the design specification.
- Produces: a ledger entry per downloaded candidate with `source_url`, `source_title`, `beat`, `resolution`, `duration_seconds`, `people_policy`, `text_logo_policy`, `semantic_match`, `decision`, and `rejection_reason`.

- [ ] **Step 1: Record Chinese and English search phrases for each beat**

Use concrete queries such as `中国学生 写作业 分心 无字幕`, `中国医生 智力测试 认知评估 无水印`, and equivalent stock-footage phrases. Store every executed query and result URL in `search-queries.json`.

- [ ] **Step 2: Download multiple viable candidates per beat**

Use the highest practical progressive MP4 or merged H.264 source and record the actual source page URL. Do not download or reuse the clean-band crop from the reference video.

- [ ] **Step 3: Generate dense contact sheets and technical probes**

For each candidate, run `ffprobe` and sample at least one frame per second across the proposed usable interval. The contact sheet must expose top, bottom, and side regions clearly enough to detect small text and platform marks.

- [ ] **Step 4: Apply the five acceptance gates**

Reject a candidate if any sampled frame contains text, a logo, a watermark, an ambiguous or foreign-looking person, poor focus/compression, or a weak semantic match. Record the exact frame time and reason for every rejection.

- [ ] **Step 5: Fill only unresolved beats with generated footage**

If a beat has no accepted web candidate, generate one 9:16 or crop-safe 16:9 clip depicting recognizably Chinese people, with the prompt ending: `画面中不要出现任何文字、字幕、标题、标牌、LOGO或水印，不要出现外国人，不要生成对白或口型特写。` Record `source_type: generated` and the failed web candidates that justified the fallback.

### Task 3: Build clean approved insert masters

**Files:**
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/media/approved/01-attention.mp4`
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/media/approved/02-comprehension.mp4`
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/media/approved/03-memory.mp4`
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/media/approved/04-language.mp4`
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/media/approved/05-social.mp4`
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/media/approved/06-doctor-assessment.mp4`
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/qc/approved-inserts-contact.jpg`

**Interfaces:**
- Consumes: ledger-approved source intervals only.
- Produces: silent 720×1280, 25fps, H.264 insert masters for timeline assembly.

- [ ] **Step 1: Trim only forward-playing clean intervals**

No reverse, ping-pong, freeze, or duplicate-frame padding is permitted. Extend a short beat by selecting a longer source interval or another approved angle.

- [ ] **Step 2: Convert to portrait with restrained reframing**

Use `scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280` only when the subject and frame edges remain intact. Otherwise use a full-height fit over a clean blurred copy of the same footage; do not magnify low-resolution pixels.

- [ ] **Step 3: Remove all source audio and normalize output**

Encode each master with `-an -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -r 25`.

- [ ] **Step 4: Perform a second-frame review on all approved masters**

Generate one combined contact sheet sampling every second, then record a director approval entry for each beat in the footage ledger.

### Task 4: Generate the complete voice track and new talking head

**Files:**
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/audio/master-voiceover.wav`
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/video/avatar-full.mp4`
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/production/tts-result.json`
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/production/avatar-result.json`

**Interfaces:**
- Consumes: `copy/presenter-only-script.txt`, voice ID `cobra_design_20250717_162347_664524`, emotion `neutral`, speed `1.1`, and host image `tmp/host-v12-c2-pro/candidate2.png`.
- Produces: a 48kHz mono PCM programme master and a full-length lip-synced presenter video.

- [ ] **Step 1: Submit a new full-script TTS task**

Use the selected voice and emotion; do not reuse task `0985a9d4-f805-445a-a836-68d3c3e882a5`. Poll until a completed signed audio URL is returned, download it, transcode to 48kHz mono PCM, and save task metadata.

- [ ] **Step 2: Verify the synthesized copy before avatar generation**

Transcribe the WAV with `tmp/models/ggml-small.bin`, compare normalized Chinese characters to the locked script, and require both previously missing tail sentences to appear. Regenerate if a sentence is absent or truncated.

- [ ] **Step 3: Submit a new audio-driven Avatar4 task**

Use the fixed host and board `6a8396054d1840c5bc7e6eb7129271d0`; do not reuse avatar task `53e8b791800e413592a3ac9441ab0bbd`. Poll to completion, download the full video, and store the new task ID and result URL.

- [ ] **Step 4: Audit presenter identity and tail lip sync**

Create an avatar contact sheet including the final five seconds and verify the closing sentence is visible and audible without truncation.

### Task 5: Derive the sentence timeline and render V02

**Files:**
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/production/timeline.json`
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/production/render-plan.json`
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/production/render.sh`
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/video/final-clean.mp4`
- Create: `tmp/bilibili-replica-v02-2026-09-10/build_v02.py`

**Interfaces:**
- Consumes: voice word timestamps, `video/avatar-full.mp4`, and the six approved insert masters.
- Produces: a sentence-aligned presenter/insert timeline and final H.264/AAC programme.

- [ ] **Step 1: Map every sentence to audio timestamps**

The timeline must begin and end inserts on semantic boundaries, include all six insert beats, and put the professional-diagnosis and closing reminder over either the doctor assessment or the returning presenter as specified in the design.

- [ ] **Step 2: Generate the render plan**

The plan must declare `source_audio_used: false`, `text_overlay_used: false`, `subtitles_used: false`, `title_used: false`, `watermark_used: false`, and the exact source interval for every insert.

- [ ] **Step 3: Render the programme**

Build a 720×1280, 25fps H.264 video, map only `audio/master-voiceover.wav`, encode AAC at 48kHz mono, and use `-movflags +faststart`. The final duration must match the voice master within 80ms.

- [ ] **Step 4: Decode the complete MP4**

Run:

```bash
ffmpeg -v error -i output/bilibili-replica-BV14ZbA6wE6K-v02/video/final-clean.mp4 -f null -
```

Expected: exit code 0 and no stderr output.

### Task 6: Run transcript, visual, and technical QC and package delivery

**Files:**
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/qc/final-probe.json`
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/qc/final-transcript.txt`
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/qc/transcript-diff.json`
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/qc/final-contact-sheet.jpg`
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/qc/insert-full-contact-sheet.jpg`
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/qc/ocr-review.json`
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/qc/casting-review.json`
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/qc/blackdetect.log`
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/qc/freezedetect.log`
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/qc/silencedetect.log`
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/qc/director-review.json`
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/qc/sha256.txt`
- Create: `output/bilibili-replica-BV14ZbA6wE6K-v02/production/delivery-manifest.json`
- Create: `tmp/bilibili-replica-v02-2026-09-10/final_qc.py`

**Interfaces:**
- Consumes: the rendered MP4, locked transcript, timeline, footage ledger, and approved masters.
- Produces: a delivery status that is `ready_to_deliver` only if every required check passes.

- [ ] **Step 1: Run technical validation**

Require 720×1280, 25fps, H.264 video, AAC 48kHz mono audio, zero subtitle/data streams, a full decode with no errors, and duration drift below 80ms.

- [ ] **Step 2: Run audio validation**

Transcribe final audio using the local Whisper model, normalize punctuation for comparison, explicitly test both V01-missing tail sentences, and compare the decoded AAC track with the PCM master for correlation and drift.

- [ ] **Step 3: Run visual validation**

Generate a programme contact sheet and a denser insert-only sheet. Run OCR-assisted scanning on all insert samples and manually review every frame for text, logos, watermarks, foreign or ambiguous people, semantic mismatch, aggressive cropping, and visible generation defects.

- [ ] **Step 4: Run anomaly filters**

Run `blackdetect`, `freezedetect`, and `silencedetect`; explain any expected silence or stillness in the report and reject unexplained anomalies.

- [ ] **Step 5: Complete director review and delivery manifest**

The review must contain separate passed checks for exact script, complete ending, Chinese-only casting, no visible text/title/watermark/logo, no insert audio, sentence matching, visual clarity, host identity, and clean technical playback. Write the SHA-256 checksum and set `status: ready_to_deliver` only when all checks pass.

- [ ] **Step 6: Verify the package one final time**

Run:

```bash
python3 tmp/bilibili-replica-v02-2026-09-10/final_qc.py
test "$(jq -r .status output/bilibili-replica-BV14ZbA6wE6K-v02/production/delivery-manifest.json)" = ready_to_deliver
```

Expected: the QC script exits 0 and the manifest status is exactly `ready_to_deliver`.
