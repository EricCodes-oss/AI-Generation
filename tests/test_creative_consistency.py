from datetime import UTC, datetime

from avatar_pipeline.creative_consistency import creative_consistency_failures
from avatar_pipeline.news_production_models import (
    CreativeLock,
    NewsTimeline,
    ShotSelection,
    ShotSelectionRecord,
    TimelineSegment,
)

NOW = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)


def lock(*, status: str = "locked", tags: list[str] | None = None) -> CreativeLock:
    return CreativeLock(
        run_id="run-1",
        status=status,
        core_subject="父亲托举少年上马",
        narrative_promise="让观众看到父子共同完成的上马瞬间和传承意味。",
        required_visual_tags=tags or ["父亲", "少年", "托举上马"],
        non_negotiables=["核心人物和核心动作不能被泛化素材取代。"],
        replaceable_elements=["草原远景"],
        prohibited_substitutions=["不得以成年骑手、搏克或马队替代少年上马。"],
        uncertainty_policy="地点或习俗无法核验时只描述画面中可见动作，不作地域断言。",
        approval_basis="director_confirmed",
        locked_by="director",
        locked_at=NOW,
    )


def shot(tags: list[str]) -> ShotSelectionRecord:
    return ShotSelectionRecord(
        shot_id="shot-1",
        asset_id="asset-1",
        script_segment_id="s2",
        semantic_role="核心上马动作",
        source_in=0,
        source_out=8,
        target_duration_seconds=8,
        continuous_action=True,
        forward_playback=True,
        visual_quality_passed=True,
        director_approved=True,
        creative_tags=tags,
    )


def timeline() -> NewsTimeline:
    return NewsTimeline(
        run_id="run-1",
        audio_duration_seconds=52,
        segments=[
            TimelineSegment(type="anchor", start=0, end=7, script_segment_id="s1"),
            TimelineSegment(
                type="broll", start=7, end=15, script_segment_id="s2", shot_id="shot-1"
            ),
            TimelineSegment(type="anchor", start=15, end=52, script_segment_id="s3"),
        ],
    )


def test_core_visuals_are_required_and_adult_substitution_fails():
    failures = creative_consistency_failures(
        lock(),
        ShotSelection(run_id="run-1", shots=[shot(["成年骑手", "马队", "搏克"])]),
        timeline(),
    )

    assert "creative_lock:missing_required_visual:父亲" in failures
    assert "creative_lock:missing_required_visual:少年" in failures
    assert "creative_lock:missing_required_visual:托举上马" in failures


def test_locked_core_visuals_pass():
    failures = creative_consistency_failures(
        lock(),
        ShotSelection(run_id="run-1", shots=[shot(["父亲", "少年", "托举上马"])]),
        timeline(),
    )

    assert failures == []


def test_draft_lock_is_a_hard_failure():
    failures = creative_consistency_failures(
        lock(status="draft"),
        ShotSelection(run_id="run-1", shots=[shot(["父亲", "少年", "托举上马"])]),
        timeline(),
    )

    assert failures == ["creative_lock:not_locked"]
