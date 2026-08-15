# V5 手动新闻视频生产 Runbook

本 Runbook 固化 V5 成功案例的生产方法，用于制作 **45—90 秒、数字人主持人主讲、9:16、1080×1920、25fps 的无字净版新闻短视频**。流程只有一个显式交互点：系统用双漏斗从广泛注意力信号中筛出最多 8 个真正合格的热点候选，也允许少于 3 个或明确报告没有 S 级选题；用户与导演共同评估并确认选题。确认后，下游事实核验、口播稿、TTS、数字人、素材、剪辑和 QC 均按非交互式流程连续执行；CLI 只在事实冲突、权利风险或硬质量门失败时停止，不在普通步骤中反复请求确认。

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
- 不添加背景音乐；插播素材原声由导演逐段判断，仅关键事实对话或强烈自然反应可保留，并须先剪取、响度标准化并合入批准的完整主音频；
- 禁止倒放、循环、乒乓播放；
- 结尾必须回到主持人，使用完整句自然收束；
- 来源、下载时间、哈希和 AI 生成信息保存为旁路记录，不烧录到无字净版。
- 最终渲染不得临时直接映射任一素材音轨；批准的现场原声必须提前写入 `audio/master-voiceover.wav`，自动 QC 以该完整混合母版为唯一音频基准。

素材可以保留用户明确接受的来源水印、平台角标或账号标识，但必须在素材账本中如实披露并记录该次用户授权。**允许保留来源标识不等同于已经获得版权授权**。烧录字幕仍是独立的画面质量策略，除非用户另外明确接受，否则不得用于成片。发布方仍需自行判断授权、合理使用和平台规则。

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
export RUN_SLUG="已确认选题的短标识"
export RUN_TOPIC="候选池中经用户确认的完整标题"
export RUN_VERSION="1"
export TOPIC_SELECTION="$PROJECT_ROOT/workspace/hotspot-selections/${RUN_DATE}/topic-selection.json"
export RUN_DIR="$PROJECT_ROOT/output/manual-news-${RUN_DATE}-${RUN_SLUG}-v01"
```

同一目录不可覆盖。返工必须提高版本号并通过 `--parent-run-id` 关联上一版。

## 3. 跨领域热点候选门与运行初始化

### 3.1 生成并导入候选池

先从社会民生、科技、财经、国际、政策、消费、教育、网红热点、普通人热议、文娱文化、天气灾害等领域抓取当日信号，形成 20—40 个原始话题；聚类和内部评审后，只向用户展示最多 8 个通过硬核验的 S/A 级候选。允许少于 3 个，不为数量或类别补入弱题。候选 JSON 必须给出最新进展、热度依据、观看动机、权威来源、画面条件、风险和导演评级。

```bash
python -m avatar_pipeline.cli --workspace "$PROJECT_ROOT/workspace" hotspot-pool-import \
  --date "$RUN_DATE" \
  --file "$PROJECT_ROOT/tmp/hotspot-selection/${RUN_DATE}/candidate-pool.json"

python -m avatar_pipeline.cli --workspace "$PROJECT_ROOT/workspace" hotspot-pool-status \
  --date "$RUN_DATE"
```

评估文件：

```text
workspace/hotspot-selections/YYYY-MM-DD/candidate-pool.json
workspace/hotspot-selections/YYYY-MM-DD/candidate-pool.md
```

此时状态必须是 `awaiting_user_evaluation`，**未确认前禁止进入 V5 生产**。用户与导演共同评估后，执行一次选题批准：

```bash
python -m avatar_pipeline.cli --workspace "$PROJECT_ROOT/workspace" hotspot-select \
  --date "$RUN_DATE" \
  --candidate-id "用户确认的候选编号" \
  --actor owner \
  --reason "共同评估后确认"
```

批准记录保存为 `workspace/hotspot-selections/YYYY-MM-DD/topic-selection.json`，并绑定候选池 SHA-256，防止候选池变化后误用旧批准。

### 3.2 初始化版本安全的运行目录

```bash
python -m avatar_pipeline.cli news-v5-init \
  --output-root "$PROJECT_ROOT/output" \
  --date "$RUN_DATE" \
  --slug "$RUN_SLUG" \
  --topic "$RUN_TOPIC" \
  --version "$RUN_VERSION" \
  --topic-selection "$TOPIC_SELECTION" \
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
│   ├── topic-selection.json
│   └── run-manifest.json
├── qc/
└── video/
```

禁止覆盖或清理历史运行目录；不要批量删除 `output/` 中的旧媒体。

## 4. 热点、事实和口播稿质量门

### 4.1 热点选择

热点抓取是制作上游的核心，必须优先于写稿和找素材。候选池不得由平庸、常青或低传播话题补位，也不得只集中于天气，更不能因为百度榜单靠前就宣称“今日最热”。进入生产前，导演必须确认：

1. 事件在今天出现新增事实、搜索增长或跨平台传播，而不是泛化、常青或过时话题；
2. 能回答“为什么是今天”，并有明确变化、冲突、反差、影响、数字、风险或认知缺口；
3. 普通人有清晰的观看理由，观众看完能获得具体解释；
4. 核心事实至少有第一方、官方或独立可靠来源支撑，且不存在未解决冲突；
5. 有足够强的真实视觉素材，并提前检查相关性、清晰度、年代、口罩或疫情时期错配和可用连续时长；
6. 标题和前三秒开场能准确制造信息需求，但不夸大事实；
7. 热度寿命仍足以覆盖制作与发布，未错过窗口。

成功案例说明，选题吸引力可以来自不同结构：胖东来门店关停依靠“仍然盈利却关闭”的强反差；《奥德赛》依靠“三千年史诗为什么今天突然刷屏”的知识缺口和时机解释。系统应识别这类结构，而不是只寻找传统突发新闻。

热点发现应交叉观察国内榜单、权威媒体、搜索需求、社交讨论、视频传播和垂直社区。新华社/新华网、人民日报、央视新闻、中国青年报、政府部门和当事机构内容，可用于热点发现、事实核验或素材候选。抖音、小红书、B站、X、YouTube 等平台内容可用于判断传播热度、重复问题和寻找现场素材线索，但注意力证据不能自动代替事实证据。内部可以记录平台信号，口播不得机械说“B站上最近很火”；核心事实应回到原始公告、第一方资料或独立可靠报道。

评分采用真实热度 30、内容吸引力 35、事实可靠性 20、视频潜力 15。单平台伪热点、旧闻回流、营销账号独占传播、无可靠事实、无相关素材、核心事实冲突和必须依靠失真标题才能点击的题目直接淘汰。用户候选最多 8 条，允许少于 3 条；无 S 级时明确报告，不凑数。

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

其中 `copy/voiceover.txt` 只记录主持人口播，不得用它代替完整成片台词。只要时间线保留了现场原声，后续还必须生成 `production/program-transcript.json` 和 `copy/full-program-transcript.txt`。

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

- 水印、平台角标和账号标识是否存在，并在账本中如实记录；
- 如果存在来源标识，是否已有本次运行的用户明确接受记录；
- 烧录字幕是否存在；除非用户另外明确接受，否则不得使用；
- 项目自身不新增字幕、标题、来源条、Logo 或账号标识；
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
      "visible_source_marks_allowed_by_user": false,
      "burned_captions_allowed_by_user": false,
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

### 7.2 导演动态插播设计

```bash
python -m avatar_pipeline.cli news-v5-guidance --duration 52.128
```

命令只返回宽松的导演参考范围，不根据时长自动指定固定段数。当前基线为：

- `selection_mode=director_dynamic`，`count_fixed=false`；
- 常见参考为 1—5 个插播块，但不是配额；
- 单个连贯块参考 4.5—12 秒，优先约 9 秒；
- 总占比参考 20%—45%；
- 优先连贯叙事块，避免频繁短切。

插播次数、单段时长和总占比必须由导演根据题材、稿件结构、素材质量、动作完整性和整体观看效果共同决定。不要为了凑数量而拆镜头，也不要因为过去常用三段就把三段写成模板。对于视觉驱动的 80 秒新闻解释视频，2—4 个约 9—12 秒的长块通常是合理起点；如果素材或叙事需要，也可以少于或多于这个起点。

专业节奏以“一个插播块完整表达一个信息”为先：同一语义段优先连续呈现，避免在相邻短句间反复切回主持人。短块只有在信息变化、动作节点或证据切换确实需要时使用。

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

### 8.1 完整节目台词

时间线确定后，创建 `production/program-transcript.json`。它必须逐段覆盖 `production/timeline.json`，包括主持人口播和保留的现场原声；每段的 `script_segment_id`、画面类型、开始时间和结束时间必须与时间线一致。

```json
{
  "run_id": "manual-news-2026-08-12-台风强降雨-v01",
  "title_path": "copy/title.txt",
  "output_path": "copy/full-program-transcript.txt",
  "director_approved": true,
  "segments": [
    {
      "script_segment_id": "script-01",
      "visual_type": "anchor",
      "audio_role": "presenter",
      "start": 0.0,
      "end": 8.0,
      "lines": [{"speaker": "主持人", "text": "经审核通过的主持人口播。"}]
    },
    {
      "script_segment_id": "source-dialogue-01",
      "visual_type": "broll",
      "audio_role": "source_audio",
      "start": 8.0,
      "end": 14.0,
      "lines": [
        {"speaker": "现场人物", "text": "经听写核对的原声内容。"}
      ]
    }
  ]
}
```

规则：

- 每个时间线片段必须且只能对应一个节目台词片段，不能遗漏原声段；
- 现场原声必须根据最终采用的音频逐字核对，听不清时保守标注，不得推测或补写；
- `director_approved` 只在导演核对成片声音、说话人和文字后设为 `true`；
- 修改时间线或台词记录后必须重新生成，旧文件视为失效；
- `copy/voiceover.txt` 是主持人口播稿；`copy/full-program-transcript.txt` 是最终成片全部可听台词。

生成完整节目台词：

```bash
python -m avatar_pipeline.cli news-v5-build-transcript --run-dir "$RUN_DIR"
```

导演交付门会再次校验生成文件是否完整、是否与结构化记录及最终时间线一致。

执行：

```bash
python -m avatar_pipeline.cli news-v5-preflight \
  --run-dir "$RUN_DIR" \
  --stage timeline
```

插播次数、时长和占比只与宽松参考范围比较，偏离时产生 advisory，供导演复审而不自动否决；语义映射、文件哈希、镜头批准、时间线连续性和结尾不合格仍会硬阻断。导演可基于题材和最终效果批准范围外方案，但必须在 `director-review.json` 的 `edit_rhythm` 中记录理由。

## 9. 安全 FFmpeg 合成

将脚本保存为 `production/render.sh`。脚本必须：

- 只使用主持人视频画面、批准的正向镜头和 `audio/master-voiceover.wav`；
- 最终渲染不直接映射素材音轨；批准的现场原声已经预先标准化并合入 `audio/master-voiceover.wav`；
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
5. `footage_relevance`：现场画面与当句台词直接对应，清晰、年代匹配，无口罩或疫情时期错配；题材不限于台风和积水。

### 第二遍：节奏、净版和完整交付

逐项检查：

1. `edit_rhythm`：插播数量不套固定公式；单块不过短、切换不过密，连贯叙事优先，并记录任何偏离宽松参考范围的导演理由；
2. `no_watermarks_text`：兼容保留该 ID；实际检查为来源水印/平台标识已如实披露且符合本次用户策略、烧录字幕符合独立策略，并且项目没有新增字幕、标题、来源条、Logo 或账号标识；
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
      "description": "来源标识披露合规且无项目新增文字",
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
| timeline | 素材来源标识未披露或未获本次用户接受、烧录字幕不合规、哈希变化、语义不匹配、尾部太短 | 补全策略记录或重选完整镜头，重做时间线 |
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
copy/full-program-transcript.txt
copy/title.txt
production/run-manifest.json
production/quality-profile.yaml
production/fact-evidence.json
production/script-review.json
production/footage-ledger.json
production/shot-selection.json
production/timeline.json
production/program-transcript.json
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
主持人口播：<copy/voiceover.txt>
完整节目台词：<copy/full-program-transcript.txt，包含现场原声>
成片：<video/final-clean.mp4>
规格：1080×1920 / 25fps / H.264 / AAC 48kHz单声道
时长：<实际秒数，须为45—90秒>
主持人：host-c2-pro-candidate-2-final
音色：未来科技解说（cobra_design_20250717_162347_664524）
净版：无项目新增字幕、标题、来源条、Logo或音乐；现场原声仅限导演批准片段
QC：自动QC通过 + 两遍导演审核通过
SHA-256：<qc/sha256.txt>
来源记录：production/footage-ledger.json
说明：用户允许保留来源水印不等同于版权授权
```

## 普通人真情类选题的前置限制

普通人真情、美好、善意类内容只有在 `ordinary_life_moment` 强制准入门通过后，才能进入口播、素材设计和 V5 制作。制作端不得把以下内容包装成普通人真实瞬间：职业博主策划公益、挑战栏目、送礼栏目、剧情摆拍或无法找到原始记录者的媒体二剪。具体核验字段和淘汰标准见 `docs/runbooks/manual-hotspot-sampling.md`。 这里的主体必须是个人生活记录账号中的普通人，事件必须发生在原本存在的日常场景，并提供可观察的自然真情或善意证据；“博主拍普通人”不能等同于“普通人记录自己的生活”。
