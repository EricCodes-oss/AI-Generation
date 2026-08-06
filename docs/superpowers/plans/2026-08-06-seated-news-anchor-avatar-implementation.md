# 固定坐播新闻主持人形象 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `subagent-driven-development` (recommended) or `executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将已确认的单一坐播新闻主持人规格落到配置、领域模型、GPT Image 2 Skill Contract 和每日复用流程中，同时保持热点新闻是内容主体。

**Architecture:** 在现有新闻生产双模式架构上增加显式的 `seated_studio_anchor` 布局和主持人资产规格；主持人资产只在首次创建或用户变更时生成/确认，日常任务直接复用已确认资产。外部 GPT Image 2、TTS 和 TV Avatar 仍通过现有契约边界注入，先完成可测试的规格和状态约束，不在本计划中直接消耗外部生成额度或生成最终视频。

**Tech Stack:** Python 3.11+, Pydantic 2, PyYAML, pytest, JSON 文件仓储，现有 Skill Contract YAML。

## Global Constraints

- V1 只使用一套固定的演播室坐播主持人形象，不实现站播、户外、访谈、多主持人或多形象专题版本。
- 主持人只负责开场、解释、串联和总结，热点事实、脚本质量、原始新闻画面和 AI 示意画面是内容主体。
- 视频默认输出 9:16、1080×1920；同一母版用于抖音、微信视频号和小红书。
- 坐播主图采用腰部以上中景、人物居中、面部/嘴部无遮挡、适合口型同步。
- 主持人视觉规格：成年东亚女性，视觉年龄 30–36 岁，黑色中长直发，深蓝西装、米白内搭，成熟、专业、可信、克制。
- 用户参考图只提供黑长发、面部气质、自信镜头感、写实摄影、灰蓝色调和专业灯光参考；不得复制警察制服、警徽、审讯室、铁栅栏、案件海报或性感化姿态。
- 不出现真实媒体 Logo、政府/执法机构标志、现实公众人物相貌、可读的虚假新闻文字或冒充权威的身份表达。
- 已确认主持人每日复用；手动模式只在首次或发生形象/演播室变更时请求主持人确认；托管模式不发起中间确认。
- 默认关闭逐字字幕；不改动已确认的热点准入、事实核验、素材来源和 AI 示意画面披露规则。
- 每个实现任务先写失败测试，再写最小实现；每个任务完成运行定向测试、`git diff --check` 并提交。

## File Map

- Modify: `src/avatar_pipeline/models.py` — 增加坐播布局类型、主持人资产元数据和一致性约束。
- Modify: `src/avatar_pipeline/config.py` — 增加 `avatar_layout` 和固定坐播规格校验。
- Modify: `configs/default.yaml` — 将默认主持人布局锁定为 `seated_studio_anchor`，写入视觉约束和生成配置。
- Modify: `src/avatar_pipeline/skill_contracts.py` — 将 GPT Image 2 主持人契约的输入/输出规格固定为坐播主图，并保留 TV Avatar 的 image+audio 方式。
- Modify: `src/avatar_pipeline/service.py` — 仅在首次/变更时进入主持人确认，保存后续任务复用标记。
- Modify: `src/avatar_pipeline/orchestration.py` — 让托管和手动编排都使用保存的固定坐播主持人，不为每日任务重复设计。
- Modify: `src/avatar_pipeline/repository.py` — 兼容旧 `HostProfile` JSON，为缺失布局字段安全补默认值。
- Modify: `src/avatar_pipeline/cli.py` — 暴露坐播布局和主持人资产状态，但不新增无必要的过程确认命令。
- Create: `tests/test_seated_host_profile.py` — 坐播主持人模型、参考图边界和复用规则。
- Modify: `tests/test_models.py` — 更新主持人和任务断言。
- Modify: `tests/test_config.py` — 默认配置和非法布局断言。
- Modify: `tests/test_skill_contracts.py` — 坐播 Image 2 与 TV Avatar 契约断言。
- Modify: `tests/test_orchestration.py` — 主持人只首次生成、后续复用的编排断言。
- Modify: `tests/test_repository.py` — 旧主持人 JSON 迁移断言。
- Modify: `README.md` — 说明固定坐播主持人仅作内容串联，及其首次确认/每日复用规则。

## Task 1: Lock the seated host domain model

**Files:**
- Modify: `src/avatar_pipeline/models.py`
- Create: `tests/test_seated_host_profile.py`
- Modify: `tests/test_models.py`

**Interfaces:**
- Add `AvatarLayout(StrEnum)` with `SEATED_STUDIO_ANCHOR = "seated_studio_anchor"`.
- Extend `HostProfile` with `layout: AvatarLayout = AvatarLayout.SEATED_STUDIO_ANCHOR`, `age_range: str = "30-36"`, `outfit: str = "deep_navy_blazer_ivory_blouse"`, and `mouth unobstructed` metadata represented by `mouth_unobstructed: bool = True`.
- Keep `reference_image`, `studio_reference`, `voice_id`, `is_new`, and `version` semantics unchanged.
- Add `HostProfile` validation rejecting non-seated layouts for V1 and blank/unsafe visual metadata.

- [ ] **Step 1: Write the failing tests**

```python
from avatar_pipeline.models import AvatarLayout, HostProfile


def test_host_profile_defaults_to_seated_studio_anchor():
    host = HostProfile(id="host", display_name="主持人", reference_image="host.png")
    assert host.layout is AvatarLayout.SEATED_STUDIO_ANCHOR
    assert host.age_range == "30-36"
    assert host.outfit == "deep_navy_blazer_ivory_blouse"
    assert host.mouth_unobstructed is True


def test_host_profile_rejects_non_seated_layout():
    with pytest.raises(ValidationError):
        HostProfile(
            id="host",
            display_name="主持人",
            reference_image="host.png",
            layout="outdoor_reporter",
        )
```

- [ ] **Step 2: Run the focused tests to verify they fail**

```bash
pytest tests/test_seated_host_profile.py tests/test_models.py -q
```

Expected: FAIL because `AvatarLayout` and the new `HostProfile` fields do not exist.

- [ ] **Step 3: Implement the minimal model changes**

```python
class AvatarLayout(StrEnum):
    SEATED_STUDIO_ANCHOR = "seated_studio_anchor"


class HostProfile(DomainModel):
    id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    reference_image: str = Field(min_length=1)
    studio_reference: str | None = None
    voice_id: str | None = None
    visual_style: str = "成熟陪伴型新闻主持人"
    layout: AvatarLayout = AvatarLayout.SEATED_STUDIO_ANCHOR
    age_range: str = "30-36"
    outfit: str = "deep_navy_blazer_ivory_blouse"
    mouth_unobstructed: bool = True
    is_new: bool = False
    version: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def validate_seated_identity(self) -> "HostProfile":
        if self.layout is not AvatarLayout.SEATED_STUDIO_ANCHOR:
            raise ValueError("V1 host must use seated_studio_anchor layout")
        if not self.mouth_unobstructed:
            raise ValueError("host mouth must remain unobstructed for lip synchronization")
        return self
```

- [ ] **Step 4: Run the focused tests to verify they pass**

```bash
pytest tests/test_seated_host_profile.py tests/test_models.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/avatar_pipeline/models.py tests/test_seated_host_profile.py tests/test_models.py
git diff --check
git commit -m "feat: model fixed seated news anchor profile"
```

## Task 2: Lock configuration and default asset-generation specification

**Files:**
- Modify: `src/avatar_pipeline/config.py`
- Modify: `configs/default.yaml`
- Modify: `tests/test_config.py`

**Interfaces:**
- Add `avatar_layout: Literal["seated_studio_anchor"]` to `AppConfig`.
- Add a strict `HostVisualConfig` containing the approved visual invariants: `visual_style`, `age_range`, `outfit`, `aspect_ratio`, `shot`, `background`, `subtitle_default`.
- Require `aspect_ratio == "9:16"`, `shot == "waist_up_seated"`, and `subtitle_default is False`.
- Keep the existing `avatar_source`, dual-mode approval policy, and video output constraints.

- [ ] **Step 1: Write failing configuration tests**

```python
def test_default_config_locks_seated_host_layout():
    config = load_config(Path("configs/default.yaml"))
    assert config.avatar_layout == "seated_studio_anchor"
    assert config.host_visual.shot == "waist_up_seated"
    assert config.host_visual.aspect_ratio == "9:16"
    assert config.host_visual.subtitle_default is False


def test_config_rejects_standing_host_layout():
    raw = yaml.safe_load(Path("configs/default.yaml").read_text())
    raw["avatar_layout"] = "standing_anchor"
    with pytest.raises(ValidationError):
        AppConfig.model_validate(raw)
```

- [ ] **Step 2: Run focused tests and verify failure**

```bash
pytest tests/test_config.py -q
```

Expected: FAIL because the config schema has no `avatar_layout` or `host_visual`.

- [ ] **Step 3: Implement schema and YAML**

```yaml
avatar_layout: seated_studio_anchor
host_visual:
  visual_style: mature_professional_news_anchor
  age_range: 30-36
  outfit: deep_navy_blazer_ivory_blouse
  aspect_ratio: "9:16"
  shot: waist_up_seated
  background: fictional_quiet_news_studio
  subtitle_default: false
```

- [ ] **Step 4: Run focused config tests**

```bash
pytest tests/test_config.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/avatar_pipeline/config.py configs/default.yaml tests/test_config.py
git diff --check
git commit -m "feat: configure seated news anchor asset"
```

## Task 3: Make Image 2 and TV Avatar contracts content-first and seated-only

**Files:**
- Modify: `src/avatar_pipeline/skill_contracts.py`
- Modify: `skills/contracts/host-image.yaml`
- Modify: `skills/contracts/avatar.yaml`
- Create: `tests/test_seated_avatar_contracts.py`
- Modify: `tests/test_skill_contracts.py`

**Interfaces:**
- `host-image` input contract must require `reference_image` optional, `prompt`, `layout=seated_studio_anchor`, `aspect_ratio=9:16`, `shot=waist_up_seated`, and a negative prompt block rejecting police/official/sexualized elements.
- Its output contract must expose `image_path`, `identity_notes`, `safety_check`.
- `avatar` contract remains `image_plus_audio`, but requires fixed host image, TTS audio path, `layout=seated_studio_anchor`, and returns `video_path`, `task_id`.
- Contract metadata must identify `giggle-gpt-image-2`, `giggle-generation-tv-avatar-video`, and `giggle-generation-speech`; no real external calls are made in these tests.

- [ ] **Step 1: Write failing contract tests**

```python
def test_host_image_contract_is_seated_and_negative_prompted():
    contracts = load_contracts(Path("skills/contracts"))
    contract = contracts[SkillKind.HOST_IMAGE]
    assert contract.provider == "giggle-gpt-image-2"
    assert contract.required_inputs["layout"] == "seated_studio_anchor"
    assert contract.required_inputs["shot"] == "waist_up_seated"
    assert "police badge" in contract.negative_prompt.lower()


def test_avatar_contract_requires_audio_and_seated_layout():
    contract = load_contracts(Path("skills/contracts"))[SkillKind.AVATAR]
    assert contract.primary_mode == "image_plus_audio"
    assert contract.required_inputs["layout"] == "seated_studio_anchor"
    assert "audio_path" in contract.required_inputs
```

- [ ] **Step 2: Run focused tests and verify failure**

```bash
pytest tests/test_seated_avatar_contracts.py tests/test_skill_contracts.py -q
```

Expected: FAIL because the contract schema/fixtures do not expose seated-specific fields.

- [ ] **Step 3: Implement the contract schema and YAML fixtures**

```yaml
name: giggle-gpt-image-2
provider: giggle-gpt-image-2
kind: host_image
required_inputs:
  layout: seated_studio_anchor
  aspect_ratio: "9:16"
  shot: waist_up_seated
  prompt: string
  negative_prompt: string
negative_prompt: "police uniform, police badge, military uniform, government emblem, ..."
required_outputs:
  - image_path
  - identity_notes
  - safety_check
```

- [ ] **Step 4: Run focused tests and lint**

```bash
pytest tests/test_seated_avatar_contracts.py tests/test_skill_contracts.py -q
ruff check src/avatar_pipeline/skill_contracts.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/avatar_pipeline/skill_contracts.py skills/contracts/host-image.yaml skills/contracts/avatar.yaml tests/test_seated_avatar_contracts.py tests/test_skill_contracts.py
git diff --check
git commit -m "feat: constrain avatar skills to seated host asset"
```

## Task 4: Reuse the confirmed seated host in service and orchestration

**Files:**
- Modify: `src/avatar_pipeline/service.py`
- Modify: `src/avatar_pipeline/orchestration.py`
- Modify: `tests/test_orchestration.py`
- Modify: `tests/test_models.py`

**Interfaces:**
- Add `HostProvider = Callable[[], HostProfile]` and make providers distinguish `saved_host` from `agent_designed`/`user_provided`.
- `DailyWorkflowService.set_host` must route new/changed hosts to `HOST_REVIEW` only in manual mode; a saved `seated_studio_anchor` host routes directly to TTS.
- Managed mode may create a host internally if none exists, but never records a user host approval.
- `run_managed` must call the host provider at most once per run, mark `avatar_source`, and preserve the same `reference_image` for TTS/TV Avatar.

- [ ] **Step 1: Write failing reuse tests**

```python
def test_managed_run_reuses_saved_seated_host_without_new_design_call():
    calls = []
    providers = make_providers(host=lambda: calls.append("host") or saved_host())
    task = run_managed(service, day, [verified_candidate()], providers)
    assert calls == ["host"]
    assert task.host_profile.layout.value == "seated_studio_anchor"
    assert task.approvals == []


def test_manual_reused_host_skips_host_review_gate():
    task = service.set_host(day, saved_host(is_new=False))
    assert task.status is TaskStatus.GENERATING_TTS
    assert task.requires_host_approval is False
```

- [ ] **Step 2: Run focused tests and verify failure**

```bash
pytest tests/test_orchestration.py tests/test_models.py -q
```

Expected: FAIL until the service explicitly handles the fixed seated host lifecycle.

- [ ] **Step 3: Implement minimal lifecycle changes**

```python
def _advance_after_media_plan(self, task: DailyTask) -> DailyTask:
    if task.host_profile and not task.host_profile.is_new:
        ensure_transition(task.status, TaskStatus.GENERATING_TTS)
        task.status = TaskStatus.GENERATING_TTS
    elif task.mode is RunMode.MANAGED:
        ensure_transition(task.status, TaskStatus.GENERATING_TTS)
        task.status = TaskStatus.GENERATING_TTS
    return self.repository.save(task)
```

- [ ] **Step 4: Run tests and lint**

```bash
pytest tests/test_orchestration.py tests/test_models.py -q
ruff check src/avatar_pipeline/service.py src/avatar_pipeline/orchestration.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/avatar_pipeline/service.py src/avatar_pipeline/orchestration.py tests/test_orchestration.py tests/test_models.py
git diff --check
git commit -m "feat: reuse fixed seated host across daily runs"
```

## Task 5: Migrate legacy host profiles safely

**Files:**
- Modify: `src/avatar_pipeline/repository.py`
- Modify: `src/avatar_pipeline/migration.py`
- Create: `tests/test_host_migration.py`

**Interfaces:**
- Loading a legacy host without `layout`, `age_range`, `outfit`, or `mouth_unobstructed` fills only safe defaults; it never changes `reference_image`, `voice_id`, `version`, or `is_new`.
- A legacy host with a known non-seated layout must be marked `is_new=True` and routed to host review rather than silently accepted.
- Unknown/unsafe layout values must raise a clear migration error and prevent publication.

- [ ] **Step 1: Write failing migration tests**

```python
def test_legacy_host_gets_safe_seated_defaults_without_identity_drift():
    payload = {"id": "host", "display_name": "主持人", "reference_image": "old.png"}
    migrated = migrate_host_profile(payload)
    assert migrated.layout.value == "seated_studio_anchor"
    assert migrated.reference_image == "old.png"
    assert migrated.is_new is True


def test_legacy_non_seated_host_requires_review():
    payload = {"id": "host", "display_name": "主持人", "reference_image": "old.png", "layout": "standing_anchor"}
    with pytest.raises(MigrationError):
        migrate_host_profile(payload)
```

- [ ] **Step 2: Run focused tests and verify failure**

```bash
pytest tests/test_host_migration.py -q
```

Expected: FAIL because host migration is not explicit.

- [ ] **Step 3: Implement migration function and repository hook**

```python
def migrate_host_profile(payload: dict[str, Any]) -> HostProfile:
    normalized = dict(payload)
    normalized.setdefault("layout", "seated_studio_anchor")
    normalized.setdefault("age_range", "30-36")
    normalized.setdefault("outfit", "deep_navy_blazer_ivory_blouse")
    normalized.setdefault("mouth_unobstructed", True)
    normalized["is_new"] = True if "layout" not in payload else normalized.get("is_new", True)
    return HostProfile.model_validate(normalized)
```

- [ ] **Step 4: Run tests and lint**

```bash
pytest tests/test_host_migration.py -q
ruff check src/avatar_pipeline/repository.py src/avatar_pipeline/migration.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/avatar_pipeline/repository.py src/avatar_pipeline/migration.py tests/test_host_migration.py
git diff --check
git commit -m "fix: migrate legacy host profiles safely"
```

## Task 6: Keep media/compositor assumptions aligned with seated anchor

**Files:**
- Modify: `src/avatar_pipeline/media.py`
- Modify: `src/avatar_pipeline/models.py`
- Create: `tests/test_seated_media_layout.py`
- Modify: `tests/test_media.py`

**Interfaces:**
- `MediaPlan` must retain the alternating `ANCHOR → insert → ANCHOR` rule and add `anchor_layout=seated_studio_anchor`.
- `MediaSegment(kind=ANCHOR)` must reference the fixed host profile ID or layout metadata.
- `validate_media_plan` rejects a non-seated anchor layout and rejects an anchor segment without the declared host ID.
- AI demo segments still require explicit disclosure; original news segments still require source/provenance.

- [ ] **Step 1: Write failing media tests**

```python
def test_media_plan_declares_seated_anchor_layout():
    plan = seated_plan()
    assert plan.anchor_layout.value == "seated_studio_anchor"
    validate_media_plan(plan, script)


def test_media_plan_rejects_non_seated_anchor_layout():
    with pytest.raises(ValidationError):
        seated_plan(anchor_layout="standing_anchor")
```

- [ ] **Step 2: Run focused tests and verify failure**

```bash
pytest tests/test_seated_media_layout.py tests/test_media.py -q
```

Expected: FAIL until media models carry the fixed host layout.

- [ ] **Step 3: Implement minimal media metadata validation**

```python
class MediaPlan(DomainModel):
    duration_seconds: float = Field(gt=0)
    segments: list[MediaSegment] = Field(min_length=3)
    anchor_layout: AvatarLayout = AvatarLayout.SEATED_STUDIO_ANCHOR
    host_id: str = Field(min_length=1)
```

- [ ] **Step 4: Run tests and lint**

```bash
pytest tests/test_seated_media_layout.py tests/test_media.py -q
ruff check src/avatar_pipeline/media.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/avatar_pipeline/media.py src/avatar_pipeline/models.py tests/test_seated_media_layout.py tests/test_media.py
git diff --check
git commit -m "feat: validate seated anchor media timeline"
```

## Task 7: Expose only meaningful user-facing host controls

**Files:**
- Modify: `src/avatar_pipeline/cli.py`
- Modify: `src/avatar_pipeline/publication.py`
- Modify: `README.md`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_publication.py`

**Interfaces:**
- `init-day` accepts `--mode managed|manual`, `--topic-source user_topic|auto_hot`, and optional `--host-image`; it defaults to reusing the saved seated host.
- Manual mode exposes exactly three gates: `approve-topic-script`, optional `approve-host`, and `approve-final`; no per-step prompts for TTS, composition, or encoding.
- Publication package contains one `master_video_path` reused by `douyin`, `wechat_channels`, and `xiaohongshu`, plus AI disclosure/source metadata.
- Refuse publication if task is not `READY_TO_PUBLISH` or source/disclosure records are incomplete.

- [ ] **Step 1: Write failing CLI/publication tests** for managed/manual initialization, the three manual approval commands, host approval omission when reusing a saved host, health output, same-master packaging, and refusal to package an unverified/unfinished task.
- [ ] **Step 2: Run focused tests**

```bash
pytest tests/test_cli.py tests/test_publication.py -q
```

Expected: FAIL because CLI commands, new status names, and publication packaging do not exist.

- [ ] **Step 3: Implement CLI parsing and dispatch** over the service/orchestrator interfaces; keep all state changes persisted through the repository.

- [ ] **Step 4: Implement platform packaging** without producing three divergent videos or claiming that AI footage is real news.

- [ ] **Step 5: Update README** with both examples:

```bash
python -m avatar_pipeline.cli --workspace workspace init-day --date 2026-08-06 --mode manual --topic-source auto_hot
python -m avatar_pipeline.cli --workspace workspace init-day --date 2026-08-06 --mode managed --topic-source user_topic --input "年轻人如何看待工作和生活的边界"
```

- [ ] **Step 6: Run focused tests, full tests, and lint**

```bash
pytest tests/test_cli.py tests/test_publication.py -q
pytest -q
ruff check src/avatar_pipeline/cli.py src/avatar_pipeline/publication.py
```

Expected: all tests pass and CLI help documents no interactive mid-process confirmation.

- [ ] **Step 7: Commit**

```bash
 git add src/avatar_pipeline/cli.py src/avatar_pipeline/publication.py tests/test_cli.py tests/test_publication.py README.md
 git commit -m "feat: expose dual-mode CLI and platform publication package"
```

## Task 8: Add end-to-end acceptance coverage and release verification

**Files:**
- Create: `tests/test_end_to_end_news_workflow.py`
- Modify: `tests/test_config.py`
- Modify: `tests/test_skill_contracts.py`
- Modify: `README.md`

**Interfaces:**
- End-to-end fixture uses fake crawler/script/TTS/avatar/media/compositor/QC providers and writes a complete persisted task plus publication package.
- Acceptance coverage must prove: verified-only admission; fixed anchor/insert timeline; original-footage-first fallback to disclosed AI demo; default no subtitles; same master for all platforms; managed mode has no user approval records; manual mode has no more than the agreed three user-facing gates and skips host confirmation on reuse; failure stops rather than publishing unsafe content.

- [ ] **Step 1: Write failing end-to-end acceptance tests** for one successful managed run, one manual run with host reuse, and one unsafe/no-candidate stop.
- [ ] **Step 2: Run the acceptance tests**

```bash
pytest tests/test_end_to_end_news_workflow.py -q
```

Expected: FAIL until all previous components are wired together.

- [ ] **Step 3: Implement only integration wiring and fixture helpers**; do not weaken domain validations to make the fixtures pass.

- [ ] **Step 4: Run the complete verification suite**

```bash
pytest -q
ruff check src tests
ruff format --check src tests
python -m avatar_pipeline.cli --workspace /tmp/avatar-pipeline-health health
```

Expected: all tests pass, Ruff check and format checks pass, and health reports Python, ffmpeg/ffprobe, and all configured contracts.

- [ ] **Step 5: Run final repository checks**

```bash
git diff --check
git status --short
git log --oneline -8
```

Expected: no whitespace errors; only intended files are modified; all implementation commits are visible.

- [ ] **Step 6: Commit**

```bash
git add tests/test_end_to_end_news_workflow.py tests/test_config.py tests/test_skill_contracts.py README.md
git commit -m "test: verify end-to-end dual-mode news production"
```

## Execution Order and Completion Criteria

Execute Tasks 1–8 in order because later contracts depend on the new domain vocabulary and state machine. Do not connect real external generation providers before the fake-provider end-to-end workflow is green. A task is complete only when its tests, lint, `git diff --check`, and commit step succeed.

The implementation is complete when:

1. `managed` and `manual` are distinct, persisted modes.
2. Only verified, low-risk hotspots reach formal production candidates.
3. Manual mode pauses only at the three approved gates, with host approval conditional on a new/changed host.
4. Managed mode completes without user confirmation records and has bounded retry/stop behavior.
5. The persisted plan expresses the fixed studio-anchor/vertical-insert structure and source/disclosure provenance.
6. TTS, GPT Image 2 host design, TV Avatar, Seedance, compositor, and QC are represented by strict contracts and injectable adapters.
7. The default output is a single 9:16 master without word-for-word subtitles, reusable across all three platforms.
8. Legacy JSON is safely migrated without fabricating fact verification.
9. Full tests, Ruff checks, format checks, and CLI health verification pass.
