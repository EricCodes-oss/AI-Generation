# Editorial Opportunity v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dual-funnel news intelligence workflow that separates attention signals from factual evidence, rejects weak or unsafe topics, scores editorial value out of 100, and returns a dynamic director-reviewed candidate list without padding.

**Architecture:** Add focused v2 domain models, an auditable scorer/gate, a source-adapter registry, and a director topic-card renderer. Integrate them through versioned configuration while preserving the existing `viral-v1.1` pipeline and user-selection gate.

**Tech Stack:** Python 3.11+, Pydantic v2, PyYAML, pytest, Ruff, existing `avatar_pipeline` domain/config/report conventions.

## Global Constraints

- New rule version is exactly `editorial-opportunity-v2.0`.
- Score weights are exactly `30 + 35 + 20 + 15 = 100`.
- Attention signals must never satisfy factual-evidence requirements.
- User-visible qualified candidate count is dynamic, capped at 8, and may be below 3.
- Weak candidates must never be added only to satisfy category or quantity targets.
- User topic selection remains mandatory before production.
- Existing `viral-v1.1` serialized models and tests remain compatible.
- External GPL/AGPL projects are service/API references only; their code is not copied.
- External adapters are optional and must define a fallback path.

---

## File Structure

- Create `src/avatar_pipeline/news_intelligence_models.py`: v2 evidence, score, rejection, opportunity, pool, and director-card contracts.
- Create `src/avatar_pipeline/editorial_opportunity.py`: hard-rejection evaluation, 100-point score calculation, grading, ranking, and dynamic pool construction.
- Create `src/avatar_pipeline/source_registry.py`: typed registry of domestic, authority, search, social, video, and vertical source adapters.
- Create `src/avatar_pipeline/editorial_opportunity_report.py`: Markdown director-topic-card report.
- Modify `src/avatar_pipeline/config.py`: versioned v2 scoring/selection/source configuration while retaining v1 parsing.
- Modify `configs/default.yaml`: activate `editorial-opportunity-v2.0` and configure dynamic pool plus source registry.
- Modify `src/avatar_pipeline/hotspot_selection.py` and `src/avatar_pipeline/cli.py`: preserve the user-selection hard gate and expose v2 report/build commands only where existing command structure permits.
- Modify `README.md`, `docs/runbooks/manual-hotspot-sampling.md`, and `docs/runbooks/manual-news-v5-production.md`: document candidate-first workflow and automatic downstream execution after topic confirmation.
- Add `tests/test_news_intelligence_models.py`, `tests/test_editorial_opportunity.py`, `tests/test_source_registry.py`, and `tests/test_editorial_opportunity_report.py`.
- Modify `tests/test_config.py`, `tests/test_cli.py`, and end-to-end hotspot tests for v2 defaults and v1 compatibility.

### Task 1: Define auditable v2 contracts

**Interfaces:**
- Produces `AttentionSignal`, `FactEvidence`, `FootageAssessment`, `EditorialOpportunityScore`, `EditorialOpportunity`, `EditorialOpportunityPool`, and `DirectorTopicCard`.
- Enforces unique IDs, evidence-role separation, exact 100-point maximums, dynamic list size 0—8, and grade/status consistency.

- [ ] Write failing model tests for evidence separation, score bounds, dynamic pools, no-S-tier status, and complete director-card fields.
- [ ] Run `PYTHONPATH="$(pwd):$(pwd)/src" .venv/bin/pytest -q tests/test_news_intelligence_models.py` and confirm collection/import failure.
- [ ] Implement the minimal Pydantic models and validators in `news_intelligence_models.py`.
- [ ] Re-run the model tests and confirm they pass.
- [ ] Review serialization names against the design spec.

### Task 2: Implement hard gates and the 100-point scorer

**Interfaces:**
- Consumes `EditorialOpportunity` evidence inputs from Task 1.
- Produces `evaluate_rejections(opportunity, policy)`, `score_opportunity(opportunity, weights)`, `grade_opportunity(...)`, and `build_opportunity_pool(...)`.

- [ ] Write failing tests for single-platform heat, first-party breaking-news watch exception, missing facts, recycled old news, unresolved conflicts, marketing-only spread, no relevant footage, score totals, outlier/velocity effects, ranking, and no-padding behavior.
- [ ] Run the focused test file and confirm failures.
- [ ] Implement deterministic rejection and scoring rules with component explanations.
- [ ] Run focused tests and confirm green.
- [ ] Add a fixture-based v2 end-to-end test from evidence to user-selection-ready pool.

### Task 3: Add source adapter registry

**Interfaces:**
- Produces `SourceAdapterSpec`, `SourceRegistry`, and `build_default_source_registry()`.
- Every adapter declares evidence roles, acquisition mode, reliability tier, credential need, experimental flag, license note, and fallback.

- [ ] Write failing tests for required source groups, authority roles, optional X/YouTube/Trends adapters, GPL/AGPL service-only notes, and mandatory fallback validation.
- [ ] Run focused tests and confirm failures.
- [ ] Implement registry models and default registrations.
- [ ] Re-run focused tests and confirm pass.

### Task 4: Render director topic cards

**Interfaces:**
- Consumes `EditorialOpportunityPool`.
- Produces `render_editorial_opportunity_report(pool) -> str` with top-level S-tier status, ordered topic cards, score breakdown, heat evidence, fact evidence, footage risks, lifetime, hook, payoff, and rejection/watch reasons.

- [ ] Write failing snapshot-style assertions for S-tier and no-S-tier reports.
- [ ] Run focused tests and confirm failures.
- [ ] Implement Markdown rendering without platform names in proposed narration text.
- [ ] Re-run report tests and confirm pass.

### Task 5: Version configuration and preserve v1 compatibility

**Interfaces:**
- Extends `HotspotConfig.rule_version` to accept both versions.
- Adds v2 weights, thresholds, dynamic candidate settings, hard-rejection toggles, and source registry policy.
- Existing v1 fixture/config parsing remains valid.

- [ ] Update tests first to expect v2 defaults, exact weight totals, 0—8 dynamic pool, no-padding, required authority sources, and explicit v1 compatibility.
- [ ] Run configuration tests and confirm failures.
- [ ] Implement versioned config models and migrate `configs/default.yaml`.
- [ ] Re-run configuration tests and confirm pass.

### Task 6: Integrate manual workflow and CLI/report entry points

**Interfaces:**
- Reuses current selection confirmation gate.
- Adds a fixture-driven CLI entry point that writes v2 JSON and Markdown reports without starting production.
- Topic confirmation remains required; after confirmation the existing V5 production workflow can continue without intermediate approvals.

- [ ] Write failing CLI and workflow tests for report generation, dynamic candidates, no-S-tier output, and selection blocking.
- [ ] Run focused tests and confirm failures.
- [ ] Implement the narrowest compatible integration in existing service/CLI modules.
- [ ] Re-run focused and hotspot end-to-end tests.

### Task 7: Update operating documentation

- [ ] Update README and hotspot runbook with six signal classes, two-funnel review, director-card fields, no-padding behavior, source reliability, and user confirmation.
- [ ] Update V5 production runbook with lessons from the Pang Dong Lai and Odyssey videos: strong contradiction/knowledge gap, variable B-roll count, fewer longer coherent blocks, and footage quality/era checks.
- [ ] Document optional external integrations and licensing boundaries.
- [ ] Run `git diff --check` for documentation formatting.

### Task 8: Full verification

- [ ] Run `PYTHONPATH="$(pwd):$(pwd)/src" .venv/bin/pytest -q` and require zero failures.
- [ ] Run `git ls-files '*.py' -z | xargs -0 .venv/bin/ruff check` and require zero errors.
- [ ] Run `git diff --check` and require zero whitespace errors.
- [ ] Run the v2 fixture CLI/demo and inspect generated JSON/Markdown artifacts.
- [ ] Review `git diff --stat` and `git status --short` to ensure no unrelated files were reverted.
