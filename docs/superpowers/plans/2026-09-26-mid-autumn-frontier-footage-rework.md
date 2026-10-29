# 中秋边疆插播返工 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace weak/low-quality inserted footage with clearer, action-led Chinese frontier-guard footage showing extreme cold, high altitude, wind/snow, and continuous patrol.

**Architecture:** Keep the approved presenter opening/closing and voiceover. Replace only the four inserted visual blocks, rebuild the clean clips from higher-resolution Bilibili sources using natural reframing, then render and verify the same 9:16 master.

**Tech Stack:** yt-dlp, FFmpeg, JSON sidecars, existing V5 news QC artifacts.

## Global Constraints

- Final output remains `1080x1920`, `25fps`, H.264 video, AAC 48kHz mono.
- No project-added subtitles, titles, logos, platform marks, or music.
- Inserted footage must show Chinese people/settings or clearly verified China context.
- No foreign people, unresolved identities, reverse playback, looping, or repeated shots.
- User authorized source-mark removal; use crop/reframe, never broad blur masking.
- Final duration remains 45–90 seconds and ends on the presenter.

### Task 1: Source replacement and contact-sheet gate

**Files:**
- Create: `output/manual-news-2026-09-24-mid-autumn-frontier-v01/media/candidates/*`
- Create: `output/manual-news-2026-09-24-mid-autumn-frontier-v01/qc/source-contact-*.jpg`

- [ ] Download higher-resolution candidates: BV1gk4y1C7Tb, BV175411v7uY, BV1tR4y147DL, BV1eMYu6eEUi.
- [ ] Build 0.5fps contact sheets and inspect every visible person and edge for watermarks/text.
- [ ] Select continuous action: high-altitude patrol, snow/low-temperature patrol, wind-snow march, and a summer/green-border patrol only if soldiers remain visible.

### Task 2: Clean insert clips

**Files:**
- Create/modify: `output/manual-news-2026-09-24-mid-autumn-frontier-v01/media/approved/*.mp4`
- Modify: `production/footage-ledger.json`, `production/shot-selection.json`

- [ ] Reframe each approved source to 1080x1920 with `setsar=1`, preserving people and action.
- [ ] Use only natural crop boundaries to remove source marks; reject any shot where removal harms the action.
- [ ] Record source URL, hash, season, `china_context_verified`, `foreign_person_detected`, and `people_identity_check`.

### Task 3: Render and verification

**Files:**
- Modify: `production/render.sh`, `production/timeline.json`, `qc/final-qc-report.json`, `qc/director-review.json`, `qc/sha256.txt`
- Verify: `video/final-clean.mp4`

- [ ] Render with the existing presenter videos and master voiceover.
- [ ] Run FFprobe, full decode, silence scan, and dense contact sheets.
- [ ] Confirm action-led footage, no visible source marks, China-context gate, final presenter close, and 45–90 second duration.
