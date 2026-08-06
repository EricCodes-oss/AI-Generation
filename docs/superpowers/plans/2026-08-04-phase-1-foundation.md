# Phase 1 项目基础与每日任务编排 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 建立可安装、可测试的 Python 项目骨架，使每日视频任务具备配置、领域数据、状态流转、人工审批、文件归档和外部 Skill 契约。

**Architecture:** 使用 `src/` 布局的 Python 包。Pydantic 模型负责数据校验，JSON 文件仓库负责 V1 持久化，显式状态机阻止越级操作，`argparse` CLI 暴露初始化、导入候选、审批和状态查询命令。外部 TTS、数字人和 Seedance 能力只定义协议与 manifest 校验，不在 Phase 1 发起真实生成。

**Tech Stack:** Python 3.11+、Pydantic 2、PyYAML、pytest、Ruff、标准库 argparse/pathlib/json、FFmpeg 7+（仅健康检查）。

## Global Constraints

- 每天只生产 1 条 35–50 秒视频，同一成片发布抖音、视频号和小红书。
- 输出规格固定为 9:16、1080×1920、无平台水印。
- 第一阶段内容仅包含职场打拼与现实压力、子女教育与家庭沟通、自我成长与人生感悟。
- “父母养老与照护压力”不进入 V1。
- 选题、脚本、成片必须经过三个人工确认点。
- 独立 TTS 音频是最终主音轨；图片 + TTS 生成数字人视频是主模式。
- 外部生成 Skill 在能力核验前不得发起真实生成。
- 所有运行产物写入 `workspace/`，该目录不得提交 Git。

---

## 文件结构

```text
pyproject.toml                         构建、依赖、CLI 和测试配置
README.md                              本地安装与 Phase 1 使用说明
.gitignore                             忽略虚拟环境、缓存和 workspace 产物
configs/default.yaml                   固定视频规格、栏目比例和审批配置
src/avatar_pipeline/__init__.py        包版本
src/avatar_pipeline/config.py          YAML 配置加载与校验
src/avatar_pipeline/models.py          选题、审批、产物、每日任务模型
src/avatar_pipeline/state.py           合法状态转移规则
src/avatar_pipeline/repository.py      JSON 文件仓库和原子写入
src/avatar_pipeline/skill_contracts.py 外部 Skill manifest 与协议
src/avatar_pipeline/service.py         每日任务应用服务
src/avatar_pipeline/cli.py             argparse 命令行入口
skills/contracts/avatar.yaml           数字人 Skill 所需接口契约
skills/contracts/tts.yaml              TTS Skill 所需接口契约
skills/contracts/seedance.yaml         Seedance 2.0 Skill 所需接口契约
tests/test_config.py                   配置测试
tests/test_models.py                   领域模型测试
tests/test_state.py                    状态机测试
tests/test_repository.py               持久化测试
tests/test_skill_contracts.py          Skill 契约测试
tests/test_service.py                  人工审批工作流测试
tests/test_cli.py                      CLI 集成测试
```

### Task 1：项目包装、默认配置与健康检查

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `README.md`
- Create: `configs/default.yaml`
- Create: `src/avatar_pipeline/__init__.py`
- Create: `src/avatar_pipeline/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: 无。
- Produces: `AppConfig`、`load_config(path: Path) -> AppConfig`、CLI 包入口所需项目元数据。

- [x] **Step 1: 编写失败的配置测试**

```python
from pathlib import Path

from avatar_pipeline.config import load_config


def test_default_config_locks_v1_video_and_content_constraints():
    config = load_config(Path("configs/default.yaml"))

    assert config.video.width == 1080
    assert config.video.height == 1920
    assert config.video.min_duration_seconds == 35
    assert config.video.max_duration_seconds == 50
    assert config.video.avatar_ratio_min == 0.55
    assert config.video.avatar_ratio_max == 0.65
    assert [pillar.slug for pillar in config.content.pillars] == [
        "career_pressure",
        "parent_child_communication",
        "self_growth",
    ]
    assert sum(pillar.monthly_count for pillar in config.content.pillars) == 30
    assert config.approvals.required == ["topic", "script", "video"]
```

- [x] **Step 2: 运行测试并确认因模块不存在而失败**

Run: `python -m pytest tests/test_config.py -v`

Expected: FAIL，错误包含 `ModuleNotFoundError: No module named 'avatar_pipeline'`。

- [x] **Step 3: 创建项目配置和最小实现**

`pyproject.toml` 必须声明 Python `>=3.11`、依赖 `pydantic>=2.10,<3` 与 `PyYAML>=6,<7`、开发依赖 pytest/Ruff，并注册 `avatar-pipeline = "avatar_pipeline.cli:main"`。`configs/default.yaml` 必须写入测试中的固定值和三个栏目月度数量 `11/9/10`。`config.py` 使用 Pydantic `BaseModel` 定义 `VideoConfig`、`ContentPillar`、`ContentConfig`、`ApprovalConfig`、`StorageConfig` 和 `AppConfig`，并由 `yaml.safe_load` 加载。

核心函数签名：

```python
def load_config(path: Path) -> AppConfig:
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return AppConfig.model_validate(raw)
```

`.gitignore` 至少包含 `.venv/`、`__pycache__/`、`.pytest_cache/`、`.ruff_cache/`、`*.pyc`、`workspace/`。README 写明创建虚拟环境、`pip install -e '.[dev]'` 和运行测试的命令。

- [x] **Step 4: 安装开发依赖并运行测试**

Run: `python -m pip install -e '.[dev]' && python -m pytest tests/test_config.py -v`

Expected: `1 passed`。

- [x] **Step 5: 运行 Ruff**

Run: `python -m ruff check src tests`

Expected: `All checks passed!`

- [x] **Step 6: 提交**

```bash
git add pyproject.toml .gitignore README.md configs src/avatar_pipeline/__init__.py src/avatar_pipeline/config.py tests/test_config.py
git commit -m "build: scaffold avatar pipeline project"
```

### Task 2：领域模型与数据约束

**Files:**
- Create: `src/avatar_pipeline/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Consumes: `AppConfig` 中的概念约束。
- Produces: `ContentPillarSlug`、`TaskStatus`、`TopicCandidate`、`ApprovalRecord`、`ArtifactRecord`、`DailyTask`。

- [x] **Step 1: 编写失败的模型测试**

```python
from datetime import date

import pytest
from pydantic import ValidationError

from avatar_pipeline.models import DailyTask, TaskStatus, TopicCandidate


def test_daily_task_accepts_exactly_three_ranked_candidates():
    candidates = [
        TopicCandidate(
            id=f"topic-{index}", title=f"候选 {index}", pillar="self_growth", score=90 - index
        )
        for index in range(1, 4)
    ]
    task = DailyTask(day=date(2026, 8, 4), status=TaskStatus.RESEARCHED, candidates=candidates)
    assert len(task.candidates) == 3


def test_daily_task_rejects_duplicate_candidate_ids():
    candidates = [
        TopicCandidate(id="same", title="A", pillar="self_growth", score=90),
        TopicCandidate(id="same", title="B", pillar="career_pressure", score=89),
        TopicCandidate(id="third", title="C", pillar="parent_child_communication", score=88),
    ]
    with pytest.raises(ValidationError, match="candidate ids must be unique"):
        DailyTask(day=date(2026, 8, 4), status=TaskStatus.RESEARCHED, candidates=candidates)


def test_retirement_care_is_not_a_valid_v1_pillar():
    with pytest.raises(ValidationError):
        TopicCandidate(id="bad", title="养老", pillar="eldercare", score=90)
```

- [x] **Step 2: 运行测试并确认失败**

Run: `python -m pytest tests/test_models.py -v`

Expected: FAIL，错误包含 `No module named 'avatar_pipeline.models'`。

- [x] **Step 3: 实现模型**

实现以下枚举值：

```python
class ContentPillarSlug(StrEnum):
    CAREER_PRESSURE = "career_pressure"
    PARENT_CHILD_COMMUNICATION = "parent_child_communication"
    SELF_GROWTH = "self_growth"


class TaskStatus(StrEnum):
    CREATED = "created"
    RESEARCHED = "researched"
    TOPIC_APPROVED = "topic_approved"
    SCRIPT_DRAFT = "script_draft"
    SCRIPT_APPROVED = "script_approved"
    AUDIO_READY = "audio_ready"
    ASSETS_GENERATING = "assets_generating"
    COMPOSITING = "compositing"
    QC_FAILED = "qc_failed"
    QC_PASSED = "qc_passed"
    VIDEO_APPROVED = "video_approved"
    PUBLISHED = "published"
    ANALYZED = "analyzed"
```

`TopicCandidate.score` 限制为 0–100。`DailyTask` 包含 `day`、`status`、`candidates`、`selected_topic_id`、`script_text`、`approvals`、`artifacts`、`created_at`、`updated_at`；当候选非空时必须恰好 3 个且 ID 唯一。

- [x] **Step 4: 运行模型测试**

Run: `python -m pytest tests/test_models.py -v`

Expected: `3 passed`。

- [x] **Step 5: 运行全部现有测试与 Ruff**

Run: `python -m pytest -q && python -m ruff check src tests`

Expected: 所有测试通过，Ruff 无错误。

- [x] **Step 6: 提交**

```bash
git add src/avatar_pipeline/models.py tests/test_models.py
git commit -m "feat: add daily task domain models"
```

### Task 3：任务状态机与三个人工确认门

**Files:**
- Create: `src/avatar_pipeline/state.py`
- Test: `tests/test_state.py`

**Interfaces:**
- Consumes: `TaskStatus`。
- Produces: `allowed_targets(status: TaskStatus) -> frozenset[TaskStatus]`、`ensure_transition(current, target) -> None`、`approval_gate_for(target) -> str | None`。

- [x] **Step 1: 编写失败的状态机测试**

```python
import pytest

from avatar_pipeline.models import TaskStatus
from avatar_pipeline.state import InvalidTransitionError, approval_gate_for, ensure_transition


def test_happy_path_transitions_are_allowed():
    ensure_transition(TaskStatus.RESEARCHED, TaskStatus.TOPIC_APPROVED)
    ensure_transition(TaskStatus.SCRIPT_DRAFT, TaskStatus.SCRIPT_APPROVED)
    ensure_transition(TaskStatus.QC_PASSED, TaskStatus.VIDEO_APPROVED)


def test_skipping_script_approval_is_rejected():
    with pytest.raises(InvalidTransitionError, match="script_draft -> audio_ready"):
        ensure_transition(TaskStatus.SCRIPT_DRAFT, TaskStatus.AUDIO_READY)


def test_manual_gate_names_are_explicit():
    assert approval_gate_for(TaskStatus.TOPIC_APPROVED) == "topic"
    assert approval_gate_for(TaskStatus.SCRIPT_APPROVED) == "script"
    assert approval_gate_for(TaskStatus.VIDEO_APPROVED) == "video"
```

- [x] **Step 2: 运行测试并确认失败**

Run: `python -m pytest tests/test_state.py -v`

Expected: FAIL，错误包含 `No module named 'avatar_pipeline.state'`。

- [x] **Step 3: 实现显式转移表**

转移表必须允许：

```text
created -> researched
researched -> topic_approved
topic_approved -> script_draft
script_draft -> script_approved
script_approved -> audio_ready
audio_ready -> assets_generating
assets_generating -> compositing
compositing -> qc_failed | qc_passed
qc_failed -> assets_generating | compositing
qc_passed -> video_approved
video_approved -> published
published -> analyzed
```

`ensure_transition` 在非法转移时抛出 `InvalidTransitionError`，错误文本包含小写状态箭头。

- [x] **Step 4: 运行状态机测试**

Run: `python -m pytest tests/test_state.py -v`

Expected: `3 passed`。

- [x] **Step 5: 运行全部测试并提交**

```bash
python -m pytest -q
python -m ruff check src tests
git add src/avatar_pipeline/state.py tests/test_state.py
git commit -m "feat: enforce daily workflow state machine"
```

### Task 4：JSON 文件仓库与原子写入

**Files:**
- Create: `src/avatar_pipeline/repository.py`
- Test: `tests/test_repository.py`

**Interfaces:**
- Consumes: `DailyTask`。
- Produces: `DailyTaskRepository(root: Path)`、`create(task)`、`get(day)`、`save(task)`、`list_days()`。

- [x] **Step 1: 编写失败的仓库测试**

```python
from datetime import date

import pytest

from avatar_pipeline.models import DailyTask
from avatar_pipeline.repository import (
    DailyTaskAlreadyExists,
    DailyTaskNotFound,
    DailyTaskRepository,
)


def test_repository_round_trips_utf8_json(tmp_path):
    repo = DailyTaskRepository(tmp_path)
    task = DailyTask(day=date(2026, 8, 4))
    repo.create(task)
    loaded = repo.get(date(2026, 8, 4))
    assert loaded.day == task.day
    assert (tmp_path / "days" / "2026-08-04" / "task.json").exists()


def test_repository_rejects_duplicate_day(tmp_path):
    repo = DailyTaskRepository(tmp_path)
    repo.create(DailyTask(day=date(2026, 8, 4)))
    with pytest.raises(DailyTaskAlreadyExists):
        repo.create(DailyTask(day=date(2026, 8, 4)))


def test_repository_reports_missing_day(tmp_path):
    with pytest.raises(DailyTaskNotFound):
        DailyTaskRepository(tmp_path).get(date(2026, 8, 4))
```

- [x] **Step 2: 运行测试并确认失败**

Run: `python -m pytest tests/test_repository.py -v`

Expected: FAIL，错误包含 `No module named 'avatar_pipeline.repository'`。

- [x] **Step 3: 实现仓库**

任务文件固定为 `<root>/days/YYYY-MM-DD/task.json`。保存时先写同目录临时文件，再使用 `Path.replace` 原子替换。JSON 使用 `model_dump(mode="json")`、UTF-8、`ensure_ascii=False`、两空格缩进。`save` 必须更新时间戳。

- [x] **Step 4: 运行仓库测试**

Run: `python -m pytest tests/test_repository.py -v`

Expected: `3 passed`。

- [x] **Step 5: 运行全部测试并提交**

```bash
python -m pytest -q
python -m ruff check src tests
git add src/avatar_pipeline/repository.py tests/test_repository.py
git commit -m "feat: persist daily tasks as atomic json"
```

### Task 5：外部 Skill 契约与 manifest 校验

**Files:**
- Create: `src/avatar_pipeline/skill_contracts.py`
- Create: `skills/contracts/avatar.yaml`
- Create: `skills/contracts/tts.yaml`
- Create: `skills/contracts/seedance.yaml`
- Test: `tests/test_skill_contracts.py`

**Interfaces:**
- Consumes: YAML 文件。
- Produces: `SkillKind`、`SkillManifest`、`load_skill_manifest(path)`、`load_contracts(directory)`。

- [x] **Step 1: 编写失败的契约测试**

```python
from pathlib import Path

from avatar_pipeline.skill_contracts import SkillKind, load_contracts


def test_required_external_skill_contracts_are_declared():
    contracts = load_contracts(Path("skills/contracts"))
    assert set(contracts) == {SkillKind.TTS, SkillKind.AVATAR, SkillKind.SEEDANCE}
    assert contracts[SkillKind.AVATAR].primary_mode == "image_plus_audio"
    assert contracts[SkillKind.AVATAR].fallback_mode == "image_plus_text"
    assert contracts[SkillKind.SEEDANCE].required_outputs == ["video_path", "task_id"]
    assert contracts[SkillKind.TTS].real_generation_enabled is False
```

- [x] **Step 2: 运行测试并确认失败**

Run: `python -m pytest tests/test_skill_contracts.py -v`

Expected: FAIL，错误包含 `No module named 'avatar_pipeline.skill_contracts'`。

- [x] **Step 3: 实现 manifest 模型与三份契约**

`SkillKind` 值为 `tts/avatar/seedance`。每份 YAML 必须声明：`kind`、`contract_version: "1.0"`、`display_name`、`required_inputs`、`required_outputs`、`supported_aspect_ratios`、`max_duration_seconds`、`real_generation_enabled: false`。Avatar 额外声明主/备用模式；TTS 声明推荐输出 WAV 和时间戳；Seedance 声明竖屏视频、任务 ID、提示词与可选参考图输入。

`load_contracts` 对 kind 重复、契约缺失或非法字段抛出 Pydantic `ValidationError` 或 `ValueError`。

- [x] **Step 4: 运行契约测试**

Run: `python -m pytest tests/test_skill_contracts.py -v`

Expected: `1 passed`。

- [x] **Step 5: 运行全部测试并提交**

```bash
python -m pytest -q
python -m ruff check src tests
git add src/avatar_pipeline/skill_contracts.py skills/contracts tests/test_skill_contracts.py
git commit -m "feat: define external generation skill contracts"
```

### Task 6：每日任务服务与人工审批

**Files:**
- Create: `src/avatar_pipeline/service.py`
- Test: `tests/test_service.py`

**Interfaces:**
- Consumes: `DailyTaskRepository`、领域模型和状态机。
- Produces: `DailyWorkflowService` 的 `start_day`、`record_research`、`approve_topic`、`record_script`、`approve_script`、`record_qc`、`approve_video`。

- [x] **Step 1: 编写失败的服务测试**

```python
from datetime import date

import pytest

from avatar_pipeline.models import TaskStatus, TopicCandidate
from avatar_pipeline.repository import DailyTaskRepository
from avatar_pipeline.service import DailyWorkflowService, WorkflowPreconditionError


def candidates():
    return [
        TopicCandidate(id="t1", title="工作受挫后", pillar="career_pressure", score=94),
        TopicCandidate(
            id="t2", title="父母先稳住情绪", pillar="parent_child_communication", score=91
        ),
        TopicCandidate(id="t3", title="停止自我否定", pillar="self_growth", score=89),
    ]


def test_three_manual_approvals_are_recorded(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 4)
    service.start_day(day)
    service.record_research(day, candidates())
    service.approve_topic(day, "t1", actor="owner")
    service.record_script(day, "工作不顺时，先别急着否定自己。")
    service.approve_script(day, actor="owner")
    service.mark_audio_ready(day, artifact_path="audio/main.wav")
    service.mark_assets_generating(day)
    service.mark_compositing(day)
    service.record_qc(day, passed=True, report_path="qc/report.json")
    task = service.approve_video(day, actor="owner")

    assert task.status == TaskStatus.VIDEO_APPROVED
    assert [approval.gate for approval in task.approvals] == ["topic", "script", "video"]


def test_topic_must_be_one_of_top_three(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 4)
    service.start_day(day)
    service.record_research(day, candidates())
    with pytest.raises(WorkflowPreconditionError, match="not in Top 3"):
        service.approve_topic(day, "unknown", actor="owner")
```

- [x] **Step 2: 运行测试并确认失败**

Run: `python -m pytest tests/test_service.py -v`

Expected: FAIL，错误包含 `No module named 'avatar_pipeline.service'`。

- [x] **Step 3: 实现服务**

所有服务方法必须先读取任务、验证前置状态、调用 `ensure_transition`、更新字段并保存。审批记录包含 `gate`、`actor`、`approved_at`。`record_script` 拒绝空白文本。`approve_video` 仅允许 `qc_passed` 状态。

- [x] **Step 4: 运行服务测试**

Run: `python -m pytest tests/test_service.py -v`

Expected: `2 passed`。

- [x] **Step 5: 运行全部测试并提交**

```bash
python -m pytest -q
python -m ruff check src tests
git add src/avatar_pipeline/service.py tests/test_service.py
git commit -m "feat: add approval-gated daily workflow service"
```

### Task 7：命令行入口与端到端烟雾测试

**Files:**
- Create: `src/avatar_pipeline/cli.py`
- Test: `tests/test_cli.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `load_config`、`DailyTaskRepository`、`DailyWorkflowService`。
- Produces: `avatar-pipeline` 命令及 JSON 标准输出。

- [x] **Step 1: 编写失败的 CLI 测试**

```python
import json
import subprocess
import sys


def run_cli(tmp_path, *args):
    return subprocess.run(
        [sys.executable, "-m", "avatar_pipeline.cli", "--workspace", str(tmp_path), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_cli_initializes_and_reports_day(tmp_path):
    created = run_cli(tmp_path, "init-day", "--date", "2026-08-04")
    assert created.returncode == 0
    status = run_cli(tmp_path, "status", "--date", "2026-08-04")
    assert status.returncode == 0
    payload = json.loads(status.stdout)
    assert payload["day"] == "2026-08-04"
    assert payload["status"] == "created"


def test_cli_health_reports_ffmpeg_and_disabled_real_generators(tmp_path):
    result = run_cli(tmp_path, "health")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["ffmpeg"]["available"] is True
    assert payload["skills"]["avatar"]["real_generation_enabled"] is False
    assert payload["skills"]["seedance"]["real_generation_enabled"] is False
```

- [x] **Step 2: 运行测试并确认失败**

Run: `python -m pytest tests/test_cli.py -v`

Expected: FAIL，因为 `avatar_pipeline.cli` 尚不存在。

- [x] **Step 3: 实现 CLI**

全局参数：`--workspace`，默认读取配置中的 `workspace`。子命令：

- `health`：检查 Python、FFmpeg/ffprobe 和三份 Skill 契约，输出 JSON；
- `init-day --date YYYY-MM-DD`；
- `status --date YYYY-MM-DD`；
- `import-topics --date ... --file topics.json`；
- `approve-topic --date ... --topic-id ... --actor ...`；
- `record-script --date ... --file script.txt`；
- `approve-script --date ... --actor ...`；
- `record-qc --date ... --passed true|false --report ...`；
- `approve-video --date ... --actor ...`。

异常写入 stderr，返回码 `2`；成功输出 UTF-8 JSON。模块末尾包含：

```python
if __name__ == "__main__":
    raise SystemExit(main())
```

README 增加从 `init-day` 到 `approve-topic` 的最小示例，并明确真实生成 Skill 尚未启用。

- [x] **Step 4: 运行 CLI 测试**

Run: `python -m pytest tests/test_cli.py -v`

Expected: `2 passed`。

- [x] **Step 5: 运行完整验证**

```bash
python -m pytest -q
python -m pytest --cov=avatar_pipeline --cov-report=term-missing
python -m ruff check src tests
avatar-pipeline health
```

Expected: 所有测试通过；覆盖率不低于 85%；Ruff 无错误；health JSON 显示 FFmpeg 可用且三个真实生成能力均为禁用。

- [x] **Step 6: 提交**

```bash
git add src/avatar_pipeline/cli.py tests/test_cli.py README.md
git commit -m "feat: add foundation workflow cli"
```

### Task 8：Phase 1 验收与文档同步

**Files:**
- Modify: `docs/superpowers/plans/2026-08-04-phase-1-foundation.md`
- Create: `docs/operations/phase-1-runbook.md`

**Interfaces:**
- Consumes: Phase 1 全部 CLI。
- Produces: 可重复的本地验收步骤。

- [x] **Step 1: 执行临时工作区端到端演练**

创建 Top 3 JSON 后依次运行：

```bash
rm -rf /tmp/avatar-pipeline-smoke
avatar-pipeline --workspace /tmp/avatar-pipeline-smoke init-day --date 2026-08-04
avatar-pipeline --workspace /tmp/avatar-pipeline-smoke import-topics --date 2026-08-04 --file tests/fixtures/top_topics.json
avatar-pipeline --workspace /tmp/avatar-pipeline-smoke approve-topic --date 2026-08-04 --topic-id t1 --actor owner
avatar-pipeline --workspace /tmp/avatar-pipeline-smoke status --date 2026-08-04
```

Expected: 最终状态为 `topic_approved`，`selected_topic_id` 为 `t1`，审批数组只包含 `topic`。

- [x] **Step 2: 编写运行手册**

`docs/operations/phase-1-runbook.md` 必须包含安装、健康检查、每日任务初始化、Top 3 JSON 格式、三个人工审批点、任务目录位置、常见错误和外部 Skill 仍被禁用的说明。

- [x] **Step 3: 勾选已执行的计划步骤并运行最终验证**

Run: `python -m pytest -q && python -m ruff check src tests && git diff --check`

Expected: 测试全部通过、Ruff 无错误、无空白错误。

- [x] **Step 4: 提交验收文档**

```bash
git add docs/operations/phase-1-runbook.md docs/superpowers/plans/2026-08-04-phase-1-foundation.md tests/fixtures/top_topics.json
git commit -m "docs: add phase one operations runbook"
```
