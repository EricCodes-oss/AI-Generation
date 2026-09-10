# Bilibili Reference Replica V02 Design

## Objective

Rebuild the 45-second vertical reference video `BV14ZbA6wE6K` with the project host and the fixed project voice while preserving the reference spoken copy in full. V02 replaces the rejected insert treatment with high-quality, sentence-matched footage and is delivered separately from V01.

## Locked Content

The programme transcript is exactly:

> 轻微智障有5个表现，你中了几个？医生提醒：对照自查，但别对号入座！近日，一则关于“轻微智障5个表现”的科普引发热议。医生指出，轻度智力障碍在注意力、感知、记忆、语言和交往能力五个方面有明显信号。一、注意力容易分散，只能专注某一件事，很难同时注意到两件事；二、感知速度减慢，很难听懂复杂讲话，但别人提示后能立刻明白；三、记忆力变差，刚学会的知识很快就忘记；四、语言能力弱，只能记住简单词句，表达时常词穷；五、交往能力差，难以进行人际交往，不知如何自处。不过以上表现仅供参考，不能作为自我诊断的依据。真正的诊断需要由专业医生，通过标准化智力测验和适应性行为评估等科学手段来完成。转发提醒身边人，自查别对号入座，有困扰找医生。

No sentence may be dropped, paraphrased, reordered, or replaced. In particular, the final two sentences omitted from V01 must be present in the audio and final transcript.

## Presenter and Voice

- Host image: `tmp/host-v12-c2-pro/candidate2.png`
- Host identity: `host-c2-pro-candidate-2-final`
- Voice: `未来科技解说`
- Voice ID: `cobra_design_20250717_162347_664524`
- Emotion: `neutral`
- Target speed: `1.1`, unless a minor adjustment is required to avoid unnatural pacing
- Avatar board: `6a8396054d1840c5bc7e6eb7129271d0`
- V01 TTS and avatar tasks are invalid because their source copy is incomplete and must not be reused.

## Editorial Structure

1. Open briefly on the project host for the hook and framing.
2. Use sentence-matched inserts for the five described signals.
3. Show a Chinese medical consultation or standardized cognitive assessment for the diagnostic explanation.
4. Return to the project host for the disclaimer and closing reminder.

The insert sequence is the main explanatory carrier. Each spoken sentence must have a visual whose literal action or emotional intent matches that sentence.

## Insert Shot Design

| Beat | Spoken idea | Required visual |
| --- | --- | --- |
| 1 | Attention is easily distracted | Chinese adult or student distracted while studying or working |
| 2 | Slow comprehension, then clarity after prompting | Chinese person struggling with a complex explanation, then understanding after clarification |
| 3 | Recently learned information is forgotten | Chinese student or worker checking notes after forgetting recent material |
| 4 | Limited language and difficulty finding words | Chinese person pausing and struggling to express themselves in conversation |
| 5 | Difficulty with social interaction | Chinese person isolated or uncomfortable in a Chinese group setting |
| 6 | Professional diagnosis | Chinese doctor conducting a cognitive assessment or consultation |

## Footage Acquisition and Acceptance

Search the public web first and download multiple candidates for every beat. AI generation is allowed only where web candidates do not pass the acceptance gates.

Every accepted insert must satisfy all of these requirements:

- No subtitles, captions, title cards, labels, logos, channel marks, or watermarks anywhere in the visible frame.
- No foreign people. Human subjects must be recognizably Chinese; otherwise use hands, notebooks, medical instruments, or other non-human detail shots.
- No audible source audio in the final programme.
- At least 1080p at source where available, with no aggressive enlargement or narrow crop.
- Direct semantic match with the simultaneous spoken sentence.
- Natural motion, usable focus, and no black frames, freeze artifacts, or distracting scene cuts.

Source URLs, licenses or usage notes, technical metadata, acceptance decisions, and rejection reasons are recorded in a footage ledger.

## Composition

- Canvas: 720×1280, vertical 9:16, matching the reference delivery format.
- Programme audio: one newly generated full-copy voice track.
- Presenter shots: newly generated from the full audio or full script; V01 presenter video is not reused.
- Inserts: full-frame where composition permits; otherwise use a restrained center crop from clean 1080p or higher material.
- Text policy: no subtitles, titles, lower thirds, stickers, or watermarks are added anywhere in the programme.
- Insert source tracks are muted; the programme voice is the only speech track.
- Duration follows the natural pace of the complete copy and may exceed the reference slightly rather than accelerating speech unnaturally.

## Deliverables

Create `output/bilibili-replica-BV14ZbA6wE6K-v02/` containing:

- `video/final-clean.mp4`
- `audio/master-voiceover.wav`
- `copy/presenter-only-script.txt`
- `copy/full-program-transcript.txt`
- `production/footage-ledger.json`
- `production/timeline.json`
- `production/delivery-manifest.json`
- QC evidence, including transcript comparison, contact sheets, OCR/text review, casting review, technical probe, and black/freeze/silence logs

## Validation

- Transcribe the final programme audio and compare it against the locked transcript, with explicit confirmation that both missing V01 tail sentences are audible.
- Review contact sheets covering every accepted insert, not only selected frames.
- Run OCR-assisted and human visual checks for subtitles, title text, logos, and watermarks.
- Review every human face for the Chinese-only casting requirement; ambiguous candidates are rejected.
- Run `ffprobe`, `blackdetect`, `freezedetect`, and `silencedetect` checks.
- Perform a final director review for visual relevance, pacing, clean frame edges, and audio/video continuity.

## Non-goals

- V01 is not modified or overwritten.
- Reference video pixels are not reused as insert footage.
- The copy is not medically expanded, fact-edited, or stylistically rewritten.
- No subtitles, titles, or watermarks are introduced for accessibility or branding.
