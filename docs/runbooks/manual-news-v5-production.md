# V5 手动新闻视频生产 Runbook

本 Runbook 固化 V5 成功案例的生产方法，用于制作 **45—90 秒、数字人主持人主讲、9:16、1080×1920、25fps 的无字净版新闻短视频**。流程为非交互式：操作员按阶段准备记录和文件，CLI 只在质量门失败时停止，不在普通步骤中反复请求确认。

> 示例日期、主题、标题、事实、URL 和素材区间仅展示文件格式。每次生产必须使用当次运行的真实日期、当前热点、权威来源和实际素材，不得照抄示例事实。

## 1. V5 锁定项与成片边界

质量配置唯一来源：`configs/news-video-quality-v5.yaml`。

- 时长：45—90 秒；
- 画幅：9:16；
- 输出：1080×1920、25fps、H.264；
- 音频：AAC、48kHz、单声道；
- 主持人：`host-c2-pro-candidate-2-final`；
- 主持人参考图：`output/host-v12-c2-pro/GPT-Image-2-Pro-C2-Pro-主持人最终选定.png`；
- 主持人 SHA-256：`939324593eb718cd2a39be4c171f74178a6a48442f7e0d61afe8a875011e8a47`；
- 音色：`未来科技解说`；
- 音色 ID：`cobra_design_20250717_162347_664524`；
- 成片不烧录字幕、标题、来源条、Logo、平台角标或账号标识；
- 不添加背景音乐，不保留或混入插播素材原声；
- 禁止倒放、循环、乒乓播放；
- 结尾必须回到主持人，使用完整句自然收束；
- 来源、下载时间、哈希和 AI 生成信息保存为旁路记录，不烧录到无字净版。

“无水印”只表示素材满足本项目的画面准入规则，**不等同于已经获得版权授权**。必须保留来源和使用依据，发布方仍需自行判断授权、合理使用和平台规则。

## 2. 环境和变量

在项目根目录执行：

```bash
cd /Users/liuweidong/Desktop/AI-Avatar-Scripts-Video
source .venv/bin/activate
export PYTHONPATH=src
```

为当次运行定义变量：

```bash
export PROJECT_ROOT="$PWD"
export RUN_DATE="2026-08-12"
export RUN_SLUG="台风强降雨"
export RUN_TOPIC="台风影响减弱但北方强降雨风险仍在持续"
export RUN_VERSION="1"
export RUN_DIR="$PROJECT_ROOT/output/manual-news-${RUN_DATE}-${RUN_SLUG}-v01"
```

同一目录不可覆盖。返工必须提高版本号并通过 `--parent-run-id` 关联上一版。

## 3. 初始化版本安全的运行目录

```bash
python -m avatar_pipeline.cli news-v5-init \
  --output-root "$PROJECT_ROOT/output" \
  --date "$RUN_DATE" \
  --slug "$RUN_SLUG" \
  --topic "$RUN_TOPIC" \
  --version "$RUN_VERSION" \
  --quality-config "$PROJECT_ROOT/configs/news-video-quality-v5.yaml"

mkdir -p "$RUN_DIR/media"
python -m avatar_pipeline.cli news-v5-status --run-dir "$RUN_DIR"
```

初始化后目录结构：

```text
RUN_DIR/
├── audio/
├── copy/
├── media/                  # 操作员创建，保存下载原片和批准镜头
├── production/
│   ├── quality-profile.yaml
│   └── run-manifest.json
├── qc/
└── video/
```

禁止覆盖或清理历史运行目录；不要批量删除 `output/` 中的旧媒体。

## 4. 热点、事实和口播稿质量门

### 4.1 热点选择

热点抓取是制作上游的核心。进入生产前，导演必须确认：

1. 事件正在当日传播，而不是泛化、常青或过时话题；
2. 有明确变化、冲突、影响、数字、风险或认知缺口；
3. 至少有权威来源可以支撑核心事实；
4. 有足够强的真实视觉素材，例如台风、强风、城市积水、抢险、交通影响；
5. 标题和开场能准确制造信息需求，但不夸大事实。

抖音、小红书、B站、X 等短视频可用于判断传播热度和寻找现场素材线索，但不能代替事实核验。新闻事实必须回到政府部门、气象部门、权威媒体、当事机构或原始文件。

### 4.2 事实证据记录

创建 `production/fact-evidence.json`：

```json
{
  "run_id": "manual-news-2026-08-12-台风强降雨-v01",
  "authoritative_sources": [
    {
      "source_id": "official-1",
      "platform": "official",
      "title": "当次运行的权威通报标题",
      "url": "https://example.com/current-official-source",
      "published_at": "2026-08-12T08:00:00+08:00",
      "reliability_note": "发布机构和原始信息说明"
    }
  ],
  "event_time": "2026-08-12T08:00:00+08:00",
  "locations": ["实际涉及地区"],
  "verified_facts": ["经来源核实的核心事实"],
  "verified_numbers": ["经核实的数字及口径"],
  "uncertainties": ["仍不确定或等待更新的内容"],
  "prohibited_claims": ["没有证据不得写入稿件的说法"]
}
```

### 4.3 口播稿导演审稿

输出：

```text
copy/title.txt
copy/voiceover.txt
production/script-review.json
```

稿件标准：

- 短句为主，一句只承载一个主要信息；
- 开头快速说明“发生了什么、为什么现在值得关注”；
- 中段按照事实变化、影响范围、关键数字、现场情况推进；
- 使用新闻播报的确定表达，不描述编辑或查证过程；
- 不使用“某份公报一边说……一边说……”等站在资料阅读者角度的措辞；
- 后半段仍保持新闻联播式信息组织，不突然变成泛泛建议；
- 最后一句完整、自然、可独立落点，禁止戛然而止；
- 不用空泛的“最后注意”等尾句拖延收束。

`production/script-review.json`：

```json
{
  "run_id": "manual-news-2026-08-12-台风强降雨-v01",
  "script_path": "copy/voiceover.txt",
  "title_path": "copy/title.txt",
  "target_duration_seconds": 60,
  "actual_audio_duration_seconds": 60,
  "authoritative_tone_passed": true,
  "sentence_clarity_passed": true,
  "information_density_passed": true,
  "ending_complete": true,
  "facts_traceable": true,
  "director_approved": true
}
```

## 5. TTS 和数字人生成

### 5.1 TTS

只使用锁定音色：

```text
未来科技解说
cobra_design_20250717_162347_664524
```

生成的母版保存为：

```text
audio/master-voiceover.wav
```

TTS 后必须核查：

- 实际时长在 45—90 秒；
- 语速清晰、克制，不吞字；
- 停顿与短句结构一致；
- 最后一整句被完整播出；
- 没有自动替换数字、地名或专有名词；
- 不在后续合成中二次截短主音频。

### 5.2 数字人

数字人必须使用锁定参考图和已批准 TTS 音频，输出：

```text
video/anchor.mp4
```

生成前运行硬质量门：

```bash
python -m avatar_pipeline.cli news-v5-preflight \
  --run-dir "$RUN_DIR" \
  --stage generation \
  --project-root "$PROJECT_ROOT"
```

此门会重新计算实际主持人参考图哈希，并核验主持人 ID、音色 ID、事实包、稿件批准、标题、口播和音频文件。任何一项失败都不得生成。

数字人素材初审：短发和人物身份一致；五官清晰自然；口型稳定；肩颈和服装不畸变；演播室、机位和裁切与 V5 一致。

## 6. 下载和筛选真实插播素材

### 6.1 素材方向

优先寻找能直接解释台词的真实现场画面，而不是泛化氛围视频。天气新闻可优先使用：

- 台风或强风中树木、路牌、建筑外立面的连续变化；
- 城市道路积水、车辆涉水、交通中断；
- 抢险排水、人员转移、封路或公共设施影响；
- 权威机构发布的雷达、路径或现场资料，但无字净版不得烧录来源条。

每个镜头必须对应一个脚本段落和语义角色。不要为了“有画面”插入与台词无关的雨景。

### 6.2 下载规则

可以从原始发布页或可用下载工具获取素材，例如用户指定的 B站下载工具或多平台下载工具。下载后只允许本地检查和剪辑，不得绕过访问控制、付费限制或版权保护。

每个文件进入制作前必须人工确认：

- 无水印；
- 无平台角标；
- 无账号标识；
- 无烧录字幕；
- 画质足够；
- 没有倒放、循环或重复片段；
- 时间顺序自然，动作连续；
- 与对应台词语义一致。

记录来源 URL、下载时间和 SHA-256：

```bash
shasum -a 256 "$RUN_DIR/media/source-01.mp4"
```

创建 `production/footage-ledger.json`：

```json
{
  "run_id": "manual-news-2026-08-12-台风强降雨-v01",
  "assets": [
    {
      "asset_id": "asset-wind-01",
      "source_platform": "bilibili",
      "source_url": "https://example.com/original-video-page",
      "downloaded_at": "2026-08-12T12:00:00+08:00",
      "local_path": "media/source-01.mp4",
      "sha256": "替换为64位小写SHA-256",
      "watermark_free": true,
      "platform_logo_free": true,
      "account_mark_free": true,
      "burned_caption_free": true,
      "visual_relevance": "强风造成城市现场影响",
      "user_usage_rule_passed": true
    }
  ]
}
```

## 7. 接触表、镜头选择和节奏设计

### 7.1 先制作接触表

对每个下载原片按固定间隔抽帧，先看完整动作，再决定区间：

```bash
ffmpeg -hide_banner -y -i "$RUN_DIR/media/source-01.mp4" \
  -vf "fps=1/2,scale=270:-1,tile=4x4" \
  -frames:v 1 "$RUN_DIR/qc/source-01-contact-sheet.jpg"
```

必要时对候选区间单独制作高密度接触表。不能只看首帧，也不能用随机切片替代完整动作检查。

### 7.2 插播次数和时长建议

```bash
python -m avatar_pipeline.cli news-v5-guidance --duration 52.128
```

导演目标：

| 成片时长 | 插播次数 | 单次建议 | 总占比 |
|---|---:|---:|---:|
| 45—55 秒 | 2—3 次 | 4.5—6.5 秒 | 25%—35% |
| 56—70 秒 | 3 次 | 5—7 秒 | 25%—35% |
| 71—90 秒 | 3—4 次 | 5—8 秒 | 25%—38% |

这不是机械定额。专业新闻节奏以“一个镜头完整表达一个信息”为先：不要将一段连续现场拆成多次过短插播；不要在相邻短句间频繁来回切主持人；同一事件阶段优先使用一个 5—8 秒、动作完整的镜头。

### 7.3 镜头记录

创建 `production/shot-selection.json`：

```json
{
  "run_id": "manual-news-2026-08-12-台风强降雨-v01",
  "shots": [
    {
      "shot_id": "shot-wind-01",
      "asset_id": "asset-wind-01",
      "script_segment_id": "script-02",
      "semantic_role": "展示强风对城市运行的直接影响",
      "source_in": 12.5,
      "source_out": 18.5,
      "target_duration_seconds": 6.0,
      "continuous_action": true,
      "forward_playback": true,
      "visual_quality_passed": true,
      "director_approved": true
    }
  ]
}
```

## 8. 时间线设计

创建 `production/timeline.json`。所有区间必须首尾相接，无间隙、无重叠，并精确结束于主音频时长：

```json
{
  "run_id": "manual-news-2026-08-12-台风强降雨-v01",
  "audio_duration_seconds": 60.0,
  "segments": [
    {
      "type": "anchor",
      "start": 0.0,
      "end": 8.0,
      "script_segment_id": "script-01"
    },
    {
      "type": "broll",
      "start": 8.0,
      "end": 14.0,
      "script_segment_id": "script-02",
      "shot_id": "shot-wind-01"
    },
    {
      "type": "anchor",
      "start": 14.0,
      "end": 60.0,
      "script_segment_id": "script-03"
    }
  ]
}
```

硬规则：

- 每个 B-roll 段必须引用已批准 `shot_id`；
- `script_segment_id` 必须与镜头记录一致；
- 时间线最后一段必须是主持人；
- 最后一段连续主持人时长至少占总时长 20%；
- 尾句音频完整，画面不能提前结束。

执行：

```bash
python -m avatar_pipeline.cli news-v5-preflight \
  --run-dir "$RUN_DIR" \
  --stage timeline
```

插播次数、时长和占比偏离导演目标会产生 advisory；语义映射、文件哈希、镜头批准、时间线连续性和结尾不合格会硬阻断。

## 9. 安全 FFmpeg 合成

将脚本保存为 `production/render.sh`。脚本必须：

- 只使用主持人视频画面、批准的正向镜头和 `audio/master-voiceover.wav`；
- 插播素材只取视频，不映射素材音轨；
- 不使用 `reverse`、`loop`、`stream_loop` 或 ping-pong；
- 不加字幕、标题、来源条、Logo 和音乐；
- 不使用 `-y` 覆盖已有最终成片；
- 输出到 `video/final-clean.mp4`。

示意骨架：

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/video/final-clean.mp4"
test ! -e "$OUT"

ffmpeg -hide_banner \
  -i "$ROOT/video/anchor.mp4" \
  -i "$ROOT/media/source-01.mp4" \
  -i "$ROOT/audio/master-voiceover.wav" \
  -filter_complex "\
[0:v]trim=start=0:end=8,setpts=PTS-STARTPTS,scale=1080:1920,fps=25[a0];\
[1:v]trim=start=12.5:end=18.5,setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=25[b0];\
[0:v]trim=start=14:end=60,setpts=PTS-STARTPTS,scale=1080:1920,fps=25[a1];\
[a0][b0][a1]concat=n=3:v=1:a=0[v]" \
  -map "[v]" -map 2:a:0 \
  -c:v libx264 -pix_fmt yuv420p -r 25 \
  -c:a aac -ar 48000 -ac 1 \
  -movflags +faststart -shortest "$OUT"
```

示意脚本中的区间必须替换为实际时间线。正式渲染前执行：

```bash
chmod +x "$RUN_DIR/production/render.sh"
python -m avatar_pipeline.cli news-v5-preflight \
  --run-dir "$RUN_DIR" \
  --stage render

"$RUN_DIR/production/render.sh"
python -m avatar_pipeline.cli news-v5-mark-rendered --run-dir "$RUN_DIR"
```

## 10. 自动 QC 证据

在执行 `news-v5-build-qc` 前生成以下文件：

```text
qc/ffprobe.json
qc/blackdetect.log
qc/silencedetect.log
qc/decode-errors.log
qc/audio-comparison.json
```

基础命令：

```bash
ffprobe -v error -show_streams -show_format -of json \
  "$RUN_DIR/video/final-clean.mp4" > "$RUN_DIR/qc/ffprobe.json"

ffmpeg -hide_banner -i "$RUN_DIR/video/final-clean.mp4" \
  -vf "blackdetect=d=0.05:pix_th=0.10" -an -f null - \
  2> "$RUN_DIR/qc/blackdetect.log"

ffmpeg -hide_banner -i "$RUN_DIR/video/final-clean.mp4" \
  -af "silencedetect=noise=-45dB:d=0.10" -vn -f null - \
  2> "$RUN_DIR/qc/silencedetect.log"

ffmpeg -v error -i "$RUN_DIR/video/final-clean.mp4" -f null - \
  2> "$RUN_DIR/qc/decode-errors.log"
```

`qc/audio-comparison.json` 由音频比对脚本生成，至少包含：

```json
{
  "best_lag_ms": 0.0,
  "normalized_correlation": 0.99999,
  "final_samples": 2880000,
  "master_samples": 2880000
}
```

必须使用实际计算结果，不得手工伪造。自动门要求相关性不低于配置值 `0.99`，样本数一致，并检查时移、流数量、编码、分辨率、帧率、音频规格、时长、黑帧、超过 1 秒的异常静音和解码错误。

执行：

```bash
python -m avatar_pipeline.cli news-v5-build-qc --run-dir "$RUN_DIR"
python -m avatar_pipeline.cli news-v5-status --run-dir "$RUN_DIR"
```

自动 QC 无硬失败时状态为 `automatic_qc_passed`；自动报告此时仍保持 `overall_passed: false`，因为导演审核尚未完成。

## 11. 两遍导演审核

### 第一遍：内容、人物和素材

逐项检查：

1. `host_identity`：短发主持人身份、服装、机位和参考图一致；
2. `facial_naturalness`：五官清晰，无明显 AI 感、糊脸或漂移；
3. `lip_sync`：全片口型和音频同步；
4. `script_clarity`：短句、重点、权威语气和结尾完整；
5. `footage_relevance`：台风、积水等现场画面与当句台词直接对应。

### 第二遍：节奏、净版和完整交付

逐项检查：

1. `edit_rhythm`：插播不过短、不过密，一个镜头完整表达一个信息；
2. `no_watermarks_text`：无水印、字幕、平台角标、账号标识和 Logo；
3. `no_reverse_repeat`：无倒放、循环、重复或异常跳帧；
4. `ending_complete`：最后完整句播完，连续主持人画面自然收束；
5. `overall_news_effect`：整体达到参考视频的主持人主讲加真实现场插播效果，但未复制其素材、文字、音乐、台标或版式。

为整片、切换边界和结尾生成审核图：

```text
qc/contact-sheet.jpg
qc/boundary-contact.jpg
qc/tail-contact.jpg
```

创建 `qc/director-review.json`，`checks` 必须包含以下十个 ID：

```json
{
  "run_id": "manual-news-2026-08-12-台风强降雨-v01",
  "approved": true,
  "checks": [
    {
      "id": "host_identity",
      "description": "主持人身份与锁定参考一致",
      "passed": true,
      "note": "短发、五官、服装和机位一致",
      "evidence_path": "qc/contact-sheet.jpg"
    },
    {
      "id": "facial_naturalness",
      "description": "五官清晰自然",
      "passed": true,
      "evidence_path": "qc/contact-sheet.jpg"
    },
    {
      "id": "lip_sync",
      "description": "口型同步",
      "passed": true,
      "evidence_path": "qc/contact-sheet.jpg"
    },
    {
      "id": "script_clarity",
      "description": "稿件短句、权威、完整",
      "passed": true,
      "evidence_path": "copy/voiceover.txt"
    },
    {
      "id": "footage_relevance",
      "description": "插播素材与台词语义匹配",
      "passed": true,
      "evidence_path": "qc/contact-sheet.jpg"
    },
    {
      "id": "edit_rhythm",
      "description": "插播次数和时长合理",
      "passed": true,
      "evidence_path": "qc/boundary-contact.jpg"
    },
    {
      "id": "no_watermarks_text",
      "description": "无水印和烧录文字",
      "passed": true,
      "evidence_path": "qc/contact-sheet.jpg"
    },
    {
      "id": "no_reverse_repeat",
      "description": "无倒放循环和异常重复",
      "passed": true,
      "evidence_path": "qc/boundary-contact.jpg"
    },
    {
      "id": "ending_complete",
      "description": "结尾句和主持人画面完整",
      "passed": true,
      "evidence_path": "qc/tail-contact.jpg"
    },
    {
      "id": "overall_news_effect",
      "description": "整体新闻效果达到V5标准",
      "passed": true,
      "evidence_path": "qc/contact-sheet.jpg"
    }
  ],
  "reviewed_at": "2026-08-12T18:00:00+08:00",
  "actor": "director"
}
```

最后执行：

```bash
python -m avatar_pipeline.cli news-v5-apply-director-review --run-dir "$RUN_DIR"
python -m avatar_pipeline.cli news-v5-status --run-dir "$RUN_DIR"
```

只有状态为 `ready_to_deliver` 且 `qc/final-qc-report.json` 的 `overall_passed` 为 `true` 才可交付。

## 12. 失败和返工路径

| 失败阶段 | 典型问题 | 返回动作 |
|---|---|---|
| generation | 主持人哈希、音色、事实包、稿件或音频不合格 | 修正输入记录；不要生成数字人 |
| timeline | 素材有水印、哈希变化、语义不匹配、尾部太短 | 重新下载或重选完整镜头，重做时间线 |
| render | 使用倒放/循环、映射素材声、缺输入、将覆盖旧成片 | 修正 `render.sh`；新版本输出不得覆盖 |
| automatic QC | 编码、黑帧、静音、解码或音频一致性失败 | 重新渲染并重新生成全部 QC 证据 |
| director review | 五官、口型、素材、节奏或结尾失败 | 创建新版本目录，针对失败项返工 |

返工示例：

```bash
python -m avatar_pipeline.cli news-v5-init \
  --output-root "$PROJECT_ROOT/output" \
  --date "$RUN_DATE" \
  --slug "$RUN_SLUG" \
  --topic "$RUN_TOPIC" \
  --version 2 \
  --parent-run-id "manual-news-${RUN_DATE}-${RUN_SLUG}-v01"
```

不要修改已交付版本的文件和哈希。

## 13. 固定交付清单

导演审核门会检查至少以下文件：

```text
video/final-clean.mp4
audio/master-voiceover.wav
copy/voiceover.txt
copy/title.txt
production/run-manifest.json
production/quality-profile.yaml
production/fact-evidence.json
production/script-review.json
production/footage-ledger.json
production/shot-selection.json
production/timeline.json
production/render.sh
qc/ffprobe.json
qc/final-qc-report.json
qc/contact-sheet.jpg
qc/boundary-contact.jpg
qc/tail-contact.jpg
qc/sha256.txt
```

固定交付摘要：

```text
运行ID：<run_id>
主题：<topic>
标题：<copy/title.txt 第一行或批准标题>
成片：<video/final-clean.mp4>
规格：1080×1920 / 25fps / H.264 / AAC 48kHz单声道
时长：<实际秒数，须为45—90秒>
主持人：host-c2-pro-candidate-2-final
音色：未来科技解说（cobra_design_20250717_162347_664524）
净版：无字幕、标题、来源条、Logo、音乐和素材原声
QC：自动QC通过 + 两遍导演审核通过
SHA-256：<qc/sha256.txt>
来源记录：production/footage-ledger.json
说明：无水印准入不等同于版权授权
```
