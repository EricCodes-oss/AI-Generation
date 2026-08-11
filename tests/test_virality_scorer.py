from datetime import datetime

import pytest

from avatar_pipeline.candidate_verifier import verify_candidate
from avatar_pipeline.config import load_config
from avatar_pipeline.virality_gate import evaluate_virality_gate
from avatar_pipeline.virality_scorer import score_virality
from tests.hotspot_factories import (
    cluster,
    editorial_signals,
    record,
    trend,
    verification,
)

CONFIG = load_config("configs/default.yaml").hotspot
AS_OF = datetime.fromisoformat("2026-08-10T20:00:00+08:00")


def _inputs():
    records = [
        record("w", "weibo", 1, "事件"),
        record("b", "baidu", 4, "事件"),
        record("z", "zhihu", 8, "事件"),
        record("k", "kuaishou", 9, "事件"),
    ]
    event = cluster(records)
    event_trend = trend()
    evidence = verification()
    verified = verify_candidate(event, evidence, as_of=AS_OF, max_age_hours=24)
    gate = evaluate_virality_gate(event, event_trend, records, verified, CONFIG)
    return records, event, event_trend, evidence, verified, gate


def test_score_uses_exact_confirmed_weights_and_is_replayable():
    records, event, event_trend, evidence, verified, gate = _inputs()
    first = score_virality(
        event,
        event_trend,
        records,
        evidence,
        verified,
        editorial_signals(),
        gate,
        CONFIG,
    )
    second = score_virality(
        event,
        event_trend,
        records,
        evidence,
        verified,
        editorial_signals(),
        gate,
        CONFIG,
    )
    assert first == second
    assert first.rule_version == "viral-v1.1"
    assert first.cross_platform_resonance == 25
    assert first.trend_velocity == 14.5
    assert first.conflict_suspense == 13.5
    assert first.public_interest == 9
    assert first.curiosity_gap == 9
    assert first.visual_impact == 8
    assert first.explanatory_depth == 4
    assert first.fact_safety == 5
    assert first.total == 88


def test_audited_subtopic_diffusion_contributes_inside_the_20_point_cap():
    records, event, event_trend, evidence, verified, gate = _inputs()
    baseline = score_virality(
        event,
        event_trend,
        records,
        evidence,
        verified,
        editorial_signals(),
        gate,
        CONFIG,
    )
    expanded = score_virality(
        event,
        event_trend.model_copy(update={"related_subtopic_count": 2}),
        records,
        evidence,
        verified,
        editorial_signals(),
        gate,
        CONFIG,
    )
    assert expanded.trend_velocity == baseline.trend_velocity + 2
    assert expanded.trend_velocity <= 20


def test_score_refuses_an_event_that_failed_a_hard_gate():
    records, event, event_trend, evidence, verified, gate = _inputs()
    rejected = gate.model_copy(update={"passed": False, "reasons": ["forced"]})
    with pytest.raises(ValueError, match="hard gates"):
        score_virality(
            event,
            event_trend,
            records,
            evidence,
            verified,
            editorial_signals(),
            rejected,
            CONFIG,
        )
