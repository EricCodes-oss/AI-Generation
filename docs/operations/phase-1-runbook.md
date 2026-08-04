# Phase 1 本地运行手册

## 1. 阶段目标

Phase 1 只建立每天一条数字人视频所需的本地任务编排基础：配置校验、Top 3 选题导入、三个人工审批点、状态流转、JSON 归档以及外部 Skill 契约检查。

本阶段**不会调用**真实 TTS、数字人或 Seedance 服务，也不会消耗生成额度。三个契约当前均设置为 `real_generation_enabled: false`。

## 2. 安装

要求：

- Python 3.11 或更高版本
- FFmpeg 与 ffprobe

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

验证安装：

```bash
avatar-pipeline health
```

健康检查 JSON 中应满足：

- `python.available` 为 `true`
- `ffmpeg.available` 为 `true`
- `skills.avatar.real_generation_enabled` 为 `false`
- `skills.tts.real_generation_enabled` 为 `false`
- `skills.seedance.real_generation_enabled` 为 `false`

## 3. 初始化每日任务

系统每天只创建一条任务。以下示例使用 2026 年 8 月 4 日：

```bash
avatar-pipeline init-day --date 2026-08-04
```

如需指定独立任务目录：

```bash
avatar-pipeline --workspace /tmp/avatar-workspace init-day --date 2026-08-04
```

任务文件固定保存在：

```text
<workspace>/days/YYYY-MM-DD/task.json
```

默认工作区来自 `configs/default.yaml`，即项目下的 `workspace/`。该目录已被 Git 忽略。

## 4. 导入每日 Top 3

候选文件既可以直接是包含三个对象的 JSON 数组，也可以是含 `candidates` 数组的对象。每个候选至少需要以下字段：

```json
[
  {
    "id": "t1",
    "title": "工作受挫后，先别急着否定自己",
    "pillar": "career_pressure",
    "score": 94
  },
  {
    "id": "t2",
    "title": "和孩子沟通前，父母先稳住情绪",
    "pillar": "parent_child_communication",
    "score": 91
  },
  {
    "id": "t3",
    "title": "停止用别人的节奏否定自己",
    "pillar": "self_growth",
    "score": 89
  }
]
```

可选字段包括目标受众、具体场景、痛点、趋势证据、推荐理由、开头钩子、情绪、风险和来源编号。完整示例见 `tests/fixtures/top_topics.json`。

导入命令：

```bash
avatar-pipeline import-topics \
  --date 2026-08-04 \
  --file tests/fixtures/top_topics.json
```

系统强制要求恰好三个候选，候选 ID 必须唯一。

## 5. 三个人工审批点

### 审批点一：选择 Top 1 选题

```bash
avatar-pipeline approve-topic \
  --date 2026-08-04 \
  --topic-id t1 \
  --actor owner
```

只能从当天 Top 3 中选择。

### 审批点二：确认脚本

先把脚本文本保存为 UTF-8 文件，例如 `script.txt`：

```bash
avatar-pipeline record-script --date 2026-08-04 --file script.txt
avatar-pipeline approve-script --date 2026-08-04 --actor owner
```

当前 CLI 暴露到审批与 QC 环节；TTS、数字人、Seedance 以及合成调用将在其 Skill 接口经过核验后接入。服务层已经预留 `audio_ready`、`assets_generating` 与 `compositing` 状态。

### 审批点三：确认成片

完成外部资产与合成流程后记录 QC：

```bash
avatar-pipeline record-qc \
  --date 2026-08-04 \
  --passed true \
  --report qc/report.json

avatar-pipeline approve-video --date 2026-08-04 --actor owner
```

`approve-video` 只接受已经进入 `qc_passed` 状态的任务，不能跳过选题或脚本审批。

## 6. 查看任务状态

```bash
avatar-pipeline status --date 2026-08-04
```

输出为 UTF-8 JSON，包含候选、选中选题、脚本、审批记录、产物记录、当前状态和时间戳。

## 7. 状态主路径

```text
created
→ researched
→ topic_approved
→ script_draft
→ script_approved
→ audio_ready
→ assets_generating
→ compositing
→ qc_passed
→ video_approved
```

若 QC 失败：

```text
compositing → qc_failed → assets_generating 或 compositing
```

## 8. 常见错误

### `daily task already exists`

同一天只能创建一个任务。使用 `status` 查看已有任务，或换用正确日期/工作区。

### `daily task not found`

对应日期尚未初始化，先执行 `init-day`，并确认所有命令使用相同的 `--workspace`。

### `not in Top 3`

审批的 `topic-id` 不属于当天导入的三个候选。先执行 `status` 查看候选 ID。

### `expected ...`

当前任务状态不允许执行该操作，说明试图跳过了流程步骤或人工审批点。根据 `status` 的状态按顺序继续。

### FFmpeg 健康检查失败

确认终端中 `ffmpeg` 与 `ffprobe` 均可执行并位于 `PATH`：

```bash
ffmpeg -version
ffprobe -version
```

### Skill 契约缺失或非法

检查 `skills/contracts/` 下是否同时存在 `avatar.yaml`、`tts.yaml` 与 `seedance.yaml`。Phase 1 不应把任何契约的 `real_generation_enabled` 改为 `true`。

## 9. 本地验收

```bash
python -m pytest -q
python -m pytest --cov=avatar_pipeline --cov-report=term-missing
python -m ruff check src tests
git diff --check
avatar-pipeline health
```

只有在用户提供数字人和 Seedance Skill、并完成输入输出接口核验后，才进入真实生成能力接入阶段。
