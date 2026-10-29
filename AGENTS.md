# Project Execution Rules

## Continuous execution

- Treat an approved task as authorization to run the complete applicable workflow, not just the next stage.
- Do not stop after ordinary progress reports and do not wait for the user to say “继续”. Continue immediately with the next safe step until the requested deliverable is complete and verified.
- Progress messages are informational only; they are not approval gates.
- For the V5 manual-news workflow, the only routine user gate is joint evaluation and selection of the hotspot candidate. After a candidate is selected, continue through fact verification, script review, TTS, avatar generation, footage preparation, editing, transcript generation, automatic QC, director QC and delivery packaging without asking for step-by-step confirmation.
- Pause only when user input is genuinely required, including: choosing among hotspot candidates, resolving a material factual conflict, accepting a rights/safety risk, supplying unavailable credentials or source material, or approving an irreversible external action.
- A failed quality gate is not automatically a user question. Diagnose, remediate and retry autonomously when the established rules determine the correction.
- Do not lower quality, substitute weak content, or declare completion merely to avoid a blocker. Report a blocker only after the available remediation paths have been exhausted.

## Delivery completion

- A task is not complete at an intermediate artifact or status update.
- Continue until all required outputs exist, validation passes, relevant tests pass, and any requested commit or remote synchronization is complete.
- For news videos that retain source audio, deliver both the presenter-only script and the complete programme transcript containing all audible source dialogue.

## Verbatim replica: plan timing before paid generation

- When the user asks to reuse a reference narration word for word, estimate the default-voice reading time before submitting TTS. The default `cobra` voice reads about 4 characters per second; reference narrators often read 6 to 7, so the same text can need almost twice the time. Compare the estimate with the usable insert footage and choose the sentence split first.
- If narration still exceeds the footage, apply one uniform `atempo` to the whole insert narration first and record the factor and final characters per second. Moving insert sentences into the presenter opening or closing changes the programme structure even when the words stay the same; ask the user before doing it.
- Record the source, scope and confirmation time of any licence to reuse another publisher's narration. Selecting an option in a question dialog is not licence evidence. Disputed facts kept at the user's request go into the QC report as `fact_flags`, never as verified facts.

## Shot labels, static sources and resolution checks

- Before batch rendering, extract the first, middle and last frame of every shot's source interval and confirm the picture matches the shot label. Scene-cut intervals are only candidates: transition blur and photo pans are easily mislabelled.
- Mark photo pans, stills and pasted images as `static_source=true` in the footage ledger. `freezedetect` never fires on a moving pan, so a clean freeze check does not prove continuous real motion. Use such shots only on explicit user instruction and list them as overrides.
- After every avatar download, check the resolution. Reject and resubmit any output narrower than 1080 pixels; never upscale it.
- Compare ASR with the script sentence by sentence using timeline intervals. A whole-programme similarity score can hide a missing sentence (one dropped sentence only moved it from 0.95 to 0.87). Recheck any missing sentence against the actual audio and record whether ASR dropped it or the audio lacks it.
