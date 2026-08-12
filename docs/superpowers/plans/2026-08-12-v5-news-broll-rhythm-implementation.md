# V5 News B-roll Rhythm Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于已获认可的V4，制作一版仅优化现场插播节奏的V5：全片3次插播，每次5—6秒，最后12.128秒连续保留主持人。

**Architecture:** V5使用独立输出目录，不覆盖V4。渲染继续以V4数字人原片和52.128秒“未来科技解说”主音频为时间基准，通过FFmpeg对主持人和3段正向连续B-roll进行裁切、统一为1080×1920/25fps后拼接，最终执行媒体属性、黑帧、静音、解码、首尾画面、时间线和哈希质检。

**Tech Stack:** Bash、FFmpeg、ffprobe、Python 3、JSON、SHA-256。

## Global Constraints

- 总时长严格为52.128秒，允许封装/帧率取整产生不超过1帧（0.04秒）的容器差异。
- 只使用C2-Pro候选2短发主持人，不重新生成数字人。
- 只使用现有“未来科技解说”音频，不改稿、不改语速、不加背景音乐。
- 全片恰好3次插播，目标时长分别为5.0、6.0、5.5秒。
- 40.000秒后连续保留主持人至52.128秒。
- 无字幕、标题、台标、资料条和新增水印。
- 插播素材原声全部弃用。
- 禁止倒放、循环、ping-pong、重复素材填时。
- B站素材仍为需确认授权，成片只标记“待授权内部预览版”。
- V4目录及成片不得修改。

---

### Task 1: 建立V5制作目录并核验输入资产

**Files:**
- Create: `output/manual-run-2026-08-12-v5/audio/master-voiceover-future-tech-v5.wav`
- Create: `output/manual-run-2026-08-12-v5/video/anchor-c2-pro-short-hair-v5-raw.mp4`
- Create: `output/manual-run-2026-08-12-v5/media/candidates/*`
- Create: `output/manual-run-2026-08-12-v5/production/input-validation.json`

**Interfaces:**
- Consumes: V4数字人、音频和三个候选素材文件。
- Produces: V5独立输入资产及包含文件大小、时长、分辨率、帧率、音频属性和SHA-256的核验记录。

- [ ] **Step 1: 创建V5目录结构**

Run:
```bash
mkdir -p output/manual-run-2026-08-12-v5/{audio,video,media/candidates,production,qc}
```
Expected: 五个制作子目录存在，V4不变。

- [ ] **Step 2: 复制并重命名输入资产**

复制V4主持人、主音频、Pexels强风素材和武汉积水素材到V5；同一武汉文件供插播2和插播3使用。

- [ ] **Step 3: 使用ffprobe和sha256核验输入**

Expected:
- 音频约52.128秒、48kHz、单声道；
- 主持人原片约52秒；
- 所有B-roll源时长足以覆盖目标裁切区间；
- 核验结果写入`production/input-validation.json`。

### Task 2: 精选三个连续镜头并建立镜头证据

**Files:**
- Create: `output/manual-run-2026-08-12-v5/qc/source-wind-contact-sheet.jpg`
- Create: `output/manual-run-2026-08-12-v5/qc/source-flood-opening-contact-sheet.jpg`
- Create: `output/manual-run-2026-08-12-v5/qc/source-flood-driving-contact-sheet.jpg`
- Create: `output/manual-run-2026-08-12-v5/production/shot-selection-v5.json`

**Interfaces:**
- Consumes: Task 1核验后的两个B-roll源文件。
- Produces: 3个明确源时间段及其内容、动作完整性和使用理由。

- [ ] **Step 1: 生成强风素材0—7秒接触表**

Expected: 可逐秒检查棕榈树风力动作，选择一个约5秒连续区间。

- [ ] **Step 2: 生成武汉素材开头0—8秒接触表**

Expected: 选择约6秒能够建立城市积水范围的连续区间。

- [ ] **Step 3: 生成武汉素材28—38秒接触表**

Expected: 选择约5.5秒车辆涉水动作完整且没有倒放/镜头跳跃的连续区间。

- [ ] **Step 4: 写入镜头选择JSON并核对时长算术**

Expected: 三段源时长与目标时长分别一致，合计16.5秒。

### Task 3: 创建V5时间线、版权台账和渲染脚本

**Files:**
- Create: `output/manual-run-2026-08-12-v5/production/timeline-v5.json`
- Create: `output/manual-run-2026-08-12-v5/production/footage-rights-ledger.json`
- Create: `output/manual-run-2026-08-12-v5/production/render-v5.sh`

**Interfaces:**
- Consumes: Task 2的`shot-selection-v5.json`。
- Produces: 7段成片时间线和可重复执行的FFmpeg渲染命令。

- [ ] **Step 1: 写入7段时间线**

Exact sequence:
```text
anchor 0.000–6.500
broll 6.500–11.500
anchor 11.500–19.000
broll 19.000–25.000
anchor 25.000–34.500
broll 34.500–40.000
anchor 40.000–52.128
```

- [ ] **Step 2: 写入版权台账**

Expected: Pexels记录许可；武汉素材记录`approved_for_release: false`、`preview_use_only: true`。

- [ ] **Step 3: 创建FFmpeg渲染脚本**

Expected:
- 主持人分为4段；
- B-roll分为3段；
- 7段concat；
- 仅映射独立主音频；
- 不包含任何reverse/loop相关滤镜；
- 输出H.264 High、AAC 192kbps、48kHz单声道、faststart。

- [ ] **Step 4: 静态检查时间线和脚本**

Run Python assertions validating segment continuity, exact count, exact B-roll durations, total duration and forbidden filter strings.
Expected: all assertions pass。

### Task 4: 渲染V5成片

**Files:**
- Create: `output/manual-run-2026-08-12-v5/video/白海豚-北方强降雨-新闻口播-无字净版-v5.mp4`

**Interfaces:**
- Consumes: Task 3渲染脚本和V5输入资产。
- Produces: V5待授权内部预览成片。

- [ ] **Step 1: 执行渲染脚本**

Run:
```bash
bash output/manual-run-2026-08-12-v5/production/render-v5.sh
```
Expected: ffmpeg exit 0，生成非空MP4。

- [ ] **Step 2: 基础播放属性核验**

Expected: 1080×1920、25fps、约52.128秒、1条视频流、1条AAC单声道音频流。

### Task 5: 执行完整技术与导演QC

**Files:**
- Create: `output/manual-run-2026-08-12-v5/qc/final-v5-ffprobe.json`
- Create: `output/manual-run-2026-08-12-v5/qc/final-v5-blackdetect.log`
- Create: `output/manual-run-2026-08-12-v5/qc/final-v5-silencedetect.log`
- Create: `output/manual-run-2026-08-12-v5/qc/final-v5-decode-errors.log`
- Create: `output/manual-run-2026-08-12-v5/qc/final-v5-contact-sheet.jpg`
- Create: `output/manual-run-2026-08-12-v5/qc/final-v5-tail-contact.jpg`
- Create: `output/manual-run-2026-08-12-v5/qc/final-v5-audio-tail.wav`
- Create: `output/manual-run-2026-08-12-v5/qc/final-v5-sha256.txt`
- Create: `output/manual-run-2026-08-12-v5/qc/final-v5-qc-report.json`

**Interfaces:**
- Consumes: Task 4成片和Task 3时间线。
- Produces: 可验证成片技术质量和导演规则的完整QC证据。

- [ ] **Step 1: 运行ffprobe并验证流属性**

Expected: 视频和音频属性满足Global Constraints。

- [ ] **Step 2: 检查黑帧、静音和解码错误**

Expected:
- 无意外黑帧；
- 中途无异常长静音；
- 解码错误日志为空；
- 仅允许音频末尾约0.28秒自然静音。

- [ ] **Step 3: 生成全片和尾部接触表**

Expected:
- 清楚看到3次而非6次插播；
- 40秒后持续为同一短发主持人；
- 无意外字幕、倒放迹象或黑画面。

- [ ] **Step 4: 导出最后4秒音频并检查完整收尾**

Expected: 音频尾部与主音频一致，最后有效人声后保留自然静音，不截词。

- [ ] **Step 5: 生成SHA-256和QC报告**

Expected: 报告逐项记录PASS/FAIL、成片路径、权限状态、3段插播时长及最终哈希。

### Task 6: 最终复核并提交制作元数据

**Files:**
- Modify: `docs/superpowers/plans/2026-08-12-v5-news-broll-rhythm-implementation.md`
- Add: V5 `production/*.json`、`production/render-v5.sh`和`qc/final-v5-qc-report.json`（若仓库策略允许跟踪输出元数据；大体积媒体不纳入Git）。

**Interfaces:**
- Consumes: Task 5全部QC结果。
- Produces: 经证据支持的交付说明和可复现制作记录。

- [ ] **Step 1: 按设计文档逐项复核10条验收标准**

Expected: 所有要求有对应文件或命令输出证明。

- [ ] **Step 2: 确认V4哈希未因本次工作变化**

Expected: V4现有成片保持不变。

- [ ] **Step 3: 提交可追踪的小型制作元数据**

Commit message:
```text
chore: record v5 news b-roll rhythm production
```

- [ ] **Step 4: 向用户交付V5**

交付内容：成片绝对路径、时长/规格、3段插播时间、QC报告路径、SHA-256及“待授权内部预览版”说明。
