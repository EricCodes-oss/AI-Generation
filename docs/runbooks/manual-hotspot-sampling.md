# Manual cross-platform hotspot sampling

This runbook is research-only. It does not generate scripts, speech, avatar video, insert media, or composites.

## Safety checks

1. Use the locked business date `2026-08-10` when rebuilding that day's decision.
2. Confirm `workspace/days/2026-08-10/task.json` is `fact_screened` or `topic_script_review` and has no `topic_script` approval.
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

Prepare `verification.json` as a JSON list of `CandidateVerification` objects and `editorial-signals.json` as a JSON list of `EditorialSignals` objects. Rebuild after importing them:

```bash
PYTHONPATH=src:. .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-import-review --date 2026-08-10 \
  --verification tmp/hotspot-sampling/verification.json \
  --editorial-signals tmp/hotspot-sampling/editorial-signals.json
PYTHONPATH=src:. .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-build-report --date 2026-08-10
```

Read both:

- `workspace/hotspots/2026-08-10/reports/candidate-report.json`
- `workspace/hotspots/2026-08-10/reports/candidate-report.md`

The report is limited to three candidates and uses the versioned `viral-v1.0` scoring rules. If `outcome` is `no_qualified_hotspot`, stop. Do not substitute a lower-quality topic or describe an ordinary topic as the hottest topic on the internet.

## Refresh only after reviewing the qualified report

Only run this command after a human has reviewed a report whose outcome is `qualified_candidates`:

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
