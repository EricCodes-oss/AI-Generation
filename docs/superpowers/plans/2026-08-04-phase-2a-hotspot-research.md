# Phase 2A Hotspot Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first Skill-gated stage that creates a daily research plan, imports and normalizes 30–40 cross-platform hotspot sources, records 5–8 A-grade comment insight cards, renders a reviewable research report, and waits for explicit user approval before any clustering or Top 3 work.

**Architecture:** Keep Phase 1's `DailyTask` production state machine intact and add a separate versioned research-run aggregate under each day. Project-owned business Skills are stored as auditable `SKILL.md` bundles; third-party collectors are pinned in a lock manifest and invoked only through failure-tolerant adapter interfaces. V1 executes fixture/manual imports first, then capability probes and small real-platform trials; it never silently manufactures missing sources or advances to clustering without approval.

**Tech Stack:** Python 3.11, Pydantic 2, PyYAML, JSON/Markdown artifacts, pytest, Ruff, Node.js 22 for OpenCLI-based third-party collectors, Chrome/Chromium for logged-in platform access.

## Global Constraints

- Exactly one daily production task; this phase produces research artifacts only and must not generate Top 3 topics or scripts.
- Every important step returns a reviewable artifact and remains `waiting_for_user_approval` until the user approves it.
- Daily target: 30–40 valid sources; 5–8 A-grade sources receive comment analysis; each A-grade source targets 20–40 valid comments.
- Time distribution: 72 hours 50%, 7 days 35%, 30 days 15%.
- Generate 9 core query groups per day: 3 per content pillar; allow at most 3 dynamic expansion groups.
- Core platforms: Douyin 8–10, WeChat Channels 6–8, Xiaohongshu 8–10; supplementary sources 7–11 combined.
- Preserve provenance, timestamps, raw artifact paths, collection method, missing fields, failures, and confidence.
- Do not copy full viral scripts or large comment blocks; collect topic, emotion, situation, need, structure, and interaction evidence.
- Do not compare raw engagement counts directly across platforms.
- Do not include the excluded eldercare/caregiving pillar.
- Do not diagnose psychological conditions or infer unknown personal attributes from comments.
- Do not bypass platform restrictions; logged-in browser assistance and manual import are valid degradations.
- Pin every third-party Skill to repository, path, and commit before installation; audit its scripts, dependencies, environment variables, network behavior, and write paths.
- Do not run the formal daily workflow or enable unattended collection during this plan.

---

## File Map

### Project-owned Skills

- Create: `skills/daily-hotspot-research/SKILL.md` — orchestration instructions and user gate for the whole first stage.
- Create: `skills/hotspot-query-planner/SKILL.md` — nine query groups, history cooldowns, and dynamic expansion rules.
- Create: `skills/channels-hotspot-research/SKILL.md` — browser-assisted/manual WeChat Channels research procedure.
- Create: `skills/hotspot-source-recorder/SKILL.md` — normalization and provenance rules.
- Create: `skills/audience-comment-insight/SKILL.md` — comment sampling, insight extraction, privacy, and confidence rules.
- Create: `skills/*/references/*.md` only when a Skill would otherwise exceed the concise core workflow; no README files inside Skill bundles.

### Third-party Skill governance

- Create: `skills/third_party.lock.yaml` — exact source repository, commit, path, install state, and audit state for `opinions-crawler` and `wechat-article-search`.
- Create: `skills/audits/opinions-crawler.md` — dependency, command, permission, failure-mode, and platform-coverage audit.
- Create: `skills/audits/wechat-article-search.md` — interface and dependency audit.
- Create: `scripts/verify_research_skills.py` — deterministic manifest and local prerequisite validation; no live collection.
- Create: `tests/test_research_skill_manifest.py` — lock and audit validation tests.

### Research domain and persistence

- Create: `src/avatar_pipeline/research_models.py` — source, query plan, comment insight, report, run state, review action, and validation models.
- Create: `src/avatar_pipeline/research_repository.py` — atomic UTF-8 persistence for research runs and artifacts under `workspace/days/YYYY-MM-DD/research/`.
- Create: `tests/test_research_models.py`.
- Create: `tests/test_research_repository.py`.

### Planning, normalization, collection, and report

- Create: `src/avatar_pipeline/query_planner.py` — deterministic query rotation, cooldown, and expansion-limit logic.
- Create: `src/avatar_pipeline/research_adapters.py` — collector protocol, fixture/manual adapters, command adapter seam, and failure result.
- Create: `src/avatar_pipeline/source_normalizer.py` — platform aliases, numeric parsing, required provenance, and raw artifact preservation.
- Create: `src/avatar_pipeline/comment_insights.py` — deterministic validation, sampling labels, insight-card assembly, and confidence calculation.
- Create: `src/avatar_pipeline/research_report.py` — JSON and Markdown report renderer.
- Create: `src/avatar_pipeline/research_service.py` — stage orchestration, revisions, approval gate, and no-advance invariant.
- Create: `tests/test_query_planner.py`.
- Create: `tests/test_research_adapters.py`.
- Create: `tests/test_source_normalizer.py`.
- Create: `tests/test_comment_insights.py`.
- Create: `tests/test_research_report.py`.
- Create: `tests/test_research_service.py`.

### CLI, configuration, fixtures, and operations

- Modify: `src/avatar_pipeline/config.py` — research target and time-window configuration.
- Modify: `configs/default.yaml` — fixed Phase 2A research constraints.
- Modify: `src/avatar_pipeline/cli.py` — research plan/import/report/review/status/health commands.
- Create: `tests/fixtures/research/manual_sources.json` — 30 deterministic normalized/importable sample sources covering all required platforms and pillars.
- Create: `tests/fixtures/research/comment_insights.json` — 5 deterministic A-grade insight cards.
- Modify: `tests/test_config.py`.
- Modify: `tests/test_cli.py`.
- Create: `docs/operations/phase-2a-hotspot-research-runbook.md` — fixture run, prerequisite checks, manual import, real trial safety, review actions, and recovery.

---

### Task 1: Pin and Audit Third-party Research Skills

**Files:**
- Create: `skills/third_party.lock.yaml`
- Create: `skills/audits/opinions-crawler.md`
- Create: `skills/audits/wechat-article-search.md`
- Create: `scripts/verify_research_skills.py`
- Create: `tests/test_research_skill_manifest.py`

**Interfaces:**
- Consumes: the user-selected repositories and paths for `opinions-crawler` and `wechat-article-search`.
- Produces: `verify_manifest(project_root: Path) -> VerificationReport`, where `VerificationReport.ok` is false for missing pins, missing audit files, unsupported runtime, missing Chrome, or unresolved install paths.
- Produces lock entries with keys: `name`, `repository`, `commit`, `path`, `role`, `install_path`, `installed`, `audit_path`, `requires`, and `real_calls_enabled`.

- [ ] **Step 1: Write failing manifest tests**

Create tests that require both lock entries, a 40-character commit pin, existing audit paths, `real_calls_enabled: false`, Node.js minimum `20`, and Chrome as a declared prerequisite. Test `verify_manifest()` with a fake executable resolver so the test is deterministic.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
python -m pytest tests/test_research_skill_manifest.py -v
```

Expected: FAIL because the lock manifest and verifier do not exist.

- [ ] **Step 3: Fetch third-party Skill sources into a temporary audit directory**

Use the pinned WorkBuddySkills commit already selected in the design discussion for `opinions-crawler`; resolve the exact repository/path/commit for `wechat-article-search`. Read every referenced executable or setup script before installation. Do not copy third-party Skill contents into Git history unless its license and update method are explicitly recorded.

- [ ] **Step 4: Write the lock manifest and audit reports**

Record exact commands, required logins, environment variables, expected JSON outputs, rate limits, platform coverage, known failure modes, filesystem writes, network destinations, and whether the Skill can be installed safely. Explicitly record that Douyin general search/comment coverage and WeChat Channels coverage are not assumed.

- [ ] **Step 5: Implement the minimal verifier**

The verifier must validate YAML structure, audit-file existence, Node major version, Chrome existence, declared install path, and keep live-call readiness separate from local prerequisite readiness. It must not log into platforms or call a live collector.

- [ ] **Step 6: Run focused tests and local verification**

Run:

```bash
python -m pytest tests/test_research_skill_manifest.py -v
python scripts/verify_research_skills.py --project-root .
```

Expected: tests PASS; command reports each prerequisite and clearly distinguishes `installed`, `locally_ready`, and `real_calls_enabled`.

- [ ] **Step 7: Commit**

```bash
git add skills/third_party.lock.yaml skills/audits scripts/verify_research_skills.py tests/test_research_skill_manifest.py
git commit -m "chore: pin and audit research skills"
```

---

### Task 2: Create the Five Project-owned Research Skill Bundles

**Files:**
- Create: `skills/daily-hotspot-research/SKILL.md`
- Create: `skills/hotspot-query-planner/SKILL.md`
- Create: `skills/channels-hotspot-research/SKILL.md`
- Create: `skills/hotspot-source-recorder/SKILL.md`
- Create: `skills/audience-comment-insight/SKILL.md`
- Create: `tests/test_project_research_skills.py`

**Interfaces:**
- Consumes: the approved Skill-gated design document.
- Produces: five discoverable Skill bundles with YAML frontmatter `name` and `description`, explicit inputs, outputs, quality gates, prohibited behavior, failure degradation, and user actions.
- `daily-hotspot-research` may invoke only the other four project Skills plus pinned collectors named in `skills/third_party.lock.yaml`.

- [ ] **Step 1: Write failing structural and policy tests**

Test that each Skill exists, frontmatter name matches its directory, and required phrases/sections express: no Top 3, no script writing, provenance, user approval, platform failure disclosure, and eldercare exclusion where relevant.

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
python -m pytest tests/test_project_research_skills.py -v
```

Expected: FAIL because the Skill bundles do not exist.

- [ ] **Step 3: Run baseline pressure scenarios without the new Skills**

Document at least one failing behavior per Skill, such as: planning only generic “心灵鸡汤” queries, hiding a failed platform, copying complete comments, inferring user demographics, or advancing directly to Top 3. Save only concise evidence in the test file or a fixture; do not create auxiliary README documents.

- [ ] **Step 4: Write minimal SKILL.md files**

Keep each core Skill concise. Move keyword packs, source schema, comment taxonomy, and report template to one-level `references/` files only if necessary. The orchestrator Skill must end by presenting the report and waiting for one of the approved user actions.

- [ ] **Step 5: Re-run structural tests and pressure scenarios**

Run:

```bash
python -m pytest tests/test_project_research_skills.py -v
```

Expected: PASS; each pressure scenario is explicitly prevented by the relevant Skill instruction.

- [ ] **Step 6: Commit**

```bash
git add skills/daily-hotspot-research skills/hotspot-query-planner skills/channels-hotspot-research skills/hotspot-source-recorder skills/audience-comment-insight tests/test_project_research_skills.py
git commit -m "feat: add hotspot research skill bundles"
```

---

### Task 3: Define Research Domain Models and Validation

**Files:**
- Create: `src/avatar_pipeline/research_models.py`
- Create: `tests/test_research_models.py`

**Interfaces:**
- Produces enums: `ResearchRunStatus`, `ResearchReviewAction`, `ResearchGrade`, `ResearchPlatform`, `TimeWindow`, `ConfidenceLevel`, `CommentSampleType`, `ImplicitNeed`.
- Produces models: `QueryGroup`, `DailyResearchPlan`, `EngagementMetrics`, `ResearchSource`, `CommentInsightCard`, `CollectionFailure`, `ResearchReportSummary`, `SkillExecutionRecord`, and `ResearchRun`.
- `ResearchRun` owns revisions and must not contain `TopicCandidate` or script fields.

- [ ] **Step 1: Write model tests for confirmed constraints**

Cover exactly 9 core query groups, 3 per pillar, at most 3 expansion groups, time shares summing to 1.0, grades A/B/C, required provenance, unknown metrics as `None`, unique source IDs, 5–8 A-grade insight cards for an approvable run, and rejection of the eldercare pillar.

- [ ] **Step 2: Run model tests and verify RED**

Run:

```bash
python -m pytest tests/test_research_models.py -v
```

Expected: FAIL on missing module/classes.

- [ ] **Step 3: Implement strict Pydantic models**

Use `extra="forbid"`, aware timestamps, `HttpUrl | None` or string URLs as appropriate for platform deep links, and explicit validators. Separate “draft may be incomplete” from `is_approvable()` so partial platform results can be persisted without pretending they meet approval thresholds.

- [ ] **Step 4: Run focused tests**

Run:

```bash
python -m pytest tests/test_research_models.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/avatar_pipeline/research_models.py tests/test_research_models.py
git commit -m "feat: define hotspot research models"
```

---

### Task 4: Add Atomic Research Persistence and Revision History

**Files:**
- Create: `src/avatar_pipeline/research_repository.py`
- Create: `tests/test_research_repository.py`

**Interfaces:**
- Consumes: `ResearchRun` from Task 3.
- Produces: `ResearchRunRepository(workspace: Path)` with `create(day)`, `get(day)`, `save(run)`, `save_revision(run)`, `write_artifact(day, relative_path, payload)`, and `list_recent_plans(before_day, days=30)`.
- Persists: `workspace/days/YYYY-MM-DD/research/run.json`, `revisions/revision-N.json`, `raw/`, and `reports/`.

- [ ] **Step 1: Write failing repository tests**

Cover UTF-8 round trip, atomic replacement, immutable numbered revisions, missing-run error, duplicate create error, path traversal rejection, and 30-day plan-history ordering.

- [ ] **Step 2: Run repository tests and verify RED**

Run:

```bash
python -m pytest tests/test_research_repository.py -v
```

Expected: FAIL because repository is missing.

- [ ] **Step 3: Implement minimal repository**

Follow the existing `DailyTaskRepository` atomic JSON pattern without modifying its storage. Validate every artifact relative path remains under the day's research directory.

- [ ] **Step 4: Run focused and regression tests**

Run:

```bash
python -m pytest tests/test_research_repository.py tests/test_repository.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/avatar_pipeline/research_repository.py tests/test_research_repository.py
git commit -m "feat: persist versioned research runs"
```

---

### Task 5: Implement the Daily Query Planner

**Files:**
- Create: `src/avatar_pipeline/query_planner.py`
- Create: `tests/test_query_planner.py`
- Modify: `src/avatar_pipeline/config.py`
- Modify: `configs/default.yaml`
- Modify: `tests/test_config.py`

**Interfaces:**
- Consumes: `AppConfig.research`, execution date, prior `DailyResearchPlan` objects, and optional user emphasis/exclusions.
- Produces: `build_daily_plan(day, config, history, user_directive=None) -> DailyResearchPlan`.
- Produces: `expand_plan(plan, discovered_terms) -> DailyResearchPlan`, capped at 3 expansions with recorded parent query and reason.

- [ ] **Step 1: Write failing config and planner tests**

Assert 9 groups, 3 per pillar, platform-aware expressions, 7-day exact-query cooldown, 3-day scene cooldown, 30-day produced-topic de-prioritization, 14-day cooldown after two empty runs, expansion cap 3, eldercare exclusion, and 50/35/15 windows.

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
python -m pytest tests/test_config.py tests/test_query_planner.py -v
```

Expected: FAIL on missing research config/planner.

- [ ] **Step 3: Add fixed research configuration**

Add strict models for platform targets, time shares, query counts, expansion cap, comment targets, and excluded topics. Put the approved values in `configs/default.yaml`.

- [ ] **Step 4: Implement deterministic planner logic**

Use curated project keyword packs grouped by pillar, scene, emotion, and natural-language query. Use the execution date as a deterministic rotation seed so fixture tests are repeatable. Do not call an LLM in this task.

- [ ] **Step 5: Run focused tests**

Run:

```bash
python -m pytest tests/test_config.py tests/test_query_planner.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/avatar_pipeline/query_planner.py src/avatar_pipeline/config.py configs/default.yaml tests/test_query_planner.py tests/test_config.py
git commit -m "feat: plan daily hotspot queries"
```

---

### Task 6: Build Collector Adapters and Graceful Failure Results

**Files:**
- Create: `src/avatar_pipeline/research_adapters.py`
- Create: `tests/test_research_adapters.py`

**Interfaces:**
- Produces protocol: `ResearchCollector.collect(plan: DailyResearchPlan) -> CollectionBatch`.
- Produces: `FixtureCollector`, `ManualImportCollector`, and `CommandCollector`.
- `CollectionBatch` contains `raw_items`, `failures`, `collector_name`, `started_at`, `completed_at`, and `raw_artifact_paths`.
- `CommandCollector` accepts an injected runner and must never use `shell=True`.

- [ ] **Step 1: Write failing adapter tests**

Cover JSON object/list input, UTF-8 content, per-platform partial success, timeout/non-zero/invalid JSON as `CollectionFailure`, command argument arrays, and preservation of raw output paths.

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
python -m pytest tests/test_research_adapters.py -v
```

Expected: FAIL on missing adapters.

- [ ] **Step 3: Implement fixture and manual adapters first**

These are the default executable adapters for Phase 2A. They must allow a complete first-stage fixture run without network or platform login.

- [ ] **Step 4: Implement the command seam without enabling real calls**

Load command templates only from the audited lock/config; capture stdout/stderr, enforce timeouts and rate-delay metadata, and return failures instead of aborting the full batch.

- [ ] **Step 5: Run focused tests**

Run:

```bash
python -m pytest tests/test_research_adapters.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/avatar_pipeline/research_adapters.py tests/test_research_adapters.py
git commit -m "feat: add resilient research collectors"
```

---

### Task 7: Normalize Sources and Preserve Provenance

**Files:**
- Create: `src/avatar_pipeline/source_normalizer.py`
- Create: `tests/test_source_normalizer.py`

**Interfaces:**
- Consumes: adapter `raw_items` plus collector/query context.
- Produces: `normalize_source(raw, context) -> ResearchSource` and `normalize_batch(batch, context) -> NormalizationResult`.
- `NormalizationResult` separates valid sources, rejected items, warnings, and missing metric fields.

- [ ] **Step 1: Write failing normalization tests**

Cover platform aliases, Chinese units such as `1.2万`, missing views as `None`, timezone-aware timestamps, stable source IDs, required `collected_at`, query provenance, raw artifact path, duplicate source-ID warning, and rejection of blank/untraceable records.

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
python -m pytest tests/test_source_normalizer.py -v
```

Expected: FAIL on missing normalizer.

- [ ] **Step 3: Implement minimal normalizer**

Do not calculate cross-platform ranking scores. Preserve all available raw metrics and warnings. Summaries may be imported but full source copy must be stored only in raw artifacts, not repeated in the review report.

- [ ] **Step 4: Run focused tests**

Run:

```bash
python -m pytest tests/test_source_normalizer.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/avatar_pipeline/source_normalizer.py tests/test_source_normalizer.py
git commit -m "feat: normalize hotspot sources"
```

---

### Task 8: Validate Comment Samples and Build Insight Cards

**Files:**
- Create: `src/avatar_pipeline/comment_insights.py`
- Create: `tests/test_comment_insights.py`

**Interfaces:**
- Consumes: a source ID, comment samples already labeled or manually curated by type, and extracted insight fields.
- Produces: `build_insight_card(...) -> CommentInsightCard`, `classify_confidence(card) -> ConfidenceLevel`, and validation warnings.
- This task validates and structures insights; it does not diagnose users or use a generic sentiment-only score.

- [ ] **Step 1: Write failing comment insight tests**

Cover invalid comment removal, five sample types, 20–40 target range warnings, up-to-60 focused deep dive, implicit-needs enum, unknown identity fields, counter-opinion requirement, confidence thresholds, privacy-field rejection, and high-risk flags for self-harm/domestic violence/illegality.

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
python -m pytest tests/test_comment_insights.py -v
```

Expected: FAIL on missing module.

- [ ] **Step 3: Implement deterministic validators and card builder**

Do not add an LLM dependency. Accept human/Skill-produced structured insights, validate them, compute counts/confidence, and prevent unsupported inferences. Keep short representative expressions optional and capped.

- [ ] **Step 4: Run focused tests**

Run:

```bash
python -m pytest tests/test_comment_insights.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/avatar_pipeline/comment_insights.py tests/test_comment_insights.py
git commit -m "feat: validate audience comment insights"
```

---

### Task 9: Render the Daily Research Report

**Files:**
- Create: `src/avatar_pipeline/research_report.py`
- Create: `tests/test_research_report.py`

**Interfaces:**
- Consumes: `ResearchRun` with plan, sources, failures, and insight cards.
- Produces: `render_report_markdown(run) -> str` and `build_report_summary(run) -> ResearchReportSummary`.
- Report sections: collection explanation, per-platform sources, A-grade comment cards, preliminary cross-platform signals, risks/gaps, and user decision actions.

- [ ] **Step 1: Write failing report tests**

Require all six sections, platform success/failure counts, time-window labels, provenance references, confidence labels, no Top 3 ranking, no script text, no raw cross-platform comparison table, and no long copied source/comment bodies.

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
python -m pytest tests/test_research_report.py -v
```

Expected: FAIL on missing renderer.

- [ ] **Step 3: Implement Markdown and summary rendering**

Render concise content cards and source references. Clearly label observations as preliminary signals and failures as coverage gaps.

- [ ] **Step 4: Run focused tests**

Run:

```bash
python -m pytest tests/test_research_report.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/avatar_pipeline/research_report.py tests/test_research_report.py
git commit -m "feat: render daily hotspot report"
```

---

### Task 10: Implement the Research Skill Gate and Revision Loop

**Files:**
- Create: `src/avatar_pipeline/research_service.py`
- Create: `tests/test_research_service.py`

**Interfaces:**
- Consumes: `ResearchRunRepository`, planner, collectors, normalizer, comment-card inputs, and report renderer.
- Produces methods: `start(day)`, `record_plan(day, plan)`, `import_collection(day, batch)`, `record_insights(day, cards)`, `render_report(day)`, `request_revision(day, feedback, action)`, `approve(day, actor, accepted_gaps=None)`, and `status(day)`.
- Approval produces a frozen approved revision but does not create Top 3 candidates or move the Phase 1 `DailyTask` to `RESEARCHED`.

- [ ] **Step 1: Write failing service tests**

Cover legal status progression, report-before-approval, explicit user actor, rejected premature approval, accepted documented gaps, revision increment without overwriting approved versions, platform补充 action, topic补充 action, comment recollection action, save/resume, and invariant that no `TopicCandidate` is produced.

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
python -m pytest tests/test_research_service.py -v
```

Expected: FAIL on missing service.

- [ ] **Step 3: Implement minimal orchestration**

Keep workflow actions explicit. Approval eligibility uses the run's `is_approvable()` plus optional user-accepted gaps, always recorded in the approval entry.

- [ ] **Step 4: Run focused tests**

Run:

```bash
python -m pytest tests/test_research_service.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/avatar_pipeline/research_service.py tests/test_research_service.py
git commit -m "feat: gate hotspot research approval"
```

---

### Task 11: Add CLI Commands, Fixtures, and End-to-End Fixture Smoke Test

**Files:**
- Modify: `src/avatar_pipeline/cli.py`
- Modify: `tests/test_cli.py`
- Create: `tests/fixtures/research/manual_sources.json`
- Create: `tests/fixtures/research/comment_insights.json`
- Create: `tests/test_research_fixture_flow.py`

**Interfaces:**
- Adds commands:
  - `research-init --date`
  - `research-plan --date`
  - `research-import --date --file --collector`
  - `research-import-insights --date --file`
  - `research-report --date`
  - `research-revise --date --action --feedback`
  - `research-approve --date --actor [--accept-gap ...]`
  - `research-status --date`
  - `research-health`
- JSON remains the machine-readable stdout contract; Markdown report is written under the day's `research/reports/` directory.

- [ ] **Step 1: Create deterministic fixtures**

Include 30 sources across Douyin, WeChat Channels, Xiaohongshu, and supplementary platforms; cover all three pillars and all time windows. Include 5 valid A-grade insight cards and at least one documented platform/metric warning.

- [ ] **Step 2: Write failing CLI and fixture-flow tests**

Exercise the complete first-stage loop from init to plan, import, insights, report, revision, regenerated report, and approval. Assert the existing `import-topics` command remains separate and no Top 3 appears in research output.

- [ ] **Step 3: Run tests and verify RED**

Run:

```bash
python -m pytest tests/test_cli.py tests/test_research_fixture_flow.py -v
```

Expected: FAIL on unknown research commands.

- [ ] **Step 4: Implement CLI commands and JSON loaders**

Reuse the existing CLI error boundary. Reject malformed fixtures with actionable errors and preserve UTF-8 output.

- [ ] **Step 5: Run focused tests and a manual smoke command sequence**

Run:

```bash
python -m pytest tests/test_cli.py tests/test_research_fixture_flow.py -v
rm -rf /tmp/avatar-research-smoke
python -m avatar_pipeline.cli --workspace /tmp/avatar-research-smoke research-init --date 2026-08-04
python -m avatar_pipeline.cli --workspace /tmp/avatar-research-smoke research-plan --date 2026-08-04
python -m avatar_pipeline.cli --workspace /tmp/avatar-research-smoke research-import --date 2026-08-04 --collector fixture --file tests/fixtures/research/manual_sources.json
python -m avatar_pipeline.cli --workspace /tmp/avatar-research-smoke research-import-insights --date 2026-08-04 --file tests/fixtures/research/comment_insights.json
python -m avatar_pipeline.cli --workspace /tmp/avatar-research-smoke research-report --date 2026-08-04
python -m avatar_pipeline.cli --workspace /tmp/avatar-research-smoke research-approve --date 2026-08-04 --actor owner
```

Expected: all commands exit 0; final status is approved; no daily Top 3 task state is modified.

- [ ] **Step 6: Commit**

```bash
git add src/avatar_pipeline/cli.py tests/test_cli.py tests/test_research_fixture_flow.py tests/fixtures/research
git commit -m "feat: expose hotspot research workflow"
```

---

### Task 12: Install Verified Collectors and Run Capability-only Probes

**Files:**
- Modify: `skills/third_party.lock.yaml`
- Modify: `skills/audits/opinions-crawler.md`
- Modify: `skills/audits/wechat-article-search.md`
- Modify: `scripts/verify_research_skills.py`
- Modify: `tests/test_research_skill_manifest.py`

**Interfaces:**
- Consumes: audit-approved installation commands from Task 1.
- Produces: pinned local installation paths and capability probe results without performing broad content collection.

- [ ] **Step 1: Install each audited Skill at its pinned commit**

Use the Skill installer or an audited sparse checkout. Do not execute login, publishing, or broad collection commands during installation. Record the resolved install path and checksum/commit in the lock file.

- [ ] **Step 2: Verify Node, Chrome, OpenCLI/CLI binaries, and extension/login prerequisites separately**

Report each prerequisite as `ready`, `missing`, or `manual_action_required`. Never report a platform as collection-ready solely because the Skill directory exists.

- [ ] **Step 3: Run non-destructive capability probes**

Use `--help`, version, auth-status, or equivalent commands only. If an auth-status command has side effects or is undocumented, skip it and record the limitation.

- [ ] **Step 4: Update tests for installed paths and readiness separation**

Run:

```bash
python -m pytest tests/test_research_skill_manifest.py -v
python scripts/verify_research_skills.py --project-root .
```

Expected: manifest tests PASS; verifier accurately reports any remaining extension/login requirements.

- [ ] **Step 5: Commit**

```bash
git add skills/third_party.lock.yaml skills/audits scripts/verify_research_skills.py tests/test_research_skill_manifest.py
git commit -m "chore: install verified research collectors"
```

---

### Task 13: Write Operations Runbook and Verify Phase 2A

**Files:**
- Create: `docs/operations/phase-2a-hotspot-research-runbook.md`
- Modify: `README.md`

**Interfaces:**
- Documents: fixture-only flow, third-party readiness checks, browser/login manual actions, manual WeChat Channels import, user review actions, revision behavior, failure recovery, privacy/copyright rules, and the boundary before clustering/Top 3.

- [ ] **Step 1: Write the runbook using verified command names**

Include exact expected workspace paths and explain that a successful fixture run proves orchestration, not live-platform access.

- [ ] **Step 2: Add a concise README pointer**

Link Phase 1 and Phase 2A runbooks without duplicating their content.

- [ ] **Step 3: Run complete verification**

Run:

```bash
python -m pytest -q
python -m pytest --cov=avatar_pipeline --cov-report=term-missing
python -m ruff check .
git diff --check
python scripts/verify_research_skills.py --project-root .
```

Expected: all tests PASS; coverage remains at or above 85%; Ruff and diff check pass; Skill verifier reports truthful readiness states.

- [ ] **Step 4: Verify no scope leakage**

Search the implementation and fixture report to confirm Phase 2A does not create Top 3 candidates or scripts:

```bash
rg -n "TopicCandidate|script_text|life-companion-scriptwriter" src/avatar_pipeline/research_* src/avatar_pipeline/query_planner.py src/avatar_pipeline/source_normalizer.py src/avatar_pipeline/comment_insights.py tests/test_research_* tests/fixtures/research
```

Expected: only explicit negative assertions/documentation, not production creation of Top 3 or scripts.

- [ ] **Step 5: Commit**

```bash
git add docs/operations/phase-2a-hotspot-research-runbook.md README.md
git commit -m "docs: add hotspot research runbook"
```

- [ ] **Step 6: Push the completed branch after final review**

Run:

```bash
git status --short --branch
git log --oneline --decorate -15
git push origin HEAD:main
```

Expected: clean branch and remote `main` updated to the verified Phase 2A commit.
