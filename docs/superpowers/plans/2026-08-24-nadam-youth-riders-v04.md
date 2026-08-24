# 那达慕少年骑手 V04 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 制作一版人物与口播一致、少年画面占比不低于80%、能够激发观众驰骋草原冲动的 V04 竖屏新闻短片。

**Architecture:** V04 使用独立运行目录，继承 V03 锁定的短发 C2 主持人和“未来科技解说”音色，但重新生成口播、TTS、数字人、素材账本、时间线、成片与 QC。素材搜索采用多平台候选池，最终只按少年身份、传承关系、动作冲击、草原意境和画面清洁度入选。

**Tech Stack:** Python 3.11+、avatar_pipeline V5 CLI、Giggle TTS、Topview avatar4、yt-dlp/平台允许的下载方式、FFmpeg/ffprobe、Pillow、JSON、pytest。

## Global Constraints

- V04 独立目录：`output/manual-news-2026-08-24-父亲把儿子托上烈马-v04`，不得覆盖或删除 V03。
- 主持人固定为 `host-c2-pro-candidate-2-final`，参考图 SHA-256 固定为 `939324593eb718cd2a39be4c171f74178a6a48442f7e0d61afe8a875011e8a47`。
- 音色固定为“未来科技解说”，voice ID 为 `cobra_design_20250717_162347_664524`，速度为 `1.1`。
- 可辨识人物镜头中，少年画面时长占比不得低于 80%；成年人物只承担父亲托举、长辈示范或传承衔接，总时长不得超过 20%。
- 至少入选五类必备画面和三类力量特写。
- 插播目标时长 40—45 秒；单个高价值动作可持续 5—7 秒。
- 禁止烧录解说字幕、新闻标题、评论框、大面积文字遮挡、倒放、循环、乒乓和重复补时。
- 插播中不加入主持人解说；交付静音插播版，供用户后期加入热血 BGM。
- 成片为 1080×1920、25fps、H.264；音频为 AAC、48kHz、单声道。
- 结尾必须回到主持人，末句完整且保留自然停顿。
- 必须交付主持人口播稿和完整节目转写。

---

### Task 1: 建立 V04 独立运行目录与选题记录

**Files:**
- Create: `output/manual-news-2026-08-24-父亲把儿子托上烈马-v04/production/topic-selection.json`
- Create: `output/manual-news-2026-08-24-父亲把儿子托上烈马-v04/production/run-manifest.json`
- Copy: `output/manual-news-2026-08-24-父亲把儿子托上烈马-v03/production/quality-profile.yaml`
- Copy: `output/host-v12-c2-pro/GPT-Image-2-Pro-C2-Pro-主持人最终选定.png`

**Interfaces:**
- Consumes: V03 run ID 和锁定质量配置。
- Produces: 后续所有任务使用的 `$RUN` 目录及合法 V5 manifest。

- [ ] **Step 1: 写入 V04 选题确认记录**

创建 `production/topic-selection.json`，内容明确记录用户于 2026-08-24 确认“少年为主、父辈托举、热血草原”的 V04 方案、无字幕要求和允许小型来源水印的既有边界。

- [ ] **Step 2: 初始化 V04**

```bash
export RUN="output/manual-news-2026-08-24-父亲把儿子托上烈马-v04"
PYTHONPATH=src .venv/bin/python -m avatar_pipeline.cli news-v5-init \
  --output-root output \
  --date 2026-08-24 \
  --slug 父亲把儿子托上烈马 \
  --topic "内蒙古那达慕少年骑手、父辈托举与草原传承" \
  --version 4 \
  --parent-run-id manual-news-2026-08-24-父亲把儿子托上烈马-v03 \
  --topic-selection "$PWD/tmp/v04-topic-selection.json"
```

Expected: 创建 `$RUN`，manifest `status=initialized`，`parent_run_id` 指向 V03。

- [ ] **Step 3: 创建工作目录**

```bash
mkdir -p "$RUN"/{research,copy,audio/parts,video,media/candidates,media/approved,production,qc/frames,qc/segment-contact}
cp output/host-v12-c2-pro/GPT-Image-2-Pro-C2-Pro-主持人最终选定.png "$RUN/production/host-reference.png"
```

- [ ] **Step 4: 验证主持人哈希和目录隔离**

```bash
shasum -a 256 "$RUN/production/host-reference.png"
test ! "$RUN" -ef output/manual-news-2026-08-24-父亲把儿子托上烈马-v03
```

Expected: 哈希为 `939324593eb718cd2a39be4c171f74178a6a48442f7e0d61afe8a875011e8a47`。

### Task 2: 锁定 V04 口播与证据边界

**Files:**
- Create: `$RUN/copy/title.txt`
- Create: `$RUN/copy/voiceover.txt`
- Create: `$RUN/production/fact-evidence.json`
- Create: `$RUN/production/script-review.json`
- Create: `$RUN/production/script-director-notes.json`

**Interfaces:**
- Consumes: 已批准设计中的“托举—接缰—驰骋—传承—远方”叙事。
- Produces: TTS 输入文本、标题和可核验的脚本边界。

- [ ] **Step 1: 写入口播稿**

```text
马蹄踏响草原，父亲把孩子托上马背，也把勇气交到了他的手里。人虽年少，握住缰绳的那一刻，眼里已经有了草原的辽阔。

从第一次上马，到独自策马、弯弓、迎风向前。练的是本领，磨的是胆气。高大骏马踏风而来，少年稳坐马背。让人想起“左牵黄，右擎苍，千骑卷平冈”的豪情。一代人托起下一代。马蹄所向，是辽阔草原，也是少年奔向远方的路。
```

- [ ] **Step 2: 写入暂定标题**

```text
马蹄踏响草原：少年骑手为何让人热血沸腾？
```

若最终没有清晰父子托举画面，保留该标题并删除口播中的“父亲”确定关系；若形成清晰父子传承线，标题改为“父亲把儿子托上烈马，也把草原的勇气交给了下一代”。

- [ ] **Step 3: 写入事实与禁用表述**

`fact-evidence.json` 必须把“人物确为少年”“父亲关系”“动作类型”标为逐素材核验项，并把未核实人物关系、赛事名次、民族身份、具体年龄列入 `prohibited_claims`。

- [ ] **Step 4: 完成导演脚本评审**

`script-review.json` 必须将 authoritative tone、sentence clarity、ending complete、facts traceable 和 director approved 设为 true；若“父亲”关系尚未由最终素材支持，`facts_traceable` 保持 false，直到 Task 4 完成关系核验后再批准。

### Task 3: 建立多平台少年素材候选池

**Files:**
- Create: `$RUN/research/search-log.json`
- Create: `$RUN/research/candidate-pool.json`
- Create: `$RUN/research/candidate-pool.md`
- Create: `$RUN/copy/source-links.txt`
- Create: `$RUN/media/candidates/*.mp4`

**Interfaces:**
- Consumes: Task 2 的动作和人物需求。
- Produces: 至少 20 个真实候选和可访问的本地视频文件。

- [ ] **Step 1: 搜索 B站、视频号、抖音、小红书和头条**

依次使用以下查询词，并记录实际访问 URL、标题、账号、发布时间、播放/点赞/评论等可见热度：

```text
父亲 托 儿子 上马
内蒙古 少年 骑马
那达慕 儿童 赛马
小孩 骑马 汽车 比赛
少年 骑射
儿童 骑射 草原
少年 马上 拾哈达
儿童 搏克
少年 并排 骑马 草原
马蹄 低机位 草原
万马奔腾 航拍
```

不得凭记忆构造 URL。视频号不可直接下载时，记录候选和页面证据；最终入选必须能够合法获取本地视频。

- [ ] **Step 2: 候选池达到最低覆盖**

`candidate-pool.json` 至少包含：

- 父辈托举候选 3 条；
- 少年策马候选 5 条；
- 少年竞速或高难动作候选 3 条；
- 少年骑射/拾哈达候选 3 条；
- 儿童搏克候选 3 条；
- 马蹄/航拍/万马候选 3 条。

- [ ] **Step 3: 下载可用候选**

对可公开获取的候选使用项目允许的下载方式。B站候选优先执行：

```bash
HTTPS_PROXY=http://127.0.0.1:8118 HTTP_PROXY=http://127.0.0.1:8118 \
  yt-dlp --no-playlist -f 'bv*+ba/b' --merge-output-format mp4 \
  -o "$RUN/media/candidates/%(id)s.%(ext)s" '实际访问得到的URL'
```

若代理失败，去掉代理重试；不得绕过付费、访问控制或版权保护。

- [ ] **Step 4: 验证来源真实性**

每个下载文件必须在 `search-log.json` 中对应一个真实来源 URL，并记录下载时间、平台和 SHA-256。没有来源映射的文件不得进入 Task 4。

### Task 4: 逐镜头导演筛选与年龄匹配审查

**Files:**
- Create: `$RUN/qc/candidate-contact-sheet.jpg`
- Create: `$RUN/production/source-clip-map.json`
- Create: `$RUN/production/footage-ledger.json`
- Create: `$RUN/production/usage-rights-note.json`
- Create: `$RUN/media/approved/*.mp4`

**Interfaces:**
- Consumes: Task 3 候选池。
- Produces: 40—45 秒少年主题批准镜头集合。

- [ ] **Step 1: 为全部候选生成视觉抽检帧**

```bash
for f in "$RUN"/media/candidates/*.mp4; do
  base="$(basename "${f%.*}")"
  mkdir -p "$RUN/qc/candidate-frames/$base"
  ffmpeg -hide_banner -loglevel error -y -i "$f" \
    -vf "fps=1/2,scale=360:-2" -frames:v 12 \
    "$RUN/qc/candidate-frames/$base/%02d.jpg"
done
```

- [ ] **Step 2: 对每个拟入选区间做逐秒审查**

每段必须记录：少年/成年/不可判断、人物关系、动作起止、字幕/标题/评论框、平台标识、竖屏重构、清晰度、运动方向和选择理由。

- [ ] **Step 3: 裁出批准片段**

每段使用正向连续动作：

```bash
ffmpeg -hide_banner -y -ss SOURCE_IN -to SOURCE_OUT -i INPUT \
  -an -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=25,format=yuv420p" \
  -c:v libx264 -preset medium -crf 18 -movflags +faststart OUTPUT
```

实际执行时用已核验的数值替换 `SOURCE_IN`、`SOURCE_OUT`、`INPUT`、`OUTPUT`，并把同一数值写入 `source-clip-map.json`。

- [ ] **Step 4: 计算人物年龄占比**

```python
recognizable = [s for s in shots if s["recognizable_person"]]
youth_seconds = sum(s["duration_seconds"] for s in recognizable if s["age_class"] == "youth")
adult_seconds = sum(s["duration_seconds"] for s in recognizable if s["age_class"] == "adult")
assert youth_seconds / sum(s["duration_seconds"] for s in recognizable) >= 0.80
assert adult_seconds / sum(s["duration_seconds"] for s in recognizable) <= 0.20
```

- [ ] **Step 5: 验证主题覆盖**

批准集合必须至少覆盖五类必备画面和三类力量特写。缺少任一硬指标时返回 Task 3 搜索，不得通过改口播掩盖弱素材。

### Task 5: 确认口播、生成 TTS 和数字人

**Files:**
- Create: `$RUN/audio/parts/opening.wav`
- Create: `$RUN/audio/parts/closing.wav`
- Create: `$RUN/audio/presenter-only.wav`
- Create: `$RUN/audio/master-voiceover.wav`
- Create: `$RUN/production/tts-result.json`
- Create: `$RUN/production/tts-opening.json`
- Create: `$RUN/production/tts-closing.json`
- Create: `$RUN/video/anchor-generated.mp4`
- Create: `$RUN/production/avatar-result.json`

**Interfaces:**
- Consumes: Task 4 已核验的人物关系和最终口播。
- Produces: 1.1 倍速主持人音频、完整静音插播母带和新数字人视频。

- [ ] **Step 1: 根据最终素材锁定“父亲”措辞**

如果至少一条清晰素材能够支持父子或父亲关系，保留“父亲把孩子托上马背”；否则改为“长辈把孩子送上马背”。重新运行脚本评审并将 `facts_traceable=true`。

- [ ] **Step 2: 使用 Giggle TTS 生成开场和结尾**

参数固定：

```json
{
  "voice_id": "cobra_design_20250717_162347_664524",
  "voice_display_name": "未来科技解说",
  "emotion": "neutral",
  "speed": 1.1
}
```

分别保存 opening/closing WAV 和 MP3，并用 ASR 验证最后一句完整。

- [ ] **Step 3: 构建完整音频母带**

```bash
ffmpeg -hide_banner -y \
  -i "$RUN/audio/parts/opening.wav" \
  -f lavfi -t BROLL_DURATION -i anullsrc=r=48000:cl=mono \
  -i "$RUN/audio/parts/closing.wav" \
  -filter_complex '[0:a][1:a][2:a]concat=n=3:v=0:a=1[a]' \
  -map '[a]' -ar 48000 -ac 1 "$RUN/audio/master-voiceover.wav"
```

`BROLL_DURATION` 使用 Task 4 批准片段总时长，必须在 40—45 秒。

- [ ] **Step 4: 生成新数字人**

先运行 generation preflight，再使用锁定主持人参考图和 `audio/presenter-only.wav` 调用 Topview avatar4。下载结果为 `video/anchor-generated.mp4`，记录 task ID、board ID、编辑链接和来源 URL。

- [ ] **Step 5: 数字人初审**

生成 `qc/avatar-contact.jpg`，确认短发 C2、五官清晰、口型稳定、服装和演播室一致。失败时重新生成，不进入剪辑。

### Task 6: 构建热血混剪和正式时间线

**Files:**
- Create: `$RUN/media/approved/grassland-youth-montage.mp4`
- Create: `$RUN/production/shot-selection.json`
- Create: `$RUN/production/timeline.json`
- Create: `$RUN/production/render-plan.json`
- Create: `$RUN/production/render.sh`
- Create: `$RUN/production/program-transcript.json`
- Create: `$RUN/copy/full-program-transcript.txt`

**Interfaces:**
- Consumes: Task 4 批准镜头和 Task 5 主持人音频/视频。
- Produces: 40—45 秒连续静音插播、完整时间线和可渲染脚本。

- [ ] **Step 1: 按五段情绪结构排序**

顺序固定为：托举约5秒、初露锋芒约8—10秒、动作高潮约14—16秒、群体气势约7—9秒、辽阔收束约6—8秒。镜头数量由动作完整度决定，不固定为三段或九段。

- [ ] **Step 2: 拼接无音轨混剪**

将所有批准片段统一为 1080×1920、25fps、H.264 后使用 concat demuxer 拼接。输出必须没有音轨：

```bash
ffprobe -v error -select_streams a -show_entries stream=index -of csv=p=0 "$RUN/media/approved/grassland-youth-montage.mp4"
```

Expected: 无输出。

- [ ] **Step 3: 创建正式时间线**

时间线只含三类区段：主持人开场、连续 B-roll、主持人结尾。B-roll 内保留逐镜头记录，用于年龄占比、语义和边界 QC。

- [ ] **Step 4: 创建完整节目转写**

`program-transcript.json` 和 `full-program-transcript.txt` 必须记录开场口播、40—45秒“静音插播，无可听源对白”、结尾口播。

- [ ] **Step 5: 运行三阶段预检**

```bash
for stage in generation timeline render; do
  PYTHONPATH=src .venv/bin/python -m avatar_pipeline.cli news-v5-preflight \
    --run-dir "$RUN" --stage "$stage" --project-root "$PWD"
done
```

Expected: 三阶段无 hard block；超过默认 B-roll 比例只可作为有导演说明的 advisory。

### Task 7: 渲染成片并生成技术 QC 证据

**Files:**
- Create: `$RUN/video/final-clean.mp4`
- Create: `$RUN/qc/ffprobe.json`
- Create: `$RUN/qc/blackdetect.log`
- Create: `$RUN/qc/silencedetect.log`
- Create: `$RUN/qc/decode-errors.log`
- Create: `$RUN/qc/audio-comparison.json`
- Create: `$RUN/qc/contact-sheet.jpg`
- Create: `$RUN/qc/boundary-contact.jpg`
- Create: `$RUN/qc/tail-contact.jpg`

**Interfaces:**
- Consumes: Task 6 渲染脚本和完整音频母带。
- Produces: V04 成片和自动 QC 所需证据。

- [ ] **Step 1: 执行渲染脚本**

```bash
bash "$RUN/production/render.sh"
```

- [ ] **Step 2: 验证媒体规格**

```bash
ffprobe -v error -show_streams -show_format -of json "$RUN/video/final-clean.mp4" > "$RUN/qc/ffprobe.json"
```

Expected: 1080×1920、25fps、H.264、AAC 48kHz mono，总时长 45—90 秒。

- [ ] **Step 3: 运行黑帧、静音、解码和音频完整性检查**

长静音只允许落在批准的连续 B-roll 区间；音频相关度必须不低于 0.99，时移不超过 40ms，样本数一致。

- [ ] **Step 4: 生成逐镜头接触表**

必须能够肉眼确认：少年占主体、没有烧录字幕/标题/评论框、所有动作正放、开关场切点自然、结尾完整。

- [ ] **Step 5: 标记已渲染**

```bash
PYTHONPATH=src .venv/bin/python -m avatar_pipeline.cli news-v5-mark-rendered --run-dir "$RUN"
```

### Task 8: 自动 QC、导演 QC 和最终交付

**Files:**
- Create: `$RUN/qc/automatic-qc-result.json`
- Create: `$RUN/qc/director-review.json`
- Create: `$RUN/qc/director-review-result.json`
- Create: `$RUN/qc/final-qc-report.json`
- Create: `$RUN/qc/final-status.json`
- Create: `$RUN/qc/sha256.txt`

**Interfaces:**
- Consumes: Task 7 成片和全部证据。
- Produces: `ready_to_deliver` 的 V04 交付包。

- [ ] **Step 1: 运行自动 QC**

```bash
PYTHONPATH=src .venv/bin/python -m avatar_pipeline.cli news-v5-build-qc \
  --run-dir "$RUN" | tee "$RUN/qc/automatic-qc-result.json"
```

Expected: 所有 hard block 为 PASS，manifest 进入 `automatic_qc_passed`。

- [ ] **Step 2: 完成导演复核**

导演复核必须包含十个标准检查，并在 `footage_relevance`、`edit_rhythm` 和 `overall_news_effect` 中额外确认：

- 少年可辨识镜头占比不低于 80%；
- 成年画面只承担传承功能且不超过 20%；
- 至少五类必备画面和三类力量特写；
- 画面能够建立热血、速度、力量和草原辽阔感；
- 台词中的父亲/长辈关系与最终素材一致。

- [ ] **Step 3: 应用导演复核**

```bash
PYTHONPATH=src .venv/bin/python -m avatar_pipeline.cli news-v5-apply-director-review \
  --run-dir "$RUN" | tee "$RUN/qc/director-review-result.json"
```

Expected: `overall_passed=true`、`director_review.approved=true`、manifest `status=ready_to_deliver`。

- [ ] **Step 4: 运行完整项目测试**

```bash
PYTHONPATH=.:src .venv/bin/pytest -q
```

Expected: 0 failures。

- [ ] **Step 5: 最终状态与哈希验证**

```bash
PYTHONPATH=src .venv/bin/python -m avatar_pipeline.cli news-v5-status \
  --run-dir "$RUN" | tee "$RUN/qc/final-status.json"
shasum -a 256 "$RUN/video/final-clean.mp4"
```

Expected: `status=ready_to_deliver`，所有 records 为 true，最终哈希与 manifest 和 QC 报告一致。

- [ ] **Step 6: 交付清单**

最终回复必须提供：成片绝对路径、标题、主持人口播稿、完整节目转写、素材链接清单、时长、规格、主持人、音色、语速、少年/成年占比、入选画面类型、插播时长、字幕/标题审查结果、来源水印披露、自动 QC、导演 QC、完整测试结果、SHA-256 和 Topview 编辑链接。
