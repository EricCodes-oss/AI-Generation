# 婚姻含金量新闻 V3 原声主导版 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 制作独立的 V3 新闻短视频，以同一对中国夫妻的连续生活原声为主要叙事，固定短发主持人仅做简短开场和结尾。

**Architecture:** 以 `BV13M7J6nEFN` 对应的 76.7 秒同人物生活原片为主素材，全网同人物原片只在能补全真实互动且通过净版检查时加入。节目采用“主持人开场 → 连续现场原声 → 主持人结尾”的三段结构，所有声音预先顺序写入单一母带，再由 FFmpeg 只映射该母带完成 9:16 合成。

**Tech Stack:** FFmpeg/ffprobe、Giggle TTS、Topview Avatar4、Bilibili/Douyin/YouTube 公开检索、JSON/YAML 制作记录、SHA-256、ZIP。

## Global Constraints

- 新运行目录必须是 `output/manual-news-2026-09-08-wife-value-v03`，不得覆盖 V2。
- 固定主持人 ID：`host-c2-pro-candidate-2-final`。
- 固定主持人图片：`tmp/host-v12-c2-pro/candidate2.png`。
- 固定图片 SHA-256：`939324593eb718cd2a39be4c171f74178a6a48442f7e0d61afe8a875011e8a47`。
- 固定音色：`未来科技解说`，Voice ID `cobra_design_20250717_162347_664524`，neutral，速度 1.1。
- 主持人只出现在开头和结尾，插播期间不得出现主持人。
- 现场原声占全部可听内容的目标比例不低于 65%，原声主体至少包含三次有内容的夫妻互动。
- 原声段不叠主持人、不叠替代旁白、不加背景音乐。
- 插播只使用同人物、同主题的中国家庭真实素材，不使用 AI 素材、海外素材或无关夫妻。
- 无字幕、标题、遮罩、项目新增水印、Logo 或来源条。
- 不倒放、不循环、不乒乓播放、不使用静帧填充插播时长。
- 交付主持人口播稿和包含全部现场对话的完整节目文字稿。

---

### Task 1: 初始化独立 V3 运行与创意锁

**Files:**
- Create: `output/manual-news-2026-09-08-wife-value-v03/copy/`
- Create: `output/manual-news-2026-09-08-wife-value-v03/audio/`
- Create: `output/manual-news-2026-09-08-wife-value-v03/media/sources/`
- Create: `output/manual-news-2026-09-08-wife-value-v03/media/approved/`
- Create: `output/manual-news-2026-09-08-wife-value-v03/production/creative-lock.json`
- Create: `output/manual-news-2026-09-08-wife-value-v03/qc/`
- Create: `output/manual-news-2026-09-08-wife-value-v03/video/`
- Create: `output/manual-news-2026-09-08-wife-value-v03/delivery/`

**Interfaces:**
- Consumes: 已批准设计 `docs/superpowers/specs/2026-09-08-wife-value-native-audio-v03-design.md`。
- Produces: V3 独立运行目录及后续全部任务使用的身份、音色、音轨和净版约束。

- [ ] **Step 1: 创建版本安全目录**

Run:

```bash
RUN=output/manual-news-2026-09-08-wife-value-v03
test ! -e "$RUN"
mkdir -p "$RUN"/{copy,audio,media/sources,media/approved,production,qc,video,delivery,research}
```

Expected: 命令退出码为 0，且 V2 文件无变化。

- [ ] **Step 2: 验证主持人锁定资产**

Run:

```bash
shasum -a 256 tmp/host-v12-c2-pro/candidate2.png
```

Expected: 输出以 `939324593eb718cd2a39be4c171f74178a6a48442f7e0d61afe8a875011e8a47` 开头。

- [ ] **Step 3: 写入创意锁并校验 JSON**

`production/creative-lock.json` 必须逐项记录 Global Constraints，并将 `status` 设为 `locked`。

Run:

```bash
python -m json.tool "$RUN/production/creative-lock.json" >/dev/null
```

Expected: JSON 校验通过。

### Task 2: 全网检索并建立真实原声素材账本

**Files:**
- Create: `output/manual-news-2026-09-08-wife-value-v03/research/search-results.json`
- Create: `output/manual-news-2026-09-08-wife-value-v03/production/source-search-report.json`
- Create: `output/manual-news-2026-09-08-wife-value-v03/production/footage-ledger.json`
- Create: `output/manual-news-2026-09-08-wife-value-v03/media/sources/main-native-raw.mp4`
- Create when approved: `output/manual-news-2026-09-08-wife-value-v03/media/sources/supplement-native-raw.mp4`

**Interfaces:**
- Consumes: 已有 `output/manual-news-2026-09-08-wife-value-v02/media/sources/source-native-raw.mp4`，以及公开检索线索 `7654168509741068474`、`7582003346304355621`。
- Produces: 可追溯的候选清单、主原声素材和至多一条同人物补充素材。

- [ ] **Step 1: 复核公开搜索结果**

检索 Bilibili、Bing、抖音、YouTube 和西瓜/好看索引，保存标题、URL、平台、人物一致性、预计时长和访问结果。重点核对：

```text
https://www.douyin.com/video/7654168509741068474
https://www.douyin.com/video/7582003346304355621
https://www.bilibili.com/video/BV13M7J6nEFN/
```

Expected: `research/search-results.json` 至少记录三个平台线索；无法获取的链接明确记录原因，不伪造下载结果。

- [ ] **Step 2: 复制已验证主原片并计算哈希**

Run:

```bash
cp output/manual-news-2026-09-08-wife-value-v02/media/sources/source-native-raw.mp4 "$RUN/media/sources/main-native-raw.mp4"
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$RUN/media/sources/main-native-raw.mp4"
shasum -a 256 "$RUN/media/sources/main-native-raw.mp4"
```

Expected: 时长约 76.736 秒，哈希与 V2 来源文件一致。

- [ ] **Step 3: 只下载通过身份和内容核验的补充原片**

若公开页面能稳定提供同人物原片，使用隔离环境按下列两个已知 URL 分别尝试下载；否则跳过且在报告中记录回退：

```bash
uv run --isolated --python 3.11 --with yt-dlp yt-dlp \
  --no-playlist -f 'bv*+ba/b' --merge-output-format mp4 \
  -o "$RUN/media/sources/douyin-7654168509741068474.%(ext)s" \
  'https://www.douyin.com/video/7654168509741068474'

uv run --isolated --python 3.11 --with yt-dlp yt-dlp \
  --no-playlist -f 'bv*+ba/b' --merge-output-format mp4 \
  -o "$RUN/media/sources/douyin-7582003346304355621.%(ext)s" \
  'https://www.douyin.com/video/7582003346304355621'
```

Expected: 下载文件可完整解码，或报告明确采用 76.7 秒主原片完成 V3。

- [ ] **Step 4: 写入素材账本**

每项记录 `source_url`、`local_path`、`sha256`、人物一致性、是否 AI、是否有字幕/水印/BGM/解说、使用或淘汰理由。

Run:

```bash
python -m json.tool "$RUN/production/footage-ledger.json" >/dev/null
```

Expected: 所有批准素材均为同人物中国家庭真实原声。

### Task 3: 转录原声并选择连续叙事区间

**Files:**
- Create: `output/manual-news-2026-09-08-wife-value-v03/research/main-native-transcript.json`
- Create: `output/manual-news-2026-09-08-wife-value-v03/qc/main-native-contact.jpg`
- Create: `output/manual-news-2026-09-08-wife-value-v03/production/native-dialogue-selection.json`

**Interfaces:**
- Consumes: Task 2 的主原片和可选补充原片。
- Produces: 有时间戳的保守听写、连续动作检查图及批准原声区间。

- [ ] **Step 1: 生成全片接触表**

Run:

```bash
ffmpeg -hide_banner -y -i "$RUN/media/sources/main-native-raw.mp4" \
  -vf 'fps=1/4,scale=270:-2,tile=5x4' -frames:v 1 \
  "$RUN/qc/main-native-contact.jpg"
```

Expected: 覆盖上菜、饭菜特写、两人吃饭和回应过程，无主持人画面。

- [ ] **Step 2: 生成并人工校正带时间戳转录**

使用语音识别获得初稿，再结合原声逐句保守校正；方言或菜名听不清时标注 `[听不清]`，不得猜测。

Expected: 至少标出三次完整夫妻互动及其起止时间。

- [ ] **Step 3: 选择原声主体**

`native-dialogue-selection.json` 按动作和对话完整性选择 60—76 秒连续原声，优先保留：丈夫评价菜品、妻子回应、继续上菜、两人吃饭交流。任何含平台音乐、第三方解说或不可去除字幕的区间必须淘汰。

Expected: 原声段不靠循环扩展，所有区间首尾落在自然停顿或动作节点。

### Task 4: 制作净版原声主体

**Files:**
- Create: `output/manual-news-2026-09-08-wife-value-v03/media/approved/native-story-clean.mp4`
- Create: `output/manual-news-2026-09-08-wife-value-v03/audio/native-story.wav`
- Create: `output/manual-news-2026-09-08-wife-value-v03/qc/native-story-contact.jpg`
- Create: `output/manual-news-2026-09-08-wife-value-v03/production/insert-cleaning.json`

**Interfaces:**
- Consumes: Task 3 批准的源时间窗。
- Produces: 可直接进入节目时间线的 1080×1920 正向净版画面和 48kHz 单声道原声。

- [ ] **Step 1: 中央裁切并拼接批准区间**

以主原片中央竖屏内容为准，使用 `crop`、`scale`、`fps=25`、`setsar=1` 和正向 `concat`；不得使用 `drawbox`、`delogo`、模糊、遮罩、`reverse` 或 `loop`。

Expected: 1080×1920、25fps，来源角标被画面裁切自然移除，人物和菜品主体完整。

- [ ] **Step 2: 提取并标准化原声**

输出 48kHz 单声道 PCM，只做响度和峰值控制，不降噪到破坏人物音色，不添加音乐。

Expected: 平均音量与固定 TTS 相差不超过 3dB，峰值不超过 -1dB。

- [ ] **Step 3: 视觉和音频复核**

Run:

```bash
ffmpeg -v error -i "$RUN/media/approved/native-story-clean.mp4" -f null -
ffmpeg -hide_banner -i "$RUN/media/approved/native-story-clean.mp4" \
  -vf 'freezedetect=n=0.003:d=0.5' -an -f null - 2> "$RUN/qc/native-story-freeze.log"
```

Expected: 无解码错误、无超过 0.5 秒异常冻结、无字幕标题遮罩或主持人。

### Task 5: 写短开场和结尾并生成固定音色 TTS

**Files:**
- Create: `output/manual-news-2026-09-08-wife-value-v03/copy/opening.txt`
- Create: `output/manual-news-2026-09-08-wife-value-v03/copy/closing.txt`
- Create: `output/manual-news-2026-09-08-wife-value-v03/copy/presenter-only-script.txt`
- Create: `output/manual-news-2026-09-08-wife-value-v03/copy/full-program-transcript.txt`
- Create: `output/manual-news-2026-09-08-wife-value-v03/audio/opening.wav`
- Create: `output/manual-news-2026-09-08-wife-value-v03/audio/closing.wav`
- Create: `output/manual-news-2026-09-08-wife-value-v03/production/tts-result.json`
- Create: `output/manual-news-2026-09-08-wife-value-v03/production/script-review.json`

**Interfaces:**
- Consumes: Task 3 的完整现场对话和已批准 V2 结尾观点。
- Produces: 8—10 秒开场、18—25 秒结尾和两段固定音色音频。

- [ ] **Step 1: 写主持人口播**

开场直接提出“一个人在外奔波、一个人把家照顾好，真正值得羡慕的是彼此是否看见”；结尾落到“饭菜是照顾，回应和搭手是珍惜；你心疼我的奔波，我不把你的付出当成理所当然”。

Expected: 不出现“有一个视频”“接下来请看”“看完这段视频”等元转场语言。

- [ ] **Step 2: 用固定音色生成 TTS**

提交参数必须为：

```json
{
  "voice_id": "cobra_design_20250717_162347_664524",
  "emotion": "neutral",
  "speed": 1.1
}
```

Expected: 两段 WAV 均为 48kHz 单声道，开场 8—10 秒，结尾 18—25 秒，尾句完整。

- [ ] **Step 3: 生成双份文字稿**

`presenter-only-script.txt` 只含首尾主持人口播；`full-program-transcript.txt` 逐段包含首尾主持人和全部现场原声。

Expected: 完整节目文字稿覆盖时间线中的每一段可听声音。

### Task 6: 生成固定短发主持人开场和结尾

**Files:**
- Create: `output/manual-news-2026-09-08-wife-value-v03/media/approved/host-opening.mp4`
- Create: `output/manual-news-2026-09-08-wife-value-v03/media/approved/host-closing.mp4`
- Create: `output/manual-news-2026-09-08-wife-value-v03/production/avatar-tasks.json`
- Create: `output/manual-news-2026-09-08-wife-value-v03/qc/opening-drive-alignment.json`
- Create: `output/manual-news-2026-09-08-wife-value-v03/qc/closing-drive-alignment.json`

**Interfaces:**
- Consumes: 锁定主持人图片与 Task 5 的批准音频。
- Produces: Topview Avatar4 音频驱动、无字幕的首尾主持人视频。

- [ ] **Step 1: 提交两段 Avatar4 任务**

使用相同图片、`includeWatermark=0`、`resolution=1080`、`mode=avatar4`，不得替换主持人形象。

Expected: 两个任务均成功，输出画面是同一短发主持人。

- [ ] **Step 2: 下载并完整解码**

Run:

```bash
ffmpeg -v error -i "$RUN/media/approved/host-opening.mp4" -f null -
ffmpeg -v error -i "$RUN/media/approved/host-closing.mp4" -f null -
```

Expected: 无解码错误，画面无字幕标题。

- [ ] **Step 3: 比对驱动音频**

提取两段数字人音轨，与批准 WAV 做 ±40ms 相关性搜索。

Expected: 相关性不低于 0.99，最佳时移不超过 40ms；接触表可见持续自然口型变化。

### Task 7: 构建单一母带和三段视频时间线

**Files:**
- Create: `output/manual-news-2026-09-08-wife-value-v03/audio/master-voiceover.wav`
- Create: `output/manual-news-2026-09-08-wife-value-v03/production/audio-assembly.json`
- Create: `output/manual-news-2026-09-08-wife-value-v03/production/timeline.json`
- Create: `output/manual-news-2026-09-08-wife-value-v03/production/program-transcript.json`

**Interfaces:**
- Consumes: Task 4 原声主体、Task 5 首尾 TTS、Task 6 主持人视频。
- Produces: 无混音的单一节目母带与严格首尾相接的三段时间线。

- [ ] **Step 1: 顺序拼接音频**

顺序必须是 `opening.wav → native-story.wav → closing.wav`，统一为 48kHz 单声道 PCM。不得使用 `amix`。

Expected: 母带时长等于三段时长之和，现场原声区间内只有 `native-story.wav`。

- [ ] **Step 2: 写入时间线和完整节目台词**

三个区间必须首尾相接；现场原声占比按 `native_duration / total_duration` 计算并记录。

Expected: 占比不低于 65%，原声说话人与文字逐段对应。

### Task 8: 合成 9:16 无字净版成片

**Files:**
- Create: `output/manual-news-2026-09-08-wife-value-v03/production/render.sh`
- Create: `output/manual-news-2026-09-08-wife-value-v03/video/final-clean.mp4`

**Interfaces:**
- Consumes: Task 4 原声画面、Task 6 首尾主持人画面、Task 7 单一母带。
- Produces: 最终 1080×1920 新闻视频。

- [ ] **Step 1: 写安全合成脚本**

脚本只拼接三段视频画面并映射 `audio/master-voiceover.wav`；不得直接映射任一素材音轨，不使用 `-y` 覆盖成片。

Expected: 滤镜链只包含 `fps`、`trim/tpad`、`setpts`、`scale/crop`、`setsar`、`format` 和正向 `concat`。

- [ ] **Step 2: 渲染成片**

Run:

```bash
"$RUN/production/render.sh"
```

Expected: 输出 H.264 High yuv420p、1080×1920、25fps、AAC LC 48kHz 单声道。

### Task 9: 自动 QC、导演审核和交付打包

**Files:**
- Create: `output/manual-news-2026-09-08-wife-value-v03/qc/ffprobe.json`
- Create: `output/manual-news-2026-09-08-wife-value-v03/qc/audio-comparison.json`
- Create: `output/manual-news-2026-09-08-wife-value-v03/qc/contact-sheet.jpg`
- Create: `output/manual-news-2026-09-08-wife-value-v03/qc/boundary-contact.jpg`
- Create: `output/manual-news-2026-09-08-wife-value-v03/qc/tail-contact.jpg`
- Create: `output/manual-news-2026-09-08-wife-value-v03/qc/final-qc-report.json`
- Create: `output/manual-news-2026-09-08-wife-value-v03/qc/director-review.json`
- Create: `output/manual-news-2026-09-08-wife-value-v03/qc/sha256.txt`
- Create: `output/manual-news-2026-09-08-wife-value-v03/production/delivery-manifest.json`
- Create: `output/manual-news-2026-09-08-wife-value-v03/delivery/manual-news-2026-09-08-wife-value-v03-delivery.zip`

**Interfaces:**
- Consumes: Task 8 最终成片及全部批准生产记录。
- Produces: 自动 QC、两遍导演审核、可校验交付包。

- [ ] **Step 1: 运行技术 QC**

Run:

```bash
ffprobe -v error -show_streams -show_format -of json "$RUN/video/final-clean.mp4" > "$RUN/qc/ffprobe.json"
ffmpeg -v error -i "$RUN/video/final-clean.mp4" -f null - 2> "$RUN/qc/decode-errors.log"
ffmpeg -hide_banner -i "$RUN/video/final-clean.mp4" -vf 'blackdetect=d=0.2:pix_th=0.10' -an -f null - 2> "$RUN/qc/blackdetect.log"
ffmpeg -hide_banner -i "$RUN/video/final-clean.mp4" -vf 'freezedetect=n=0.003:d=0.5' -an -f null - 2> "$RUN/qc/freezedetect.log"
ffmpeg -hide_banner -i "$RUN/video/final-clean.mp4" -af 'silencedetect=noise=-45dB:d=1.0' -vn -f null - 2> "$RUN/qc/silencedetect.log"
```

Expected: 无解码错误、黑帧、异常冻结或超过 1 秒的非自然静音。

- [ ] **Step 2: 验证整片及三段音频互斥**

最终 AAC 解码后与母带比较；首尾分别与固定 TTS 比较；中段与 `native-story.wav` 比较。

Expected: 所有相关性不低于 0.99，最佳时移不超过 40ms，中段不存在主持人 TTS。

- [ ] **Step 3: 完成两遍导演审核**

第一遍检查主持人身份、五官、口型、脚本、人物和素材相关性；第二遍检查剪辑节奏、无字净版、无倒放循环、结尾完整和整体新闻效果。

Expected: 十项导演 ID 全部通过，原声占比不低于 65%，至少三次自然夫妻互动。

- [ ] **Step 4: 生成哈希和 ZIP**

交付包至少包含最终 MP4、母带、批准原声主体、主持人口播稿、完整节目文字稿、时间线、素材账本、QC 报告、导演审核和 SHA-256。

Expected: `shasum -a 256 -c` 全部通过，`unzip -t` 报告无错误，运行状态为 `ready_to_deliver`。
