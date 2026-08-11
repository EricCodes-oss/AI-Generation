from datetime import date

from avatar_pipeline.hotspot_models import (
    EvaluatedHotspot,
    GateDecision,
    ShortVideoAssessment,
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


def _short_video_assessment(event_id, *, passed=True):
    return ShortVideoAssessment(
        event_id=event_id,
        passed=passed,
        required_platforms=["douyin", "xiaohongshu"],
        missing_platforms=[] if passed else ["xiaohongshu"],
        strong_platforms=["douyin", "xiaohongshu"] if passed else ["douyin"],
        platform_scores={"douyin": 0.9, "xiaohongshu": 0.8 if passed else None},
        checks={
            "short_video_evidence:douyin": True,
            "short_video_evidence:xiaohongshu": passed,
        },
        reasons=[] if passed else ["missing_short_video_evidence:xiaohongshu"],
    )


def _evaluated(event_id, total, *, passed=True, short_video_passed=True):
    records = [record(f"{event_id}-w", "weibo", 1, event_id)]
    return EvaluatedHotspot(
        cluster=cluster(records, event_id=event_id),
        trend=trend(event_id=event_id),
        gate=GateDecision(event_id=event_id, passed=passed, checks={}, reasons=[]),
        score=_score(event_id, total) if passed else None,
        verification=verification(event_id=event_id),
        editorial_signals=editorial_signals(event_id=event_id),
        short_video_assessment=_short_video_assessment(
            event_id, passed=short_video_passed
        ),
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
    assert "本轮导演首选" in render_hotspot_markdown(report)


def test_best_84_point_candidate_is_watch_only_without_director_recommendation():
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
    assert report.director_recommendation_event_id is None
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


def test_missing_xiaohongshu_keeps_candidate_watch_only_and_blocks_recommendation():
    report = build_hotspot_report(
        day=date(2026, 8, 11),
        rule_version="viral-v1.1",
        snapshot_ids=["t0", "t1", "t2"],
        failures=[],
        evaluations=[_evaluated("event-1", 92, short_video_passed=False)],
        display_score_min=75,
        strong_score_min=80,
        director_score_min=85,
        max_candidates=3,
    )
    assert report.outcome == "qualified_candidates"
    assert report.director_recommendation_event_id is None
    assert report.candidates[0].director_action.value == "watch"
    assert report.candidates[0].score_band.value == "strong_candidate"
    assert "missing_short_video_evidence:xiaohongshu" in report.candidates[0].risks
    rendered = render_hotspot_markdown(report)
    assert "导演首选" not in rendered
    assert "短视频适配证据不足" in rendered
