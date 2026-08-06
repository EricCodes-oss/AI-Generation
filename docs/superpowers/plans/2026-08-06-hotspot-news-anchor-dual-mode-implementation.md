# 热点新闻数字人主持人双模式视频系统 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `subagent-driven-development` (recommended) or `executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有“人生陪伴型数字人”流程升级为每天生产一条“固定演播室主持人 + 竖屏新闻画面插播”的热点新闻解读视频，并支持托管模式与手动模式。

**Architecture:** 保留当前 Python、Pydantic、YAML、JSON 文件持久化和 CLI 架构，但把旧的鸡汤选题/独立脚本审批改为新闻生产领域模型。热点采集结果先经过去重、事实状态和风险策略筛选，只有 `verified` 且低风险的候选才能进入脚本、媒体计划和生成阶段；托管模式自动通过内部闸门，手动模式只暴露“选题+脚本+画面规划”“新主持人形象”“最终视频”三个关键确认点。外部生成器通过可校验的 Skill Contract 和适配器接入，具体生成仍由已安装的 TTS、TV Avatar、Seedance 技能执行。

**Tech Stack:** Python 3.11+, Pydantic 2, PyYAML, pytest, JSON 文件仓储，ffmpeg/ffprobe 能力探测；外部技能：`opinions-crawler`、`wechat-article-search`、`material-organizer`、`viral-topic-forge`/`wechat-viral-topic`、`scene-planner`、`giggle-generation-speech`、`giggle-gpt-image-2`、`giggle-generation-tv-avatar-video`、`giggle-seedance2-gen`，以及新增的新闻素材截取、视频合成和质量检查契约。

## Global Constraints

- V1 固定使用“演播室主持人 + 竖屏新闻画面插播”结构，不实现户外主持、访谈主持、多主持人、多演播室和复杂剧情表演。
- 视频默认输出 9:16、1080×1920，同一母版用于抖音、微信视频号和小红书。
- 单条视频目标时长为 45–75 秒，按事实复杂度和 TTS 实际时长决定，不强行截断有效事实。
- 默认关闭逐字口播字幕；只保留原创栏目名、热点标题、简短信息条、来源标识和必要的“AI生成示意画面”标识。
- 热度只用于确定核查优先级；`pending`、`unverified`、`high_risk`、`malicious` 永远不得进入正式候选池、脚本、TTS、数字人或合成阶段。
- 原始新闻视频优先；无法合规使用或不适合展示时使用 Seedance AI 示意画面，且不得伪装成真实现场、真实人物或事实证据。
- 不复制参考视频 `/Users/liuweidong/Downloads/40561412638-1-192.mp4` 的 Logo、栏目名称、颜色体系、字体组合或版式，只复用“主持人和插播画面交替”的结构原则。
- 托管模式不向用户发起中间确认；遇到事实不足、风险、版权、生成或质检失败时自动换题、重试或停止，并在最终结果中说明原因。
- 手动模式仅在选题/脚本/画面规划、主持人形象首次或变更、最终视频三个关键点请求确认；TTS 参数、普通转场、音量、编码、命名和过程日志不单独确认。
- 已确认的固定主持人和演播室配置每日复用；用户提供主持人形象时优先使用，未提供时由 Agent 设计并在手动模式首次或变更时确认。
- 每日没有达到可信度、安全性和素材可用标准的热点时，不为满足日更而强行生产。
- 每一项实现都必须先写失败测试，再写最小实现；每个任务结束运行该任务的定向测试和 `git diff --check` 后提交。

## File Map

- Modify: `src/avatar_pipeline/models.py` — 新闻候选、事实核验、主持人、脚本、媒体计划、审批、产物和每日任务模型。
- Modify: `src/avatar_pipeline/state.py` — 双模式共享状态机、托管内部闸门和手动关键审批状态。
- Modify: `src/avatar_pipeline/service.py` — 每日任务服务、候选准入、编排动作、审批动作和重试/停止规则。
- Modify: `src/avatar_pipeline/config.py` — 新配置结构及旧配置迁移/校验。
- Modify: `configs/default.yaml` — V1 视频、模式、内容范围、媒体策略、字幕和审批策略默认值。
- Modify: `src/avatar_pipeline/repository.py` — 版本化 JSON 持久化及旧任务读取迁移。
- Modify: `src/avatar_pipeline/skill_contracts.py` — 新闻研究、文案、TTS、主持人、素材、Seedance、合成和 QC 契约加载。
- Modify: `src/avatar_pipeline/cli.py` — 双模式启动、导入研究结果、提交规划、审批、状态和产物登记命令。
- Create: `src/avatar_pipeline/policy.py` — 事实状态和风险准入策略，避免将安全规则散落在 CLI/服务中。
- Create: `src/avatar_pipeline/orchestration.py` — 托管模式自动推进和手动模式阶段推进的编排边界。
- Create: `src/avatar_pipeline/media.py` — 原始视频素材记录、AI 示意标记和媒体计划校验。
- Create: `src/avatar_pipeline/publication.py` — 三个平台共用母版的发布包装数据生成。
- Create: `skills/contracts/opinions-crawler.yaml` — 多平台热点采集输入/输出契约。
- Create: `skills/contracts/news-script-writer.yaml` — 热点新闻解读脚本契约。
- Create: `skills/contracts/news-media-planner.yaml` — 主持人/插播时间轴契约。
- Create: `skills/contracts/gpt-image-2-host.yaml` — 固定主持人和演播室参考图契约。
- Create: `skills/contracts/news-footage-clipper.yaml` — 原始新闻片段截取契约。
- Create: `skills/contracts/news-compositor.yaml` — 栏目合成契约。
- Create: `skills/contracts/news-quality-control.yaml` — 事实、素材、音画和安全区检查契约。
- Modify: `tests/test_models.py`, `tests/test_state.py`, `tests/test_service.py`, `tests/test_config.py`, `tests/test_repository.py`, `tests/test_cli.py`, `tests/test_skill_contracts.py` — 将旧流程测试改为双模式新闻流程。
- Create: `tests/test_policy.py`, `tests/test_media.py`, `tests/test_orchestration.py`, `tests/test_publication.py`, `tests/fixtures/verified_hotspots.json`, `tests/fixtures/legacy_task.json` — 新策略、媒体、编排、发布和迁移测试夹具。
- Modify: `README.md` — 更新运行方式、模式语义、质量闸门、生成边界和验收命令。

---

### Task 1: 重建新闻生产领域模型与配置边界

**Files:**
- Modify: `src/avatar_pipeline/models.py`
- Modify: `src/avatar_pipeline/config.py`
- Modify: `configs/default.yaml`
- Test: `tests/test_models.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces `RunMode(str, Enum)` with `MANAGED = "managed"` and `MANUAL = "manual"`.
- Produces `TopicSource(str, Enum)` with `USER_TOPIC = "user_topic"` and `AUTO_HOT = "auto_hot"`.
- Produces `AvatarSource(str, Enum)` with `USER_PROVIDED = "user_provided"`, `SAVED_HOST = "saved_host"`, and `AGENT_DESIGNED = "agent_designed"`.
- Produces `FactStatus(str, Enum)` with `VERIFIED`, `PENDING`, `UNVERIFIED`, `HIGH_RISK`, `MALICIOUS`.
- Replaces old `ContentPillarSlug` with news-oriented values: `social_phenomena`, `workplace_life`, `education`, `consumer_life`, `technology_life`, `family_relationships`, `youth_lifestyle`.
- Produces `SourceEvidence` with `source_id`, `platform`, `title`, `url_or_reference`, `published_at`, `evidence_type`, and `reliability_note`.
- Extends `TopicCandidate` with `fact_status`, `risk_flags`, `source_evidence`, `dedupe_key`, `cluster_id`, `verified_at`, `verification_summary`, and `publishable`; retains score/title/recommendation data needed by the UI.
- Produces `HostProfile`, `NewsScript`, `ScriptSegment`, `MediaPlan`, `MediaSegment`, and `DailyTask` fields for `mode`, `input_text`, `topic_source`, `avatar_source`, `selected_topic_id`, `host_profile`, `news_script`, `media_plan`, `subtitle_enabled`, `video_structure`, `media_policy`, `platforms`, and `schema_version`.
- Replaces `ApprovalRecord.gate` values with `topic_script`, `host`, and `final_video`; supports `host` only when a host is new or changed.
- Updates `AppConfig` to validate `mode`, `topic_source`, `avatar_source`, `subtitle`, `video_structure`, `media_policy`, `platforms`, `approval_policy`, and 45–75 second production bounds.

- [ ] **Step 1: Write failing model tests** for both mode enums, verified/unverified candidate fields, combined script/media plan, conditional host approval, default no-subtitle configuration, and rejection of unsupported video structures.
- [ ] **Step 2: Run focused tests**

```bash
pytest tests/test_models.py tests/test_config.py -q
```

Expected: FAIL because the old pillar, candidate, approval, and config models do not expose the new news workflow.

- [ ] **Step 3: Implement the minimal models and config validation** without adding provider-specific API calls.
- [ ] **Step 4: Update `configs/default.yaml`** with the exact V1 defaults: `mode: manual`, `topic_source: auto_hot`, `avatar_source: saved_host`, `subtitle: false`, `video_structure: studio_anchor_plus_vertical_news_insert`, `media_policy: reliable_original_first_ai_demo_fallback`, three platforms, and the two approval policies.
- [ ] **Step 5: Run focused tests and lint**

```bash
pytest tests/test_models.py tests/test_config.py -q
ruff check src/avatar_pipeline/models.py src/avatar_pipeline/config.py
```

Expected: all focused tests pass and Ruff reports no errors.

- [ ] **Step 6: Commit**

```bash
git add src/avatar_pipeline/models.py src/avatar_pipeline/config.py configs/default.yaml tests/test_models.py tests/test_config.py
git commit -m "refactor: define news anchor domain models and config"
```

### Task 2: Implement fact-status and risk admission policy

**Files:**
- Create: `src/avatar_pipeline/policy.py`
- Create: `tests/test_policy.py`
- Create: `tests/fixtures/verified_hotspots.json`
- Modify: `src/avatar_pipeline/service.py`
- Test: `tests/test_service.py`

**Interfaces:**
- Produces `AdmissionDecision(status: FactStatus, publishable: bool, reasons: list[str])`.
- Produces `evaluate_candidate(candidate: TopicCandidate) -> AdmissionDecision`.
- Produces `screen_candidates(candidates: Sequence[TopicCandidate]) -> tuple[list[TopicCandidate], list[TopicCandidate]]`, returning publishable verified candidates and skipped candidates with reasons.
- Produces `rank_verified_candidates(candidates: Sequence[TopicCandidate], limit: int = 3) -> list[TopicCandidate]`.
- `DailyWorkflowService.record_research` accepts any raw research result only for screening, persists the skipped audit trail, and exposes exactly the verified ranked candidates as the formal pool; it must not require exactly three candidates when fewer than three verified candidates exist.
- A candidate with `FactStatus.PENDING`, `UNVERIFIED`, `HIGH_RISK`, or `MALICIOUS` must cause `approve_topic_script` and any managed selection method to reject it.

- [ ] **Step 1: Write failing policy tests** covering multi-source verified acceptance, pending auto-skip, single-source anonymous rejection, malicious/high-risk rejection, duplicate IDs/dedupe keys, and “no publishable topic” behavior.
- [ ] **Step 2: Run the policy tests**

```bash
pytest tests/test_policy.py tests/test_service.py -q
```

Expected: FAIL because no admission policy exists and the service still treats all three old candidates as formal options.

- [ ] **Step 3: Implement pure policy functions** with deterministic reason codes; keep platform crawling outside the policy module.
- [ ] **Step 4: Integrate screening into `record_research`** so unverified/harmful items are retained only in an audit field and never in `candidates` used for production.
- [ ] **Step 5: Add fixture data** with at least two reliable evidence items for a verified topic and explicit skipped pending/malicious examples.
- [ ] **Step 6: Run focused tests and lint**

```bash
pytest tests/test_policy.py tests/test_service.py -q
ruff check src/avatar_pipeline/policy.py src/avatar_pipeline/service.py
```

Expected: all policy and service tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/avatar_pipeline/policy.py tests/test_policy.py tests/fixtures/verified_hotspots.json src/avatar_pipeline/service.py tests/test_service.py
git commit -m "feat: enforce verified hotspot admission policy"
```

### Task 3: Add script, media-plan, and source-record contracts

**Files:**
- Create: `src/avatar_pipeline/media.py`
- Create: `tests/test_media.py`
- Modify: `src/avatar_pipeline/models.py`
- Modify: `src/avatar_pipeline/service.py`
- Modify: `skills/contracts/news-script-writer.yaml`
- Modify: `skills/contracts/news-media-planner.yaml`
- Create: `skills/contracts/news-footage-clipper.yaml`
- Create: `skills/contracts/gpt-image-2-host.yaml`
- Modify: `skills/contracts/seedance.yaml`

**Interfaces:**
- Produces `MediaKind.ORIGINAL_NEWS` and `MediaKind.AI_DEMO`.
- Produces `OriginalFootageRecord` with source reference, published time, clip start/end, usage basis, rights note, and optional mute/crop metadata.
- Produces `AIDemoRecord` with prompt, `is_factual_evidence = False`, and required disclosure text.
- Produces `MediaSegment` and `MediaPlan` validation: each non-host segment maps to a script claim, original footage has provenance, AI demo has disclosure, and timeline is non-overlapping and within the target duration.
- Produces `build_media_plan(script: NewsScript, media_items: Sequence[...]) -> MediaPlan` and `validate_media_plan(plan: MediaPlan) -> None`.
- `news-script-writer` output must distinguish fact, context, interpretation, and conclusion; include title, information bars, source IDs, disclosure requirements, and spoken text.
- `news-media-planner` output must support `anchor -> insert -> anchor -> insert -> anchor`, 9:16, source labels, AI-demo labels, and no forced subtitles.

- [ ] **Step 1: Write failing media/model tests** for provenance requirements, AI disclosure, script-claim mapping, timeline ordering, and the fixed anchor/vertical-insert structure.
- [ ] **Step 2: Run focused tests**

```bash
pytest tests/test_media.py tests/test_models.py -q
```

Expected: FAIL because the new media records and plan validators are absent.

- [ ] **Step 3: Implement media records and validation** as deterministic domain logic; do not download or generate media in this task.
- [ ] **Step 4: Add YAML skill contracts** with input schema, required outputs, no-fabrication constraints, and `real_generation_enabled: false` unless a provider is explicitly configured.
- [ ] **Step 5: Run focused tests and contract parsing tests**

```bash
pytest tests/test_media.py tests/test_skill_contracts.py -q
ruff check src/avatar_pipeline/media.py src/avatar_pipeline/models.py
```

Expected: all tests pass and all contracts load with strict validation.

- [ ] **Step 6: Commit**

```bash
git add src/avatar_pipeline/media.py tests/test_media.py src/avatar_pipeline/models.py skills/contracts/news-script-writer.yaml skills/contracts/news-media-planner.yaml skills/contracts/news-footage-clipper.yaml skills/contracts/gpt-image-2-host.yaml skills/contracts/seedance.yaml tests/test_skill_contracts.py
git commit -m "feat: model news scripts and insert media provenance"
```

### Task 4: Replace the old state machine with dual-mode gates

**Files:**
- Modify: `src/avatar_pipeline/state.py`
- Modify: `src/avatar_pipeline/service.py`
- Modify: `tests/test_state.py`
- Modify: `tests/test_service.py`

**Interfaces:**
- Defines `TaskStatus`: `INPUT_RECEIVED`, `RESEARCHING`, `FACT_SCREENED`, `TOPIC_SCRIPT_REVIEW`, `HOST_REVIEW`, `MEDIA_PLANNING`, `GENERATING_TTS`, `GENERATING_ANCHOR`, `ACQUIRING_OR_GENERATING_MEDIA`, `COMPOSITING`, `QUALITY_CHECK`, `FINAL_REVIEW`, `READY_TO_PUBLISH`, `STOPPED`.
- Defines legal transitions for both modes. Manual mode pauses only at `TOPIC_SCRIPT_REVIEW`, conditional `HOST_REVIEW`, and `FINAL_REVIEW`; managed mode uses the same internal states but moves through them with automatic gate records and no user approval request.
- Produces `approval_gate_for(target: TaskStatus) -> str | None` mapping review states to `topic_script`, `host`, and `final_video`.
- Produces service methods: `start_day`, `record_research`, `record_script_and_media_plan`, `approve_topic_script`, `approve_host`, `mark_tts_ready`, `mark_anchor_ready`, `mark_media_ready`, `mark_compositing`, `record_qc`, `approve_final_video`, and `stop_task`.
- `approve_host` is legal only when `DailyTask.requires_host_approval` is true; saved unchanged hosts bypass `HOST_REVIEW`.
- `record_qc(passed=False)` must return to generation/compositing retry states without losing source, script, or audit records.

- [ ] **Step 1: Rewrite transition tests first** for manual three-gate flow, saved-host no-gate flow, managed no-user-gate flow, illegal skips, and QC retry/stop behavior.
- [ ] **Step 2: Run the rewritten state/service tests**

```bash
pytest tests/test_state.py tests/test_service.py -q
```

Expected: FAIL because the current state machine contains separate topic/script approvals and old audio/assets states.

- [ ] **Step 3: Implement the new transition table and gate helpers**.
- [ ] **Step 4: Implement service methods with mode-aware preconditions**; retain source/skipped-candidate and artifact audit data across retries.
- [ ] **Step 5: Run focused tests, full unit tests, and lint**

```bash
pytest tests/test_state.py tests/test_service.py -q
pytest -q
ruff check src/avatar_pipeline/state.py src/avatar_pipeline/service.py
```

Expected: all tests pass; no old `approve_topic`/`approve_script` path remains as a required production flow.

- [ ] **Step 6: Commit**

```bash
git add src/avatar_pipeline/state.py src/avatar_pipeline/service.py tests/test_state.py tests/test_service.py
git commit -m "refactor: implement managed and manual workflow gates"
```

### Task 5: Add managed orchestration and skill adapters

**Files:**
- Create: `src/avatar_pipeline/orchestration.py`
- Modify: `src/avatar_pipeline/skill_contracts.py`
- Modify: `tests/test_orchestration.py`
- Modify: `tests/test_skill_contracts.py`
- Create: `skills/contracts/opinions-crawler.yaml`
- Create: `skills/contracts/news-compositor.yaml`
- Create: `skills/contracts/news-quality-control.yaml`

**Interfaces:**
- Produces protocol-style ports: `ResearchProvider`, `ScriptProvider`, `TTSProvider`, `AvatarProvider`, `MediaProvider`, `Compositor`, and `QualityController`; each returns validated Pydantic data or an explicit failure result.
- Produces `run_managed(task, providers, *, max_topic_attempts: int = 5) -> DailyTask`; it automatically skips candidates that fail fact/risk policy, retries provider failures within bounds, selects the next verified candidate, and ends in `STOPPED` with a reason when no safe candidate or usable output remains.
- Produces `advance_manual(task, action, ...) -> DailyTask` for one stage at a time, never auto-approving a user-facing manual gate.
- Skill contract loader must recognize kinds for crawler, script, host image, TTS, avatar, footage clipper, Seedance, compositor, and QC, and expose required outputs plus `real_generation_enabled`.
- `opinions-crawler` contract must support user topic/auto hot mode and source evidence; it must not imply unrestricted scraping or publication rights.
- `news-compositor` and `news-quality-control` contracts must explicitly check no-subtitle default, source/AI labels, 9:16 geometry, audio/lip-sync, and fixed structure.

- [ ] **Step 1: Write failing orchestration tests** using fake providers for: managed success, pending-first-then-verified fallback, no safe topic stop, provider retry, manual pause at topic/script, host reuse, and final-only approval.
- [ ] **Step 2: Run focused orchestration tests**

```bash
pytest tests/test_orchestration.py tests/test_skill_contracts.py -q
```

Expected: FAIL because no orchestrator ports, managed runner, or expanded skill kinds exist.

- [ ] **Step 3: Implement fake-provider-compatible ports and the managed runner**; keep provider calls injectable so tests are deterministic and external skills remain replaceable.
- [ ] **Step 4: Add and load all new Skill Contracts** with the exact required inputs/outputs and safety constraints.
- [ ] **Step 5: Run focused tests and lint**

```bash
pytest tests/test_orchestration.py tests/test_skill_contracts.py -q
ruff check src/avatar_pipeline/orchestration.py src/avatar_pipeline/skill_contracts.py
```

Expected: all tests pass and every declared contract is strictly parsed.

- [ ] **Step 6: Commit**

```bash
git add src/avatar_pipeline/orchestration.py src/avatar_pipeline/skill_contracts.py tests/test_orchestration.py tests/test_skill_contracts.py skills/contracts/opinions-crawler.yaml skills/contracts/news-compositor.yaml skills/contracts/news-quality-control.yaml
 git commit -m "feat: orchestrate managed runs through validated skill contracts"
```

### Task 6: Version JSON persistence and migrate existing tasks

**Files:**
- Modify: `src/avatar_pipeline/repository.py`
- Create: `src/avatar_pipeline/migration.py`
- Create: `tests/fixtures/legacy_task.json`
- Modify: `tests/test_repository.py`
- Modify: `tests/test_models.py`

**Interfaces:**
- Adds `schema_version: int` to persisted tasks, with the new version set to `2`.
- Produces `migrate_task_payload(payload: Mapping[str, Any]) -> dict[str, Any]` converting old topic/script/video approval records and old status values into a safe `manual` task representation without inventing fact verification or source evidence.
- Repository reads version 1/legacy JSON through the migration function, validates the result, and writes version 2 on the next save.
- Legacy tasks with old pillars are mapped to the closest news pillar only for archival display; they are not treated as verified news candidates or publishable content.

- [ ] **Step 1: Write failing repository/migration tests** for legacy load, version-2 save, preservation of artifacts and approval audit, invalid legacy data rejection, and no fabricated verification status.
- [ ] **Step 2: Run focused tests**

```bash
pytest tests/test_repository.py tests/test_models.py -q
```

Expected: FAIL because persisted tasks have no schema version and repository validation expects the old model only.

- [ ] **Step 3: Implement pure migration** with explicit defaults and an archival marker for legacy content.
- [ ] **Step 4: Update repository read/write paths** to migrate on read and persist the new schema on save.
- [ ] **Step 5: Run focused tests, full tests, and lint**

```bash
pytest tests/test_repository.py tests/test_models.py -q
pytest -q
ruff check src/avatar_pipeline/repository.py src/avatar_pipeline/migration.py
```

Expected: all tests pass and old JSON cannot bypass the new fact/risk gates.

- [ ] **Step 6: Commit**

```bash
git add src/avatar_pipeline/repository.py src/avatar_pipeline/migration.py tests/fixtures/legacy_task.json tests/test_repository.py tests/test_models.py
 git commit -m "feat: version and safely migrate persisted workflow tasks"
```

### Task 7: Update CLI and publication packaging

**Files:**
- Modify: `src/avatar_pipeline/cli.py`
- Create: `src/avatar_pipeline/publication.py`
- Create: `tests/test_publication.py`
- Modify: `tests/test_cli.py`
- Modify: `README.md`

**Interfaces:**
- CLI supports `init-day --mode {managed,manual} --topic-source {user_topic,auto_hot} [--input TEXT] [--host-image PATH]`, `status`, `import-research`, `record-plan`, `approve-topic-script`, `approve-host`, `record-artifact`, `record-qc`, `approve-final-video`, and `stop`.
- CLI outputs JSON only on stdout and actionable validation errors on stderr with exit code `2`; it must not ask interactive confirmations.
- `health` reports configured skill kinds, real-generation flags, ffmpeg/ffprobe, subtitle default, video structure, and media policy.
- Produces `PublicationPackage` with one master video path and per-platform title, description, tags, source note, and AI-demo note for Douyin, WeChat Channels, and Xiaohongshu.
- `build_publication_package(task) -> PublicationPackage` must use the same master video path for all three platforms and must fail if the task is not `READY_TO_PUBLISH` or source/disclosure records are incomplete.

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

### Task 8: Add end-to-end acceptance coverage and release verification

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
