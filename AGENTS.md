# Project Execution Rules

## News production skill and learning loop

- For presenter-led news production and revisions, load the installed `video-generator` skill and its `references/news-editorial-quality.md` before script review or paid generation, and apply its checks again before delivery. The installed entry is `/Users/liuweidong/.codex/skills/video-generator/SKILL.md`; its news reference is `/Users/liuweidong/.codex/skills/video-generator/references/news-editorial-quality.md`.
- These checks cover reference understanding, same-source footage feasibility, final-canvas previews, pronunciation review, revision-specific QC and evidence limits. They are internal checks, not additional user approval gates.
- For confirmed failures or user corrections, repair and reverify the current artifact, update the smallest relevant skill/runbook rule, and record failure evidence, cause, changed rule and regression result in the run's review record. Preserve the user's authorized scope and continuous execution.

## Bilibili acquisition: browser is the last fallback

- For a Bilibili reference, first use `PYTHONPATH=src .venv/bin/python -m avatar_pipeline.bilibili '<URL-or-BV>' --output-dir '<new-source-directory>'`.
- Reuse only verified matching downloads. A 412 from the video-detail endpoint or yt-dlp does not mean all non-browser methods failed: try the public pagelist endpoint to resolve the selected part's CID, then the public playurl endpoint and available CDN backup URLs.
- Use bounded retries for transient network errors; do not repeatedly hammer an endpoint returning 412. Record attempted methods and outcomes in `download-report.json`.
- Do not start or control a browser for Bilibili acquisition until all applicable non-browser methods have failed and their results are recorded. Explain the remaining blocker and why browser fallback is needed before switching.
- Do not automatically read browser cookies, profiles or login credentials. Do not bypass login, CAPTCHA, paid-content or rights restrictions. Such restrictions are not a reason to try stronger download methods.
- Validate downloaded audio/video streams and duration before reuse or production. Download success does not approve footage for editorial, watermark, framing or rights QC.

## Continuous execution

- Treat an approved task as authorization to run the complete applicable workflow, not just the next stage.
- Do not stop after ordinary progress reports and do not wait for the user to say “继续”. Continue immediately with the next safe step until the requested deliverable is complete and verified.
- Progress messages are informational only; they are not approval gates.
- For the V5 manual-news workflow, the only routine user gate is joint evaluation and selection of the hotspot candidate. After a candidate is selected, continue through fact verification, script review, TTS, avatar generation, footage preparation, editing, transcript generation, automatic QC, director QC and delivery verification without asking for step-by-step confirmation.
- Pause only when user input is genuinely required, including: choosing among hotspot candidates, resolving a material factual conflict, accepting a rights/safety risk, supplying unavailable credentials or source material, or approving an irreversible external action.
- A failed quality gate is not automatically a user question. Diagnose, remediate and retry autonomously when the established rules determine the correction.
- Do not lower quality, substitute weak content, or declare completion merely to avoid a blocker. Report a blocker only after the available remediation paths have been exhausted.

## Delivery handoff rule

- Do not create, update, or offer a ZIP/delivery archive for news-video handoff.
- Deliver the verified `video/final-clean.mp4` directly, with only the requested standalone sidecar files (for example: presenter script, complete programme transcript, source ledger, timeline, QC report, and SHA-256 record).
- A directory may contain internal production artifacts, but the user-facing handoff must list direct file paths and must not include `delivery-package.zip`, `*-delivery.zip`, or equivalent archives.

## Delivery completion

- A task is not complete at an intermediate artifact or status update.
- Continue until all required outputs exist, validation passes, relevant tests pass, and any requested commit or remote synchronization is complete.
- For news videos that retain source audio, deliver both the presenter-only script and the complete programme transcript containing all audible source dialogue.

## News remix editorial language

- For presenter-led news remixes, the presenter must speak directly about the person, behavior, social phenomenon, or real-life situation. Do not introduce the source as a piece of content.
- Never use empty meta-transition language such as “有一个视频”, “这个视频讲了什么”, “我们一起来看”, “接下来请看”, “看完这段视频”, or equivalent phrasing.
- Use the fixed editorial structure: raise the real-life situation or tension directly, let inserted footage and its replacement narration develop the concrete actions or responses, then return to the presenter for a concise summary and thematic elevation.
- Treat inserted footage as the main narrative carrier and presenter segments as framing and commentary. The opening should be brief and the closing should add a clear judgment rather than repeat the inserted narration.
- Match inserted visuals and narration sentence by sentence for meaning and emotional intent. The audience should be able to understand and feel the point from the picture they see and the words they hear at the same moment.
- Keep inserted narration natural, clear, and comfortably paced. Never force excessive speech acceleration to fit a preselected duration; retime, extend, slow, loop, or restructure footage instead.
- Video quality and editorial effect determine the final duration. Do not ask the user to choose a duration when they have already stated that duration is not a hard constraint.

## Inserted-footage regional and people-identity hard gate

- For China-focused news videos, inserted footage must use Chinese people and recognizable Chinese settings whenever people or location are visible. Do not use identifiable foreign people, foreign classroom scenes, or generic overseas stock footage as substitutes.
- Before download approval, search for China-based, Chinese-platform, or clearly China-contextual footage that matches the script. “Looks similar” is not enough.
- If a visible person’s nationality or the scene’s China context cannot be verified, reject that shot; use a non-identifying detail shot (hands, notebooks, classroom objects, signage-free interiors) or keep searching. Do not infer nationality from appearance alone.
- The footage ledger and QC report must record `china_context_verified`, `foreign_person_detected`, and `people_identity_check`. Any `foreign_person_detected=true`, `china_context_verified=false`, or unresolved identity is a hard failure.
- Contact-sheet review must check every visible person, not only the first frame. A video with foreign people is not deliverable even when it has no subtitles, watermark, title, or blur.

## Inserted-footage motion and framing hard gate

- For this reference-remix series, the output canvas is 9:16 portrait. Place landscape inserts proportionally at the center with black space above and below. Do not switch the whole programme to landscape to accommodate film footage.
- For the work-stress/weight episode, include clean, high-quality scenes from 《瘦身男女》 and clothed footage of 文章 in 《胖子行动队》 as specifically requested. Reject bare-torso/nude substitutions. Other matching Chinese movie inserts may enrich the programme.

- Inserted footage must retain continuous real motion at normal playback speed. Do not add freeze frames, still-image padding, repeated static frames, or extreme slow motion to fill narration time.
- Do not add zoom effects or punch-in crops. Uniform proportional scaling so a landscape insert fills the full 1080 canvas width is required, not forbidden; record the scale factor in the ledger.
- Every landscape insert fills the full 1080 width, is vertically centered, and has black space only above and below. Left/right black bars or aspect distortion are a hard failure.
- If a clean source interval is too short, find longer footage of the same action or another verified same-source shot. Do not compensate with frozen frames, repeated loops, or punch-in crops.
- Before delivery, review every inserted shot and record playback speed, scale, source interval, freeze detection, and framing approval in the QC report. Any added zoom or freeze is a hard failure.

## Inserted-footage format uniformity hard gate

- Every insert in one programme uses the same display aspect ratio and the same on-canvas size. Do not mix landscape and portrait inserts in the same video.
- Default insert format is landscape 16:9, proportionally scaled to the full 1080 width and vertically centered on the 1080x1920 canvas with plain black bars above and below only. Do not add a blurred or enlarged background layer unless the user explicitly asks for it.
- Reject portrait (9:16) sources when the programme uses landscape inserts; reject landscape sources when the programme uses portrait inserts. Decide the format before searching, and record it once in the footage ledger as `insert_format`.
- Source resolution of every insert must be at least 1080p. A 720p source is allowed only when no 1080p or better match exists for that beat, and the ledger must then record `below_1080p_justified=true` with the search attempts that were exhausted.
- Prefer 25 fps or 50 fps sources for the 25 fps output. When a 24 fps source is used, record the framerate conversion in the ledger.
- The QC report must assert that every insert has an identical `display_size` and that all sources meet the resolution rule. A mixed-format programme is a hard failure.

## Fixed three-part programme structure

- The default programme structure is three parts: a short presenter opening, one continuous insert body, and a short presenter closing. Do not alternate presenter and insert more than once.
- The presenter opening raises the real-life situation or tension directly and runs roughly 5 to 15 seconds.
- The insert body is one uninterrupted stretch carrying the main narrative, with per-shot narration voiced in the default host voice. It carries the majority of the programme.
- The presenter closing returns to the host for a concise summary and a clear thematic judgement. It must not repeat the insert narration.
- A reference video supplies topic, facts, information order, and shot semantics, not its edit rhythm. When a reference alternates presenter and insert in three rounds, re-consolidate the inserts into one body and keep the presenter only at the head and tail.
- Shot durations follow the reference video's own pacing for the same beat; do not impose a fixed minimum or maximum clip length when the reference provides the rhythm.

## Footage sourcing order

- Order of preference: footage already approved inside this project; a clean same-source master of the reference shot; a China-contextual licensed source; then a free-license stock library.
- Bilibili without a logged-in session caps downloads at 480p. Treat it as unusable for inserts that must meet the 1080p rule unless a verified higher-quality stream is available, and record that finding instead of retrying it.
- Pexels and Pixabay block scripted access from this environment. Mixkit free-stock video is reachable and serves up to 4K; for each candidate try `2160`, then `1440`, then `1080`, then `720` under `https://assets.mixkit.co/videos/<id>/<id>-<res>.mp4`.
- Record every attempted source, its resolution ceiling, and the reason for rejection in the source search log.
- Run frame OCR (every 0.5 s) on each candidate source interval before approval. Reject any interval showing readable text, barcodes, labels, or brand marks, even when the text is small or at the frame edge.
- For generated inserts, inspect garment and prop regions at source resolution throughout each used interval. OCR misses tiny synthetic glyphs; a clean contact sheet at reduced size is insufficient. After local mark removal, inspect the repaired region across motion and rerun OCR and final-canvas QC on the rebuilt MP4.

## Reference-video remix: insert source and presenter role

- Before production, confirm with the user where inserts come from: the reference video itself, same-source film footage, or AI generation. Do not guess; three rebuilds of the 五星红旗 episode came from guessing.
- When the user says the insert should use the reference video, download it with the Bilibili tool and use the reference video itself as the insert body, keeping its original audio. Do not substitute other films, re-cut a different source, generate scenes, or re-voice its content. This explicit instruction overrides the default rules on rewriting reference narration and on the 1080p source minimum; record each such override in the QC report.
- Before analysing any file, verify its BVID, title and duration match the user's reference. Never treat a footage candidate as the reference.
- Remove burned subtitles by measuring the subtitle top row and cropping only that strip plus a 3-row margin. Remove in-picture name cards with time-limited delogo, and trim the reference's trailing black/end cards. Diegetic prop text may stay but must be noted in the ledger.
- The presenter opening raises the question; the closing gives judgement and civic or educational meaning. The presenter must not explain facts, symbolism or process that the insert already tells; that weakens the insert.
- The V5 insert-ratio and duration limits are guidance for a full-reference insert; exceeding them at the user's request is a documented override, not a failure to hide.

## QC tool self-check

- Prove each detector works on a known positive before trusting a negative result. Local tesseract has no chi_sim data; use `swift tmp/vision_ocr.swift <png-dir>` (macOS Vision) for Chinese text. An empty OCR result is not a pass.

## Self-correction

- When the user corrects a production mistake, update the relevant contract in `skills/contracts/`, this file, and the tests in `tests/test_skill_contracts.py` in the same session, so the same mistake cannot recur.

## Reference-script rights and medical claims

- Do not reproduce another publisher's narration word for word. A reference supplies facts, structure, and information order; the spoken copy is rewritten in this project's own words unless the user supplies proof of a licence for the reference.
- Verify every medical, legal, or financial claim in a reference before reusing it. Drop or soften claims that lack an authoritative basis, and record the correction in the script review.
- Keep the reference's demonstrable facts, figures, timings, and quoted professional advice when they check out.

## Inserted-footage content tone gate

- Every insert must picture the sentence it is playing over. A shot that is merely topical, or merely clean, is a rejection.
- Health and medical beats use ordinary, reassuring scenes: the person's own reaction, a calm consultation room, food and drinks. Never use needles, syringes, IV bags, blood, wounds, hospital beds, surgical instruments, or operating-theatre equipment as filler.
- Review every insert on a contact sheet for how it feels, not only for technical defects. Anything that would alarm a general audience is rejected even when it contains no text, watermark or identifiable person.
- When no stock footage matches the sentence and the China-context or tone gates, generate the scene instead of substituting an unrelated shot. Generated scenes are recorded as AI illustrative footage, never presented as the real event or the actual person.

## Verbatim replica: plan timing before paid generation

- When the user asks to reuse a reference narration word for word, estimate the default-voice reading time before submitting TTS. The default `cobra` voice reads about 4 characters per second; reference narrators often read 6 to 7, so the same text can need almost twice the time. Compare the estimate with the usable insert footage and choose the sentence split first.
- If narration still exceeds the footage, apply one uniform `atempo` to the whole insert narration first and record the factor and final characters per second. Moving insert sentences into the presenter opening or closing changes the programme structure even when the words stay the same; ask the user before doing it.
- In a verbatim replica the opening, insert body and closing must be a contiguous prefix, middle and suffix of the reference script. Do not move sentences across parts to match the reference's own shot alternation; verify the full sentence order before submitting TTS or avatar jobs.
- Record the source, scope and confirmation time of any licence to reuse another publisher's narration. Selecting an option in a question dialog is not licence evidence. Disputed facts kept at the user's request go into the QC report as `fact_flags`, never as verified facts.

## Shot labels, static sources and resolution checks

- Before batch rendering, extract the first, middle and last frame of every shot's source interval and confirm the picture matches the shot label. Scene-cut intervals are only candidates: transition blur and photo pans are easily mislabelled.
- Mark photo pans, stills and pasted images as `static_source=true` in the footage ledger. `freezedetect` never fires on a moving pan, so a clean freeze check does not prove continuous real motion. Use such shots only on explicit user instruction and list them as overrides.
- After every avatar download, check the resolution. Reject and resubmit any output narrower than 1080 pixels; never upscale it.
- Compare ASR with the script sentence by sentence using timeline intervals. A whole-programme similarity score can hide a missing sentence (one dropped sentence only moved it from 0.95 to 0.87). Recheck any missing sentence against the actual audio and record whether ASR dropped it or the audio lacks it.
