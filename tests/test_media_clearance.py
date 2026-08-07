import pytest
from pydantic import ValidationError

from avatar_pipeline.media_clearance import (
    MediaEvidence,
    MediaInspection,
    decide_media_clearance,
    require_production_media_clearance,
)
from avatar_pipeline.research_models import MediaClearanceStatus


def evidence(**overrides):
    payload = {
        "asset_id": "asset-1",
        "origin": "douyin",
        "origin_url": "https://example.test/video/1",
        "rights_reference": "授权文件-1",
        "watermark_detected": False,
        "logo_detected": False,
        "account_mark_detected": False,
        "qr_code_detected": False,
        "ai_generated": False,
        "non_replicative": False,
    }
    payload.update(overrides)
    return MediaEvidence.model_validate(payload)


def test_platform_research_evidence_is_not_production_media_by_default():
    result = decide_media_clearance(evidence(rights_reference=None))

    assert isinstance(result, MediaInspection)
    assert result.status is MediaClearanceStatus.REJECTED_UNCLEARED
    assert result.production_allowed is False
    assert result.fallback_plan


def test_watermark_logo_account_mark_and_qr_code_fail_closed():
    for field in (
        "watermark_detected",
        "logo_detected",
        "account_mark_detected",
        "qr_code_detected",
    ):
        result = decide_media_clearance(evidence(**{field: True}))
        assert result.status is MediaClearanceStatus.REJECTED_WATERMARK
        assert result.production_allowed is False


def test_authorized_clean_original_media_passes():
    result = decide_media_clearance(evidence(origin="authorized_original"))

    assert result.status is MediaClearanceStatus.AUTHORIZED_ORIGINAL
    assert result.production_allowed is True


def test_ai_illustrative_media_requires_non_replication_and_disclosure():
    result = decide_media_clearance(
        evidence(
            origin="seedance",
            rights_reference=None,
            ai_generated=True,
            non_replicative=True,
            ai_disclosure="AI生成示意画面",
        )
    )

    assert result.status is MediaClearanceStatus.AI_ILLUSTRATIVE
    assert result.production_allowed is True


def test_ai_media_without_disclosure_or_non_replication_is_rejected():
    for overrides in (
        {"origin": "seedance", "ai_generated": True, "non_replicative": True},
        {
            "origin": "seedance",
            "ai_generated": True,
            "non_replicative": False,
            "ai_disclosure": "AI生成示意画面",
        },
    ):
        result = decide_media_clearance(evidence(rights_reference=None, **overrides))
        assert result.production_allowed is False
        assert result.status is MediaClearanceStatus.REJECTED_UNCLEARED


def test_required_clearance_raises_with_fail_closed_reason():
    with pytest.raises(ValueError, match="watermark"):
        require_production_media_clearance(evidence(watermark_detected=True))


def test_credentials_and_unknown_fields_are_not_accepted():
    with pytest.raises(ValidationError):
        evidence(cookie="must-not-be-persisted")


def _production_plan(kind, *, asset_path, disclosure=None):
    from avatar_pipeline.models import MediaKind, MediaPlan, MediaSegment

    host_id = "host-main"
    return MediaPlan(
        duration_seconds=15,
        host_id=host_id,
        segments=[
            MediaSegment(
                id="a1",
                kind=MediaKind.ANCHOR,
                start_seconds=0,
                end_seconds=5,
                script_segment_id="s1",
                host_id=host_id,
            ),
            MediaSegment(
                id="insert",
                kind=kind,
                start_seconds=5,
                end_seconds=10,
                script_segment_id="s1",
                source_id="src" if kind is MediaKind.ORIGINAL_NEWS else None,
                provenance="官方授权素材" if kind is MediaKind.ORIGINAL_NEWS else None,
                disclosure=disclosure,
                asset_path=asset_path,
            ),
            MediaSegment(
                id="a2",
                kind=MediaKind.ANCHOR,
                start_seconds=10,
                end_seconds=15,
                script_segment_id="s1",
                host_id=host_id,
            ),
        ],
    )


def _production_script():
    from avatar_pipeline.models import NewsScript, ScriptSegment

    return NewsScript(
        title="标题",
        spoken_segments=[ScriptSegment(id="s1", kind="fact", text="事实", source_ids=["src"])],
        source_ids=["src"],
    )


def test_media_plan_with_acquired_original_asset_requires_clearance_metadata():
    from avatar_pipeline.media import validate_media_plan
    from avatar_pipeline.models import MediaKind

    media_plan = _production_plan(MediaKind.ORIGINAL_NEWS, asset_path="clip.mp4")

    with pytest.raises(ValueError, match="clearance metadata"):
        validate_media_plan(media_plan, _production_script())


def test_media_plan_rejects_watermarked_acquired_asset():
    from avatar_pipeline.media import validate_media_plan
    from avatar_pipeline.models import MediaKind

    media_plan = _production_plan(MediaKind.ORIGINAL_NEWS, asset_path="clip.mp4")

    with pytest.raises(ValueError, match="watermark"):
        validate_media_plan(
            media_plan,
            _production_script(),
            media_evidence={"clip.mp4": evidence(watermark_detected=True)},
        )


def test_media_plan_accepts_cleared_acquired_asset():
    from avatar_pipeline.media import validate_media_plan
    from avatar_pipeline.models import MediaKind

    media_plan = _production_plan(MediaKind.ORIGINAL_NEWS, asset_path="clip.mp4")

    validate_media_plan(
        media_plan,
        _production_script(),
        media_evidence={"clip.mp4": evidence(origin="authorized_original")},
    )
