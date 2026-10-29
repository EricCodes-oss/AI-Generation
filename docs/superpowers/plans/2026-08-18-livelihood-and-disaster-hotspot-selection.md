# Livelihood and Disaster Hotspot Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add auditable livelihood-priority scoring and an authoritative major-disaster fast lane to the existing V5 hotspot candidate workflow, then run it for August 18, 2026.

**Architecture:** Extend the existing Pydantic candidate contracts rather than create a parallel workflow. Candidate import computes/validates livelihood and disaster assessments, applies historical semantic de-duplication, sorts qualifying urgent disasters ahead of scored livelihood candidates, and renders all decision evidence in the existing Markdown director report.

**Tech Stack:** Python 3.12, Pydantic v2, argparse CLI, pytest, Markdown/JSON artifacts.

## Global Constraints

- Candidate selection remains the only routine user approval gate.
- Candidate pool size remains dynamic from 0 to 8; never pad weak topics.
- Major disasters require authoritative evidence and a concrete impact threshold.
- Platform heat evidence never substitutes for fact evidence.
- Historical output topics must be semantically de-duplicated.
- Do not revert unrelated working-tree changes.

---

### Task 1: Add livelihood and disaster assessment contracts

**Files:**
- Modify: `src/avatar_pipeline/hotspot_selection.py`
- Test: `tests/test_hotspot_selection.py`

**Interfaces:**
- Produces `LivelihoodAssessment`, `DisasterEventType`, `DisasterAssessment`, and candidate priority helpers.
- `HotspotPoolCandidate` accepts optional `livelihood_assessment` and `disaster_assessment` fields.

- [ ] Write failing tests for exact livelihood score totals, score bounds, required citizen-impact fields, disaster severity gates, authoritative evidence, and non-qualifying ordinary alerts.
- [ ] Run focused tests and verify failure.
- [ ] Implement minimal Pydantic contracts and validators.
- [ ] Re-run focused tests and verify pass.

### Task 2: Rank urgent disasters and high-value livelihood candidates

**Files:**
- Modify: `src/avatar_pipeline/hotspot_selection.py`
- Test: `tests/test_hotspot_selection.py`

**Interfaces:**
- `HotspotSelectionService.import_pool(day, pool)` returns the filtered and priority-sorted pool.
- Priority order is qualifying active disaster, livelihood score, director grade, then stable input order.

- [ ] Write failing import-order tests.
- [ ] Verify they fail.
- [ ] Implement deterministic priority sorting after historical de-duplication.
- [ ] Verify focused tests pass.

### Task 3: Render structured candidate cards

**Files:**
- Modify: `src/avatar_pipeline/hotspot_selection_report.py`
- Test: `tests/test_hotspot_selection.py`

**Interfaces:**
- `render_candidate_pool_markdown(pool)` exposes affected people, direct interest, effective date, misconception, action, six score components, disaster status, and evidence update time.

- [ ] Write failing report assertions.
- [ ] Implement compact Markdown sections.
- [ ] Run report tests.

### Task 4: Update runbook and configuration guidance

**Files:**
- Modify: `docs/runbooks/manual-news-v5-production.md`
- Modify: `configs/news-video-quality-v5.yaml` only if quality policy belongs there.

- [ ] Document livelihood pool, disaster fast lane, scoring, ethics, semantic de-duplication, and candidate card fields.
- [ ] Run `git diff --check`.

### Task 5: Verify and run today’s discovery

**Files:**
- Create: `tmp/hotspot-selection/2026-08-18/candidate-pool.json`
- Generate: `workspace/hotspot-selections/2026-08-18/candidate-pool.json`
- Generate: `workspace/hotspot-selections/2026-08-18/candidate-pool.md`

- [ ] Run focused hotspot and CLI tests.
- [ ] Run all relevant regression tests.
- [ ] Search current cross-platform signals and authoritative sources for August 18, 2026.
- [ ] Exclude previously produced events unless there is material new development.
- [ ] Import the qualified pool through the CLI.
- [ ] Inspect the generated director report and present candidates for the joint user selection gate.
