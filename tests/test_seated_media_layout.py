import pytest
from pydantic import ValidationError

from avatar_pipeline.media import validate_media_plan
from avatar_pipeline.models import (
    AvatarLayout,
    MediaKind,
    MediaPlan,
    MediaSegment,
    NewsScript,
    ScriptSegment,
)

HOST_ID = "host-main"


def script() -> NewsScript:
    return NewsScript(
        title="标题",
        spoken_segments=[ScriptSegment(id="s1", kind="fact", text="事实", source_ids=["src"])],
        source_ids=["src"],
    )


def seated_plan(**overrides: object) -> MediaPlan:
    values = {
        "duration_seconds": 15,
        "anchor_layout": AvatarLayout.SEATED_STUDIO_ANCHOR,
        "host_id": HOST_ID,
        "segments": [
            MediaSegment(
                id="a1",
                kind=MediaKind.ANCHOR,
                start_seconds=0,
                end_seconds=5,
                script_segment_id="s1",
                host_id=HOST_ID,
            ),
            MediaSegment(
                id="o1",
                kind=MediaKind.ORIGINAL_NEWS,
                start_seconds=5,
                end_seconds=10,
                script_segment_id="s1",
                source_id="src",
                provenance="src 00:01-00:06",
            ),
            MediaSegment(
                id="a2",
                kind=MediaKind.ANCHOR,
                start_seconds=10,
                end_seconds=15,
                script_segment_id="s1",
                host_id=HOST_ID,
            ),
        ],
    }
    values.update(overrides)
    return MediaPlan(**values)


def test_media_plan_declares_seated_anchor_layout_and_fixed_host():
    plan = seated_plan()

    assert plan.anchor_layout is AvatarLayout.SEATED_STUDIO_ANCHOR
    assert plan.host_id == HOST_ID
    validate_media_plan(plan, script())


def test_media_plan_rejects_non_seated_anchor_layout():
    with pytest.raises(ValidationError, match="anchor_layout"):
        seated_plan(anchor_layout="standing_anchor")


def test_media_plan_rejects_blank_host_id():
    with pytest.raises(ValidationError, match="host_id"):
        seated_plan(host_id="")


def test_validate_media_plan_rejects_non_seated_anchor_layout_even_if_model_is_bypassed():
    valid = seated_plan()
    invalid = MediaPlan.model_construct(
        duration_seconds=valid.duration_seconds,
        segments=valid.segments,
        subtitle_enabled=False,
        aspect_ratio="9:16",
        anchor_layout="standing_anchor",
        host_id=HOST_ID,
    )

    with pytest.raises(ValueError, match="seated_studio_anchor"):
        validate_media_plan(invalid, script())


def test_validate_media_plan_rejects_anchor_without_host_id():
    plan = seated_plan()
    plan.segments[0].host_id = None

    with pytest.raises(ValueError, match="anchor segment requires host_id"):
        validate_media_plan(plan, script())


def test_validate_media_plan_rejects_anchor_with_different_host_id():
    plan = seated_plan()
    plan.segments[-1].host_id = "another-host"

    with pytest.raises(ValueError, match="declared fixed host"):
        validate_media_plan(plan, script())
