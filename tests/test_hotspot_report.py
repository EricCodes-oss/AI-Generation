from datetime import date

from avatar_pipeline.hotspot_models import (
    EvaluatedHotspot,
    GateDecision,
    ViralityScore,
)
from avatar_pipeline.hotspot_report import build_hotspot_report, render_hotspot_markdown
from tests.hotspot_factories import cluster, editorial_signals, record, trend, verification


def _score(event_id, total):
    capacities = [25, 20, 15, 10, 10, 10, 5, 5]
    remaining = float(total)
    values = []
    for capacity in capacities:
        value = min(remaining, capacity)
        values.append(value)
        remaining -= value
    return ViralityScore(
        event_id=event_id,
        rule_version="viral-v1.0",
        cross_platform_resonance=values[0],
        trend_velocity=values[1],
        conflict_suspense=values[2],
        public_interest=values[3],
        curiosity_gap=values[4],
        visual_impact=values[5],
        explanatory_depth=values[6],
        fact_safety=values[7],
        total=total,
    )


def _evaluated(event_id, total, *, passed=True):
    records = [record(f"{event_id}-w", "weibo", 1, event_id)]
    return EvaluatedHotspot(
        cluster=cluster(records, event_id=event_id),
        trend=trend(event_id=event_id),
        gate=GateDecision(event_id=event_id, passed=passed, checks={}, reasons=[]),
        score=_score(event_id, total) if passed else None,
        verification=verification(event_id=event_id),
        editorial_signals=editorial_signals(event_id=event_id),
    )


def test_report_keeps_only_passing_scores_at_least_75_and_caps_three():
    report = build_hotspot_report(
        day=date(2026, 8, 10),
        rule_version="viral-v1.0",
        snapshot_ids=["t0", "t1", "t2"],
        failures=[],
        evaluations=[
            _evaluated("e1", 86),
            _evaluated("e2", 84),
            _evaluated("e3", 79),
            _evaluated("e4", 78),
            _evaluated("low", 74),
            _evaluated("rejected", 99, passed=False),
        ],
        display_score_min=75,
        strong_score_min=80,
        director_score_min=85,
        max_candidates=3,
    )
    assert [item.event_id for item in report.candidates] == ["e1", "e2", "e3"]
    assert report.director_recommendation_event_id == "e1"
    assert [item.score_band.value for item in report.candidates] == [
        "director_first",
        "strong_candidate",
        "backup",
    ]
    assert report.outcome == "qualified_candidates"
    assert "全网最热" not in render_hotspot_markdown(report)
    assert "本轮跨平台综合评分第一" in render_hotspot_markdown(report)


def test_best_84_point_candidate_is_still_recommended_without_director_first_band():
    report = build_hotspot_report(
        day=date(2026, 8, 10),
        rule_version="viral-v1.0",
        snapshot_ids=["t0", "t1", "t2"],
        failures=[],
        evaluations=[_evaluated("best", 84), _evaluated("second", 81)],
        display_score_min=75,
        strong_score_min=80,
        director_score_min=85,
        max_candidates=3,
    )
    assert report.director_recommendation_event_id == "best"
    assert report.candidates[0].score_band.value == "strong_candidate"
    assert report.candidates[0].director_action.value == "watch"


def test_no_qualified_event_returns_explicit_safe_stop_outcome():
    report = build_hotspot_report(
        day=date(2026, 8, 10),
        rule_version="viral-v1.0",
        snapshot_ids=["t0"],
        failures=[],
        evaluations=[_evaluated("low", 74)],
        display_score_min=75,
        strong_score_min=80,
        director_score_min=85,
        max_candidates=3,
    )
    assert report.candidates == []
    assert report.director_recommendation_event_id is None
    assert report.outcome == "no_qualified_hotspot"
