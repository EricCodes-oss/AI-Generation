# Manual cross-platform hotspot sampling

This runbook is research-only. It does not generate scripts, speech, avatar video, insert media, or composites.

## Safety checks

1. Use the current sampling date for a new run (for example `2026-08-11`). Never reuse an earlier business date to imitate fresh evidence.
2. Confirm the matching `workspace/days/<date>/task.json`, if it exists, is `fact_screened` or `topic_script_review` and has no `topic_script` approval.
3. Do not run `mark-tts`, `mark-anchor`, `mark-media`, or `mark-compositing`.
4. Keep the C2-Pro Candidate 2 host image and `host_profile` unchanged; verify SHA256 `939324593eb718cd2a39be4c171f74178a6a48442f7e0d61afe8a875011e8a47` before refresh.

Run the exact check and stop on mismatch:

```bash
test "$(shasum -a 256 'output/host-v12-c2-pro/GPT-Image-2-Pro-C2-Pro-主持人最终选定.png' | awk '{print $1}')" = \
  "939324593eb718cd2a39be4c171f74178a6a48442f7e0d61afe8a875011e8a47"
```

## Import T0, T+10, and T+20

For canonical snapshots:

```bash
PYTHONPATH=src:. .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-import-snapshot --date 2026-08-10 --format canonical \
  --file tmp/hotspot-sampling/t0.json
sleep 600
PYTHONPATH=src:. .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-import-snapshot --date 2026-08-10 --format canonical \
  --file tmp/hotspot-sampling/t1.json
sleep 600
PYTHONPATH=src:. .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-import-snapshot --date 2026-08-10 --format canonical \
  --file tmp/hotspot-sampling/t2.json
```

For a TopHub structured export, include immutable capture metadata and an optional failure map whose JSON shape is `{"bilibili": ["api returned -352", "tmp/raw/bilibili.json"]}`:

```bash
PYTHONPATH=src:. .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-import-snapshot --date 2026-08-10 --format tophub \
  --file tmp/hotspot-sampling/tophub_structured.json --snapshot-id t0 \
  --captured-at 2026-08-10T19:47:17+08:00 --timezone Asia/Shanghai \
  --failures tmp/hotspot-failures.json
```

The CLI only imports saved local evidence. It does not perform network collection. Snapshot files are immutable: importing an existing snapshot ID fails rather than overwriting evidence.

## Discover event IDs and import human review

Build once to expose rejected cluster IDs. Missing review data is an explicit rejection, not an error or zero score:

```bash
PYTHONPATH=src:. .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-build-report --date 2026-08-10
PYTHONPATH=src:. .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-status --date 2026-08-10
```

Prepare three auditable review files:

- `verification.json`: `CandidateVerification` objects for fact safety;
- `editorial-signals.json`: `EditorialSignals` objects for click, conflict, relevance, visuals, and explanation;
- `short-video-evidence.json`: `EventShortVideoEvidence` objects with separate Douyin and Xiaohongshu evidence. Preserve source counts, observed views/likes/comments/shares/saves, comment samples, emotion/conflict signals, hook patterns, visual materials, suitability score, and raw evidence paths. A restricted or failed platform must retain `collection_status` and `failure_reason`; never convert missing data to zero heat.

Rebuild after importing them:

```bash
PYTHONPATH=src:. .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-import-review --date 2026-08-10 \
  --verification tmp/hotspot-sampling/verification.json \
  --editorial-signals tmp/hotspot-sampling/editorial-signals.json \
  --short-video-evidence tmp/hotspot-sampling/short-video-evidence.json
PYTHONPATH=src:. .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-build-report --date 2026-08-10
```

Read both:

- `workspace/hotspots/2026-08-10/reports/candidate-report.json`
- `workspace/hotspots/2026-08-10/reports/candidate-report.md`

The report is limited to three candidates and uses the versioned `viral-v1.1` rules. Rank-board virality and short-video fit are separate layers. A candidate may remain visible with `director_action=watch`, but it can become the director recommendation and enter `hotspot-refresh` only when both Douyin and Xiaohongshu evidence pass their source, comment, engagement/observed-interaction, and suitability thresholds. If evidence is missing or restricted, the platform score stays unknown rather than zero. If `outcome` is `no_qualified_hotspot`, stop. Do not substitute a lower-quality topic or describe an ordinary topic as the hottest topic on the internet.

## Refresh only after reviewing the qualified report

Only run this command after a human has reviewed a report whose outcome is `qualified_candidates` **and** whose `director_recommendation_event_id` is non-null. A watch-only report cannot refresh production:

```bash
PYTHONPATH=src:. .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-refresh --date 2026-08-10 \
  --archive-reason "旧‘大学新生电脑涨价’方案传播性不足，改用跨平台连续采样候选" \
  --confirmed-host-profile output/manual-run-2026-08-10/planning/host-profile.json
```

This archives the old candidates, script, and media plan; preserves the host; clears the active selection/script/media plan; and remains at `topic_script_review`:

```bash
PYTHONPATH=src:. .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  status --date 2026-08-10
```

The expected state is `topic_script_review`, with the C2-Pro Candidate 2 `host_profile`, no selected topic, no script, no media plan, and no new artifacts. User confirmation is still required before any paid generation.
