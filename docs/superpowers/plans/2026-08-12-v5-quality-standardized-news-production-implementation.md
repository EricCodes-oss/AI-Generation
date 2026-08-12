# V5 Standardized News Production Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable, testable manual-production quality gate that keeps every 45–90 second vertical avatar-news video aligned with the approved V5 host, voice, script, footage, timeline, render, QC, and delivery standards.

**Architecture:** Add a V5-specific configuration and a separate manual-run domain instead of changing the legacy `DailyTask` schema. Focused modules load strict configuration, model production records, validate each stage, create version-safe workspaces, and expose non-interactive CLI commands. Existing hotspot selection remains upstream; FFmpeg and director judgment remain external actions whose evidence is consumed by hard quality gates.

**Tech Stack:** Python 3.11+, Pydantic 2, PyYAML, pathlib, hashlib, argparse, pytest, Ruff, JSON, FFmpeg/ffprobe evidence files.

## Global Constraints

- Scope is limited to 45–90 second, 9:16, 1080×1920, 25fps, clean-master avatar-led news videos.
- Lock host `host-c2-pro-candidate-2-final` to SHA-256 `939324593eb718cd2a39be4c171f74178a6a48442f7e0d61afe8a875011e8a47`.
- Lock voice ID to `cobra_design_20250717_162347_664524`.
- Do not burn subtitles, titles, source labels, logos, or other text into the clean master.
- Do not add background music or source-footage audio.
- Forbid reverse, loop, and ping-pong footage processing.
- Require each B-roll shot to map to an approved script semantic segment and use one forward continuous source interval.
- Treat watermark-free footage as the user-approved project usage rule; never label watermark-free status as copyright authorization.
- Require automatic QC and an explicit director approval before `ready_to_deliver`.
- Never overwrite a prior run directory or existing final video.
- Preserve the current V5 final video and its SHA-256 unchanged.

---

## File Structure

- `configs/news-video-quality-v5.yaml`: canonical V5 identity, format, rhythm, clean-master, and QC thresholds.
- `src/avatar_pipeline/news_quality_config.py`: strict Pydantic configuration models and YAML loader.
- `src/avatar_pipeline/news_production_models.py`: production manifest, evidence, script review, footage, shot, timeline, director review, and QC report schemas.
- `src/avatar_pipeline/news_production.py`: workspace initialization, duration guidance, stage validation, version protection, and manifest transitions.
- `src/avatar_pipeline/news_qc.py`: ffprobe/log/audio-integrity parsing and final evidence-rich QC report construction.
- `src/avatar_pipeline/cli.py`: non-interactive `news-v5-*` commands.
- `tests/test_news_quality_config.py`: quality configuration validation.
- `tests/test_news_production_models.py`: strict record schemas and cross-record invariants.
- `tests/test_news_production.py`: initialization, preflight, timeline, render, and delivery gates.
- `tests/test_news_qc.py`: technical QC evidence tests.
- `tests/test_cli.py`: public CLI coverage.
- `skills/contracts/*.yaml`: align script, planner, clipper, compositor, TTS, avatar, and QC contracts with V5.
- `docs/runbooks/manual-news-v5-production.md`: complete operator and director SOP.
- `README.md`: document the V5 manual workflow and commands.

---

### Task 1: Strict V5 quality configuration

**Files:**
- Create: `configs/news-video-quality-v5.yaml`
- Create: `src/avatar_pipeline/news_quality_config.py`
- Create: `tests/test_news_quality_config.py`

**Interfaces:**
- Produces: `NewsVideoQualityConfig` and `load_news_quality_config(path: Path | str) -> NewsVideoQualityConfig`.
- Consumed by: all later production and QC tasks.

- [ ] **Step 1: Write failing configuration tests**

Test that the canonical file loads with exact V5 values, rejects durations outside 45–90, rejects non-1080×1920/25fps output, rejects enabled clean-master overlays/audio, and rejects a blank host hash or voice ID.

```python
from pydantic import ValidationError

from avatar_pipeline.news_quality_config import load_news_quality_config


def test_canonical_v5_quality_config_is_locked():
    config = load_news_quality_config("configs/news-video-quality-v5.yaml")
    assert config.profile.id == "v5_vertical_anchor_news"
    assert config.host.sha256 == "939324593eb718cd2a39be4c171f74178a6a48442f7e0d61afe8a875011e8a47"
    assert config.voice.voice_id == "cobra_design_20250717_162347_664524"
    assert (config.output.width, config.output.height, config.output.fps) == (1080, 1920, 25)
    assert config.profile.min_duration_seconds == 45
    assert config.profile.max_duration_seconds == 90
```

- [ ] **Step 2: Run tests and verify the module is missing**

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_news_quality_config.py -q`  
Expected: FAIL during import because `news_quality_config` does not exist.

- [ ] **Step 3: Implement the strict models and canonical YAML**

Define focused `StrictModel` subclasses for `profile`, `output`, `clean_master`, `host`, `voice`, `broll`, `ending`, and `quality`. Use literal values for locked output and identity-lock behavior, validate ordered ranges, and reject any enabled clean-master decoration or secondary audio.

```python
def load_news_quality_config(path: Path | str) -> NewsVideoQualityConfig:
    with Path(path).open("r", encoding="utf-8") as handle:
        return NewsVideoQualityConfig.model_validate(yaml.safe_load(handle))
```

- [ ] **Step 4: Run focused tests and lint**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_news_quality_config.py -q
.venv/bin/ruff check src/avatar_pipeline/news_quality_config.py tests/test_news_quality_config.py
```

Expected: all tests pass and Ruff reports no errors.

- [ ] **Step 5: Commit the configuration unit**

```bash
git add configs/news-video-quality-v5.yaml src/avatar_pipeline/news_quality_config.py tests/test_news_quality_config.py
git commit -m "feat: add locked v5 news quality profile"
```

### Task 2: Production records and invariant-rich schemas

**Files:**
- Create: `src/avatar_pipeline/news_production_models.py`
- Create: `tests/test_news_production_models.py`

**Interfaces:**
- Produces: `NewsRunStatus`, `NewsRunManifest`, `FactEvidence`, `ScriptReview`, `FootageLedger`, `ShotSelectionRecord`, `NewsTimeline`, `DirectorReview`, `QualityCheck`, and `FinalQualityReport`.
- Consumed by: `news_production.py`, `news_qc.py`, and CLI commands.

- [ ] **Step 1: Write failing model tests**

Cover these invariants with concrete model fixtures:

- a fact pack needs one authoritative source and one verified fact;
- an approved script review needs traceable facts, authoritative tone, clear sentences, adequate information, and a complete ending;
- a footage item needs a URL, local path, hash, and all watermark/text checks set to true before `user_usage_rule_passed=true`;
- a shot needs `source_out > source_in`, forward playback, continuous action, semantic role, script segment ID, and director approval;
- a timeline starts at zero, has no gaps or overlaps, ends at audio duration, references approved shots, and ends with an anchor segment;
- a final report cannot be overall-passed while containing failed checks or an unapproved director review.

```python
with pytest.raises(ValidationError, match="watermark"):
    FootageAsset(..., watermark_free=False, user_usage_rule_passed=True)
```

- [ ] **Step 2: Run tests and verify failure**

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_news_production_models.py -q`  
Expected: FAIL during import.

- [ ] **Step 3: Implement strict production models**

Use `ConfigDict(extra="forbid", validate_assignment=True)` for every stored record. Store run IDs in every top-level file, use ISO dates/timestamps, and represent statuses with this enum:

```python
class NewsRunStatus(StrEnum):
    INITIALIZED = "initialized"
    GENERATION_READY = "generation_ready"
    TIMELINE_READY = "timeline_ready"
    RENDER_READY = "render_ready"
    RENDERED_PENDING_QC = "rendered_pending_qc"
    AUTOMATIC_QC_PASSED = "automatic_qc_passed"
    DIRECTOR_REVIEW = "director_review"
    READY_TO_DELIVER = "ready_to_deliver"
    CHANGES_REQUIRED = "changes_required"
```

Add model validators for interval ordering, approval implications, unique IDs, and internal QC consistency.

- [ ] **Step 4: Run focused tests and lint**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_news_production_models.py -q
.venv/bin/ruff check src/avatar_pipeline/news_production_models.py tests/test_news_production_models.py
```

Expected: all pass.

- [ ] **Step 5: Commit the record schemas**

```bash
git add src/avatar_pipeline/news_production_models.py tests/test_news_production_models.py
git commit -m "feat: model v5 news production records"
```

### Task 3: Version-safe run initialization and B-roll guidance

**Files:**
- Create: `src/avatar_pipeline/news_production.py`
- Create: `tests/test_news_production.py`

**Interfaces:**
- Consumes: `NewsVideoQualityConfig`, `NewsRunManifest`.
- Produces:
  - `initialize_news_run(output_root: Path, day: date, slug: str, topic: str, version: int, quality_config_path: Path, parent_run_id: str | None = None) -> Path`
  - `recommend_broll(duration_seconds: float, config: NewsVideoQualityConfig) -> BrollGuidance`
  - `load_run_record(run_dir: Path, relative_path: str, model_type: type[T]) -> T`
  - `save_manifest(run_dir: Path, manifest: NewsRunManifest) -> None`

- [ ] **Step 1: Write failing initialization and guidance tests**

Verify exact directories, manifest identity values, output naming, parent version recording, non-overwrite behavior, and duration-aware guidance:

```python
assert recommend_broll(52.128, config).recommended_count == 3
assert recommend_broll(40, config)  # raises outside configured range
assert initialize_news_run(...) == tmp_path / "manual-news-2026-08-12-storm-v01"
with pytest.raises(FileExistsError):
    initialize_news_run(...)
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_news_production.py -q`  
Expected: FAIL because the functions do not exist.

- [ ] **Step 3: Implement initialization and guidance**

Create only these directories during initialization: `video`, `audio`, `copy`, `production`, and `qc`. Write `production/run-manifest.json` atomically and copy the selected quality configuration to `production/quality-profile.yaml`. Refuse an existing target directory.

Use this default guidance table:

```python
if duration_seconds <= 55:
    return BrollGuidance(2, 3, 4.5, 6.5, 0.25, 0.35)
if duration_seconds <= 70:
    return BrollGuidance(3, 3, 5.0, 7.0, 0.25, 0.35)
return BrollGuidance(3, 4, 5.0, 8.0, 0.25, 0.38)
```

The guidance remains advisory; later validation hard-blocks structural defects and emits advisory findings for rhythm deviations.

- [ ] **Step 4: Run tests and lint**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_news_production.py -q
.venv/bin/ruff check src/avatar_pipeline/news_production.py tests/test_news_production.py
```

Expected: pass.

- [ ] **Step 5: Commit the workspace unit**

```bash
git add src/avatar_pipeline/news_production.py tests/test_news_production.py
git commit -m "feat: initialize version-safe v5 news runs"
```

### Task 4: Generation, footage, timeline, and render hard gates

**Files:**
- Modify: `src/avatar_pipeline/news_production.py`
- Modify: `tests/test_news_production.py`

**Interfaces:**
- Produces:
  - `validate_generation_preflight(run_dir: Path, project_root: Path) -> StageValidationResult`
  - `validate_timeline_preflight(run_dir: Path) -> StageValidationResult`
  - `validate_render_preflight(run_dir: Path) -> StageValidationResult`
  - `mark_rendered(run_dir: Path) -> NewsRunManifest`
- Each function raises `NewsProductionGateError` on hard-block failures and updates status only after all checks pass.

- [ ] **Step 1: Add failing generation preflight tests**

Create valid fixture files, then independently corrupt host hash, voice ID, fact evidence, script approval, script/audio duration, and required copy paths. Assert each corruption produces a named hard-block issue and leaves the manifest status unchanged.

- [ ] **Step 2: Run generation tests and verify failure**

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_news_production.py -q -k generation`  
Expected: FAIL because preflight is missing.

- [ ] **Step 3: Implement generation preflight**

Recompute the actual host image SHA-256 from `project_root / config.host.reference_image`; compare it with both the quality profile and manifest. Load `fact-evidence.json` and `script-review.json`, verify `copy/voiceover.txt` and `copy/title.txt`, compare voice ID, and enforce 45–90 seconds. Update status to `generation_ready` only after a clean result.

- [ ] **Step 4: Add failing footage and timeline tests**

Test missing source URL, failed watermark/text checks, missing local assets, mismatched hashes, unapproved shots, unknown shot IDs, missing semantic mappings, gaps, overlaps, B-roll first/last segments, incomplete final duration, and short anchor tail.

- [ ] **Step 5: Implement footage and timeline validation**

Validate `footage-ledger.json`, `shot-selection.json`, and `timeline.json` as a joined graph. Hard-block source-integrity and structural errors. Return advisory findings when B-roll count, clip duration, or total ratio falls outside guidance. Set status to `timeline_ready` only after hard checks pass.

- [ ] **Step 6: Add failing render-preflight and non-overwrite tests**

Test missing `render.sh`, references to files outside the run, `-map` of source audio, existing final output, and case-insensitive forbidden tokens such as `reverse`, `loop`, and `pingpong`.

- [ ] **Step 7: Implement render preflight and mark-rendered**

Require a safe render script, all referenced assets, a declared final output under `video/`, no existing output before rendering, and no forbidden processing. `mark_rendered` requires a non-empty final video and changes status from `render_ready` to `rendered_pending_qc`.

- [ ] **Step 8: Run the full production test file and lint**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_news_production.py -q
.venv/bin/ruff check src/avatar_pipeline/news_production.py tests/test_news_production.py
```

Expected: pass.

- [ ] **Step 9: Commit the stage gates**

```bash
git add src/avatar_pipeline/news_production.py tests/test_news_production.py
git commit -m "feat: enforce v5 production stage gates"
```

### Task 5: Evidence-rich automatic QC and director delivery gate

**Files:**
- Create: `src/avatar_pipeline/news_qc.py`
- Create: `tests/test_news_qc.py`
- Modify: `src/avatar_pipeline/news_production.py`
- Modify: `tests/test_news_production.py`

**Interfaces:**
- Produces:
  - `build_automatic_qc_report(run_dir: Path) -> FinalQualityReport`
  - `apply_director_review(run_dir: Path) -> FinalQualityReport`
- Consumes standard files under `qc/` and production records from earlier tasks.

- [ ] **Step 1: Write failing technical QC tests**

Use small JSON/text fixtures to test:

- one H.264 1080×1920 25fps video and one AAC 48kHz mono audio stream;
- duration difference no greater than one frame plus encoded rounding tolerance;
- no `black_start` events;
- no silence over one second except a short natural tail;
- empty decode-error log;
- audio correlation at or above `0.99` with zero/near-zero lag;
- final SHA-256 recording;
- complete required QC evidence.

- [ ] **Step 2: Run QC tests and verify failure**

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_news_qc.py -q`  
Expected: FAIL during import.

- [ ] **Step 3: Implement automatic QC parsing and report construction**

Read `qc/ffprobe.json`, `qc/blackdetect.log`, `qc/silencedetect.log`, `qc/decode-errors.log`, and `qc/audio-comparison.json`. Reuse stage validators for identity, timeline, and render safety. Write grouped `QualityCheck` records with expected value, actual value, result, evidence path, and timestamp. Save `qc/final-qc-report.json` and `qc/sha256.txt`. Set `automatic_qc_passed` only when every hard check passes; otherwise set `changes_required`.

- [ ] **Step 4: Write failing director-review and deliverable tests**

Test that all required human checks and contact sheets are present, `approved=true`, no failed director checks exist, all standard deliverables exist, and automatic QC has passed. Verify a missing title, contact sheet, or approval blocks delivery.

- [ ] **Step 5: Implement the director delivery gate**

Load `qc/director-review.json`, validate the required review checklist and evidence files, merge director checks into `final-qc-report.json`, and update the manifest to `ready_to_deliver`. Failed review sets `changes_required`. Do not infer approval from the presence of a video.

- [ ] **Step 6: Run focused tests and lint**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_news_qc.py tests/test_news_production.py -q
.venv/bin/ruff check src/avatar_pipeline/news_qc.py src/avatar_pipeline/news_production.py tests/test_news_qc.py tests/test_news_production.py
```

Expected: pass.

- [ ] **Step 7: Commit the QC gates**

```bash
git add src/avatar_pipeline/news_qc.py src/avatar_pipeline/news_production.py tests/test_news_qc.py tests/test_news_production.py
git commit -m "feat: add automatic and director v5 quality gates"
```

### Task 6: Non-interactive CLI workflow

**Files:**
- Modify: `src/avatar_pipeline/cli.py`
- Modify: `tests/test_cli.py`

**Interfaces:**
- Adds commands:
  - `news-v5-init`
  - `news-v5-guidance`
  - `news-v5-preflight --stage generation|timeline|render`
  - `news-v5-mark-rendered`
  - `news-v5-build-qc`
  - `news-v5-apply-director-review`
  - `news-v5-status`

- [ ] **Step 1: Write failing parser and dispatch tests**

Test command arguments, JSON stdout, non-zero error exits, run-directory creation, status reporting, guidance for 52.128 seconds, and every stage command against temporary fixtures.

```python
args = build_parser().parse_args(["news-v5-guidance", "--duration", "52.128"])
assert dispatch(args)["recommended_count"] == 3
```

- [ ] **Step 2: Run CLI tests and verify failure**

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_cli.py -q -k news_v5`  
Expected: FAIL because commands are unknown.

- [ ] **Step 3: Implement parser branches and dispatch**

Keep commands non-interactive. Accept explicit paths and values, serialize Pydantic models with `mode="json"`, and return structured stage results containing status, hard failures, advisories, and evidence paths.

- [ ] **Step 4: Run CLI and related tests**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_cli.py tests/test_news_production.py tests/test_news_qc.py -q
.venv/bin/ruff check src/avatar_pipeline/cli.py tests/test_cli.py
```

Expected: pass.

- [ ] **Step 5: Commit the CLI**

```bash
git add src/avatar_pipeline/cli.py tests/test_cli.py
git commit -m "feat: expose v5 manual news quality commands"
```

### Task 7: Align external skill contracts with the clean-master V5 profile

**Files:**
- Modify: `skills/contracts/avatar.yaml`
- Modify: `skills/contracts/news-compositor.yaml`
- Modify: `skills/contracts/news-footage-clipper.yaml`
- Modify: `skills/contracts/news-media-planner.yaml`
- Modify: `skills/contracts/news-quality-control.yaml`
- Modify: `skills/contracts/news-script-writer.yaml`
- Modify: `skills/contracts/tts.yaml`
- Modify: `tests/test_skill_contracts.py`

**Interfaces:**
- Consumed by: existing `load_contracts()` health checks and external-provider adapters.
- Produces: contracts that declare V5 duration and clean-master behavior without enabling real generation.

- [ ] **Step 1: Add failing contract assertions**

Assert 90-second duration support for TTS/avatar/planner/compositor/QC, semantic mapping and forward-continuous footage requirements, clean-master no-text/no-source-audio constraints, fixed host/voice identity fields, and QC identity/timeline/ending outputs.

- [ ] **Step 2: Run contract tests and verify failure**

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_skill_contracts.py -q`  
Expected: FAIL against the old 50/75-second and overlay-oriented contracts.

- [ ] **Step 3: Update YAML contracts**

Keep `contract_version: "1.0"` and `real_generation_enabled: false` for parser compatibility. Add V5 requirements through required/optional inputs, outputs, duration values, and explicit safety constraints. Store source and AI provenance in sidecar records rather than visual overlays for the clean master.

- [ ] **Step 4: Run contract tests and health checks**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_skill_contracts.py tests/test_seated_avatar_contracts.py -q
PYTHONPATH=src .venv/bin/python -m avatar_pipeline.cli health
```

Expected: tests pass and health reports all contracts loaded.

- [ ] **Step 5: Commit contract alignment**

```bash
git add skills/contracts tests/test_skill_contracts.py
git commit -m "chore: align news skill contracts with v5 quality"
```

### Task 8: Manual runbook and project documentation

**Files:**
- Create: `docs/runbooks/manual-news-v5-production.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: all commands and records from Tasks 1–7.
- Produces: one operator-ready SOP and a concise project entry point.

- [ ] **Step 1: Write the full runbook**

Document exact command order, directory layout, JSON record requirements, hotspot/fact/script gates, voice and host verification, footage download and watermark inspection, contact-sheet shot selection, duration-aware timeline planning, safe FFmpeg rendering, automatic evidence generation, two-pass director review, failure return paths, and the fixed delivery summary.

Include complete command examples using an example run directory, but state that dates, topics, and source facts must come from the current run.

- [ ] **Step 2: Update README product boundaries and CLI examples**

Separate legacy V1 behavior from the V5 manual clean-master profile. Add a short “V5手动新闻制作” section that links the runbook and lists the new commands.

- [ ] **Step 3: Check documentation consistency**

Run:

```bash
rg -n "45.?90|未来科技解说|cobra_design_20250717_162347_664524|939324593eb718cd2a39be4c171f74178a6a48442f7e0d61afe8a875011e8a47|无字净版" \
  docs/runbooks/manual-news-v5-production.md README.md configs/news-video-quality-v5.yaml
git diff --check
```

Expected: every locked value is documented consistently and no whitespace errors exist.

- [ ] **Step 4: Commit documentation**

```bash
git add docs/runbooks/manual-news-v5-production.md README.md
git commit -m "docs: standardize v5 manual news production"
```

### Task 9: Full verification and V5 preservation audit

**Files:**
- Modify: `docs/superpowers/plans/2026-08-12-v5-quality-standardized-news-production-implementation.md`

**Interfaces:**
- Consumes: complete implementation.
- Produces: checked task list and final evidence summary.

- [ ] **Step 1: Run the complete automated suite**

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Run static checks**

```bash
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
git diff --check
```

Expected: all checks pass.

- [ ] **Step 3: Exercise CLI health and V5 guidance**

```bash
PYTHONPATH=src .venv/bin/python -m avatar_pipeline.cli health
PYTHONPATH=src .venv/bin/python -m avatar_pipeline.cli news-v5-guidance --duration 52.128
```

Expected: health is OK and guidance recommends three B-roll inserts within the V5 rhythm range.

- [ ] **Step 4: Verify the approved V5 media was not changed**

```bash
test "$(shasum -a 256 'output/manual-run-2026-08-12-v5/video/白海豚-北方强降雨-新闻口播-无字净版-v5.mp4' | awk '{print $1}')" = \
  "96556832d3e657dc1d78831d9eb0b25c517278488ec4d2a02acd1a665716338f"
```

Expected: exit 0.

- [ ] **Step 5: Mark completed plan checkboxes and commit verification metadata**

```bash
git add docs/superpowers/plans/2026-08-12-v5-quality-standardized-news-production-implementation.md
git commit -m "chore: verify v5 standardized news workflow"
```

- [ ] **Step 6: Review final change impact and status**

Run:

```bash
git status --short
git log --oneline -12
```

Expected: only historical untracked media remains; all implementation files are committed in small, auditable commits.
