# Real Three-Platform Hotspot Collection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a traceable, fail-closed research pipeline that accepts real read-only evidence from Douyin, WeChat Channels, and Xiaohongshu, verifies and clusters it, produces at most three eligible hotspot cards, and prevents watermarked or uncleared platform media from entering production.

**Architecture:** Browser/OpenCLI execution remains outside the credential-free Python core and writes strict collection envelopes with provenance. The Python pipeline validates and normalizes those envelopes, clusters platform records into events, applies fact and risk gates before scoring, then bridges eligible Top 3 cards into the existing `hotspot_review` state. Hotspot evidence and production-media clearance are separate domain objects so a popular platform video cannot accidentally become an edit asset.

**Tech Stack:** Python 3.11+, Pydantic 2, PyYAML, argparse CLI, JSON filesystem repositories, pytest, Ruff; authenticated collection is performed through the Agent-controlled user Chrome session without persisting credentials.

## Global Constraints

- Chrome use is read-only: no likes, comments, saves, follows, messages, publication, or account changes.
- Search the latest 72 hours first; expand to the latest 7 days only when fewer than three eligible hotspots exist.
- A hotspot enters the formal pool only if it appears on at least two target platforms, or has one high-heat target-platform source plus an authoritative verification source.
- Unknown interaction metrics remain `null`; they are never estimated or converted to zero.
- WeChat Official Account articles are supplementary verification evidence and never count as WeChat Channels heat.
- Unverified, conflicting, malicious, privacy-invasive, or otherwise risky topics are skipped automatically.
- Platform hotspot videos are research evidence only and are not production media by default.
- Watermarked, QR-bearing, account-branded, or uncleared media fails closed; the project must not implement watermark removal, cropping, covering, blurring, or AI erasure.
- Production media priority is authorized watermark-free official media, authorized original media, then non-replicative Seedance 2.0 illustrative video.
- Manual mode retains exactly three user gates: hotspot, script, and final video.
- Authentication cookies, tokens, passwords, and browser storage must never be persisted in repository files, artifacts, logs, or command arguments.

---

### Task 1: Strict real-collection and hotspot-card domain models

**Files:**
- Modify: `src/avatar_pipeline/research_models.py`
- Create: `tests/test_real_hotspot_models.py`

**Interfaces:**
- Produces: `CollectorMethod`, `MetricVisibility`, `FactVerificationStatus`, `MediaClearanceStatus`, `PlatformEvidenceRecord`, `AuthorityEvidence`, `HotspotCluster`, `HotspotScoreBreakdown`, and `HotspotReviewCard`.
- Consumes: existing `ResearchPlatform`, `EngagementMetrics`, `ContentPillarSlug`, and timezone-aware timestamp validators.

- [ ] **Step 1: Write failing model tests**

Cover strict rejection of credentials/unknown fields, null metrics, target-platform identity, authoritative evidence, score weights, risk flags, and media-clearance separation.

- [ ] **Step 2: Run the model tests and verify RED**

Run: `PYTHONPATH=src:. .venv/bin/pytest tests/test_real_hotspot_models.py -q`

Expected: import failures because the new models do not exist.

- [ ] **Step 3: Implement the minimal Pydantic models**

Add enums and models without adding browser credentials or raw media bytes. Enforce unique source IDs, valid target-platform coverage, score range `0..100`, and a distinct `production_media_clearance` field.

- [ ] **Step 4: Run model tests and verify GREEN**

Run: `PYTHONPATH=src:. .venv/bin/pytest tests/test_real_hotspot_models.py -q`

- [ ] **Step 5: Commit**

```bash
git add src/avatar_pipeline/research_models.py tests/test_real_hotspot_models.py
git commit -m "feat: model real hotspot evidence and review cards"
```

### Task 2: Credential-free browser collection envelope and capability report

**Files:**
- Create: `src/avatar_pipeline/browser_collection.py`
- Create: `tests/test_browser_collection.py`
- Modify: `src/avatar_pipeline/research_adapters.py`

**Interfaces:**
- Produces: `BrowserCollectionEnvelope`, `BrowserCapability`, `load_browser_collection(path: Path) -> CollectionBatch`, and `write_collection_template(...)`.
- Consumes: Task 1 evidence fields and existing `RawCollectionItem`/`CollectionBatch`.

- [ ] **Step 1: Write failing envelope tests**

Test accepted Douyin/Xiaohongshu/WeChat Channels exports, explicit `login_required` and `ui_changed` failures, rejection of cookie/token/password-shaped keys at any nesting depth, immutable raw artifact hashing, and rejection of Official Account records mislabeled as Channels.

- [ ] **Step 2: Run tests and verify RED**

Run: `PYTHONPATH=src:. .venv/bin/pytest tests/test_browser_collection.py -q`

- [ ] **Step 3: Implement the minimal envelope loader**

The loader reads local JSON produced by the Agent browser session, validates provenance and metric visibility, scans keys recursively for credential material, and converts successful records and failures into the existing collection adapter boundary.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `PYTHONPATH=src:. .venv/bin/pytest tests/test_browser_collection.py tests/test_research_adapters.py -q`

- [ ] **Step 5: Commit**

```bash
git add src/avatar_pipeline/browser_collection.py src/avatar_pipeline/research_adapters.py tests/test_browser_collection.py
git commit -m "feat: ingest authenticated browser research safely"
```

### Task 3: Cross-platform clustering, fact admission, and relative heat ranking

**Files:**
- Create: `src/avatar_pipeline/hotspot_ranking.py`
- Create: `tests/test_hotspot_ranking.py`

**Interfaces:**
- Produces: `cluster_sources(...) -> list[HotspotCluster]`, `rank_hotspots(...) -> list[HotspotReviewCard]`, and `hotspot_is_eligible(...) -> AdmissionResult`.
- Consumes: Task 1 models plus `CommentInsightCard` and configured excluded-topic terms.

- [ ] **Step 1: Write failing ranking tests**

Cover same-platform dedupe, conservative event clustering, per-platform percentile heat, 72-hour selection, 7-day fallback, dual-platform admission, single-platform-high-heat plus authority admission, Official Account non-counting, fact conflicts, risk exclusions, and fewer-than-three honest results.

- [ ] **Step 2: Run tests and verify RED**

Run: `PYTHONPATH=src:. .venv/bin/pytest tests/test_hotspot_ranking.py -q`

- [ ] **Step 3: Implement deterministic minimal ranking**

Use stable identity/URL dedupe and explicit event keys supplied by the collection envelope. Do not invent semantic equivalence when an event key is absent; keep uncertain records separate. Normalize engagement only inside the same platform and collection window, calculate the documented weighted score, and treat fact verification as a hard gate rather than a score boost.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `PYTHONPATH=src:. .venv/bin/pytest tests/test_hotspot_ranking.py tests/test_policy.py -q`

- [ ] **Step 5: Commit**

```bash
git add src/avatar_pipeline/hotspot_ranking.py tests/test_hotspot_ranking.py
git commit -m "feat: rank verified cross-platform hotspots"
```

### Task 4: Fail-closed media clearance and watermark policy

**Files:**
- Create: `src/avatar_pipeline/media_clearance.py`
- Create: `tests/test_media_clearance.py`
- Modify: `src/avatar_pipeline/media.py`

**Interfaces:**
- Produces: `MediaEvidence`, `MediaInspection`, `decide_media_clearance(...)`, and `require_production_media_clearance(...)`.
- Consumes: Task 1 `MediaClearanceStatus` and existing media plan validation.

- [ ] **Step 1: Write failing policy tests**

Test that platform research links are rejected as production media by default; visible/suspected watermarks, logos, usernames, QR codes, missing rights records, and unknown clearance all fail; authorized clean originals pass; Seedance illustrative assets pass only with AI disclosure and non-replication declaration.

- [ ] **Step 2: Run tests and verify RED**

Run: `PYTHONPATH=src:. .venv/bin/pytest tests/test_media_clearance.py -q`

- [ ] **Step 3: Implement the clearance decision service**

Implement metadata-level fail-closed checks and integrate the check into media-plan validation. Do not add image manipulation or watermark-removal code.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `PYTHONPATH=src:. .venv/bin/pytest tests/test_media_clearance.py tests/test_media.py -q`

- [ ] **Step 5: Commit**

```bash
git add src/avatar_pipeline/media_clearance.py src/avatar_pipeline/media.py tests/test_media_clearance.py
git commit -m "feat: reject watermarked and uncleared production media"
```

### Task 5: Top 3 report, research-to-production bridge, and CLI

**Files:**
- Modify: `src/avatar_pipeline/research_report.py`
- Modify: `src/avatar_pipeline/research_service.py`
- Modify: `src/avatar_pipeline/cli.py`
- Modify: `src/avatar_pipeline/service.py`
- Create: `tests/test_real_hotspot_flow.py`
- Modify: `tests/test_cli.py`

**Interfaces:**
- Produces CLI commands:
  - `research-import-browser --date YYYY-MM-DD --file PATH`
  - `research-rank-hotspots --date YYYY-MM-DD --authority-file PATH`
  - `research-hotspot-report --date YYYY-MM-DD`
  - `research-submit-top3 --date YYYY-MM-DD`
- Produces a Markdown and JSON review payload containing real channels, visible metrics, missing fields, verification, audience insight, risk notes, speaking angle, and production-media plan.
- Consumes: Tasks 1–4 and existing `DailyWorkflowService.record_research()`.

- [ ] **Step 1: Write failing end-to-end tests**

Exercise browser import through Top 3 generation and bridge into a manual daily task. Verify the task stops at `HOTSPOT_REVIEW`, only eligible cards become `TopicCandidate`s, source links and verification summaries survive, and the existing `approve-hotspot` command remains the only first gate.

- [ ] **Step 2: Run tests and verify RED**

Run: `PYTHONPATH=src:. .venv/bin/pytest tests/test_real_hotspot_flow.py tests/test_cli.py -q`

- [ ] **Step 3: Implement service/report/CLI integration**

Persist ranked cards beside the research run, render truthful Top 3 output, convert selected evidence to existing production candidates, and keep raw browser credentials outside all persisted payloads.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `PYTHONPATH=src:. .venv/bin/pytest tests/test_real_hotspot_flow.py tests/test_cli.py tests/test_manual_confirmation_flow.py -q`

- [ ] **Step 5: Commit**

```bash
git add src/avatar_pipeline/research_report.py src/avatar_pipeline/research_service.py src/avatar_pipeline/cli.py src/avatar_pipeline/service.py tests/test_real_hotspot_flow.py tests/test_cli.py
git commit -m "feat: connect real hotspot Top 3 to manual review"
```

### Task 6: Browser operator protocol and capability diagnostics

**Files:**
- Create: `docs/operations/real-three-platform-collection-runbook.md`
- Modify: `docs/operations/phase-2a-hotspot-research-runbook.md`
- Modify: `README.md`
- Modify: `skills/third_party.lock.yaml`
- Modify: `skills/audits/opinions-crawler.md`
- Create: `tests/test_real_collection_docs.py`

**Interfaces:**
- Documents the Agent-owned Chrome collection procedure, exact read-only actions, capability statuses, evidence export format, failure codes, 72-hour/7-day fallback, and Video Channels assisted-import path.
- Updates third-party state only after an actual capability probe; no optimistic `real_calls_enabled: true` value.

- [ ] **Step 1: Write failing documentation-contract tests**

Assert the runbook contains all three platforms, credential prohibition, no-interaction rule, no-watermark rule, no-watermark-removal rule, capability failure codes, time fallback, and exact CLI commands.

- [ ] **Step 2: Run tests and verify RED**

Run: `PYTHONPATH=src:. .venv/bin/pytest tests/test_real_collection_docs.py -q`

- [ ] **Step 3: Write the operator documentation and truthful capability state**

Document that browser automation is Agent-executed and project ingestion is credential-free. Preserve `real_calls_enabled: false` until a live logged-in probe succeeds for each platform; record per-platform results rather than one global boolean.

- [ ] **Step 4: Run documentation tests and verify GREEN**

Run: `PYTHONPATH=src:. .venv/bin/pytest tests/test_real_collection_docs.py tests/test_project_research_skills.py tests/test_research_skill_manifest.py -q`

- [ ] **Step 5: Commit**

```bash
git add README.md docs/operations skills/third_party.lock.yaml skills/audits/opinions-crawler.md tests/test_real_collection_docs.py
git commit -m "docs: define authenticated read-only collection operations"
```

### Task 7: Live Chrome capability probe and full verification

**Files:**
- Runtime artifacts only under ignored `runs/` or `workspace/`; do not commit login state or raw credentials.
- Modify tracked capability documentation only if observed results warrant it.

**Interfaces:**
- Consumes the Agent-controlled Chrome session and Task 2 envelope format.
- Produces a sanitized capability report for Douyin, WeChat Channels, and Xiaohongshu, plus a sample real collection envelope if access succeeds.

- [ ] **Step 1: Connect to the existing Chrome session**

List open tabs and inspect target platform login state without exposing credentials.

- [ ] **Step 2: Probe one read-only search per platform**

Use a low-frequency query, read only visible public fields, and record `ready`, `login_required`, `ui_changed`, `rate_limited`, or `manual_assist_required`. Do not bypass verification or access controls.

- [ ] **Step 3: Import and validate any successful sample**

Run the new browser-import and hotspot-ranking commands against sanitized output. If a platform cannot be accessed, preserve the failure and continue; do not fabricate replacement records.

- [ ] **Step 4: Run complete verification**

```bash
PYTHONPATH=src:. .venv/bin/pytest -q
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
git diff --check
```

Expected: zero failures, zero lint violations, all files formatted, and no whitespace errors.

- [ ] **Step 5: Review tracked and ignored artifacts**

Run `git status --short` and confirm `runs/`, `workspace/`, browser exports, screenshots, credentials, and generated media are not staged.

- [ ] **Step 6: Commit any truthful capability-state updates**

```bash
git add README.md docs/operations skills/third_party.lock.yaml skills/audits/opinions-crawler.md
git commit -m "chore: record live platform collection capabilities"
```

Do not create this commit when no tracked capability state changed.
