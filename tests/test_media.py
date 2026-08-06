import pytest

from avatar_pipeline.media import validate_media_plan
from avatar_pipeline.models import MediaKind, MediaPlan, MediaSegment, NewsScript, ScriptSegment


def script():
    return NewsScript(
        title="标题",
        spoken_segments=[ScriptSegment(id="s1", kind="fact", text="事实", source_ids=["src"])],
        source_ids=["src"],
    )


def test_original_media_requires_provenance():
    plan = MediaPlan(
        duration_seconds=10,
        segments=[
            MediaSegment(
                id="a", kind="anchor", start_seconds=0, end_seconds=5, script_segment_id="s1"
            ),
            MediaSegment(
                id="o",
                kind=MediaKind.ORIGINAL_NEWS,
                start_seconds=5,
                end_seconds=10,
                script_segment_id="s1",
                source_id="src",
            ),
        ],
    )
    with pytest.raises(ValueError, match="provenance"):
        validate_media_plan(plan, script())


def test_ai_demo_requires_disclosure_and_fixed_structure():
    plan = MediaPlan(
        duration_seconds=10,
        segments=[
            MediaSegment(
                id="a", kind="anchor", start_seconds=0, end_seconds=5, script_segment_id="s1"
            ),
            MediaSegment(
                id="d",
                kind=MediaKind.AI_DEMO,
                start_seconds=5,
                end_seconds=10,
                script_segment_id="s1",
            ),
        ],
    )
    with pytest.raises(ValueError, match="disclosure"):
        validate_media_plan(plan, script())


def test_media_plan_accepts_anchor_insert_anchor_with_source_or_ai_disclosure():
    plan = MediaPlan(
        duration_seconds=15,
        segments=[
            MediaSegment(
                id="a1", kind="anchor", start_seconds=0, end_seconds=5, script_segment_id="s1"
            ),
            MediaSegment(
                id="o",
                kind=MediaKind.ORIGINAL_NEWS,
                start_seconds=5,
                end_seconds=10,
                script_segment_id="s1",
                source_id="src",
                provenance="src 00:01-00:06",
            ),
            MediaSegment(
                id="a2", kind="anchor", start_seconds=10, end_seconds=15, script_segment_id="s1"
            ),
        ],
    )
    validate_media_plan(plan, script())
