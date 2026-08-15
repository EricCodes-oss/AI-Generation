from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from avatar_pipeline.news_production_models import (
    AuthoritativeSource,
    DirectorCheck,
    DirectorReview,
    FactEvidence,
    FinalQualityReport,
    FootageAsset,
    FootageLedger,
    NewsRunManifest,
    NewsRunStatus,
    NewsTimeline,
    QualityCheck,
    ScriptReview,
    ShotSelection,
    ShotSelectionRecord,
    TimelineSegment,
)

NOW = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)


def source():
    return AuthoritativeSource(
        source_id="official-1",
        platform="official",
        title="权威通报",
        url="https://example.com/official",
        published_at=NOW,
    )


def approved_asset():
    return FootageAsset(
        asset_id="asset-1",
        source_platform="bilibili",
        source_url="https://example.com/video",
        downloaded_at=NOW,
        local_path="media/storm.mp4",
        sha256="a" * 64,
        watermark_free=True,
        platform_logo_free=True,
        account_mark_free=True,
        burned_caption_free=True,
        visual_relevance="strong_wind",
        user_usage_rule_passed=True,
    )


def approved_shot():
    return ShotSelectionRecord(
        shot_id="shot-1",
        asset_id="asset-1",
        script_segment_id="script-2",
        semantic_role="展示强风影响",
        source_in=2.0,
        source_out=7.5,
        target_duration_seconds=5.5,
        continuous_action=True,
        forward_playback=True,
        visual_quality_passed=True,
        director_approved=True,
    )


def test_fact_evidence_requires_authoritative_source_and_verified_fact():
    with pytest.raises(ValidationError, match="authoritative source"):
        FactEvidence(run_id="run-1", authoritative_sources=[], verified_facts=["事实"])
    with pytest.raises(ValidationError, match="verified fact"):
        FactEvidence(run_id="run-1", authoritative_sources=[source()], verified_facts=[])


def test_approved_script_review_requires_every_editorial_check():
    with pytest.raises(ValidationError, match="approved script review"):
        ScriptReview(
            run_id="run-1",
            script_path="copy/voiceover.txt",
            title_path="copy/title.txt",
            target_duration_seconds=60,
            actual_audio_duration_seconds=58.4,
            authoritative_tone_passed=False,
            sentence_clarity_passed=True,
            information_density_passed=True,
            ending_complete=True,
            facts_traceable=True,
            director_approved=True,
        )


def test_footage_usage_rule_allows_disclosed_source_marks_when_user_approved():
    payload = approved_asset().model_dump()
    payload.update(
        watermark_free=False,
        platform_logo_free=False,
        account_mark_free=False,
        visible_source_marks_allowed_by_user=True,
    )

    asset = FootageAsset.model_validate(payload)

    assert asset.user_usage_rule_passed is True
    assert asset.visible_source_marks_allowed_by_user is True


def test_footage_usage_rule_rejects_undisclosed_source_marks():
    payload = approved_asset().model_dump()
    payload["watermark_free"] = False
    with pytest.raises(ValidationError, match="source marks"):
        FootageAsset.model_validate(payload)


def test_footage_usage_rule_keeps_burned_captions_as_separate_policy():
    payload = approved_asset().model_dump()
    payload.update(
        burned_caption_free=False,
        visible_source_marks_allowed_by_user=True,
    )
    with pytest.raises(ValidationError, match="burned captions"):
        FootageAsset.model_validate(payload)

    payload["burned_captions_allowed_by_user"] = True
    asset = FootageAsset.model_validate(payload)
    assert asset.burned_captions_allowed_by_user is True


def test_shot_requires_forward_continuous_approved_interval():
    payload = approved_shot().model_dump()
    payload["source_out"] = payload["source_in"]
    with pytest.raises(ValidationError, match="source interval"):
        ShotSelectionRecord.model_validate(payload)
    payload = approved_shot().model_dump()
    payload["forward_playback"] = False
    with pytest.raises(ValidationError, match="forward"):
        ShotSelectionRecord.model_validate(payload)


def test_ledgers_require_unique_ids():
    with pytest.raises(ValidationError, match="asset IDs"):
        FootageLedger(run_id="run-1", assets=[approved_asset(), approved_asset()])
    with pytest.raises(ValidationError, match="shot IDs"):
        ShotSelection(run_id="run-1", shots=[approved_shot(), approved_shot()])


def test_timeline_must_be_contiguous_and_close_with_anchor():
    valid = [
        TimelineSegment(type="anchor", start=0, end=7, script_segment_id="script-1"),
        TimelineSegment(
            type="broll", start=7, end=12.5, script_segment_id="script-2", shot_id="shot-1"
        ),
        TimelineSegment(type="anchor", start=12.5, end=52, script_segment_id="script-3"),
    ]
    timeline = NewsTimeline(run_id="run-1", audio_duration_seconds=52, segments=valid)
    assert timeline.segments[-1].type == "anchor"
    gap = [valid[0], valid[1].model_copy(update={"start": 8}), valid[2]]
    with pytest.raises(ValidationError, match="gaps or overlaps"):
        NewsTimeline(run_id="run-1", audio_duration_seconds=52, segments=gap)
    with pytest.raises(ValidationError, match="close with the anchor"):
        NewsTimeline(
            run_id="run-1",
            audio_duration_seconds=52,
            segments=[valid[0], valid[1].model_copy(update={"end": 52})],
        )


def test_final_report_cannot_pass_with_failures_or_without_director_approval():
    failed = QualityCheck(
        id="streams",
        category="technical",
        severity="hard_block",
        expected="1 video stream",
        actual="2 video streams",
        status="FAIL",
        evidence_path="qc/ffprobe.json",
        checked_at=NOW,
    )
    approved_director = DirectorReview(
        run_id="run-1",
        approved=True,
        checks=[DirectorCheck(id="overall", description="整体效果", passed=True)],
        reviewed_at=NOW,
        actor="director",
    )
    with pytest.raises(ValidationError, match="failed checks"):
        FinalQualityReport(
            run_id="run-1",
            overall_passed=True,
            checks=[failed],
            director_review=approved_director,
            final_video_sha256="b" * 64,
        )
    rejected_director = approved_director.model_copy(update={"approved": False})
    with pytest.raises(ValidationError, match="director approval"):
        FinalQualityReport(
            run_id="run-1",
            overall_passed=True,
            checks=[],
            director_review=rejected_director,
            final_video_sha256="b" * 64,
        )


def test_manifest_uses_explicit_v5_statuses():
    manifest = NewsRunManifest(
        run_id="manual-news-2026-08-12-storm-v01",
        quality_profile="v5_vertical_anchor_news",
        quality_profile_version="1.0",
        topic="台风新闻",
        target_duration_seconds=60,
        host_id="host-c2-pro-candidate-2-final",
        host_reference_image="output/host.png",
        host_sha256="c" * 64,
        voice_id="voice-1",
        clean_master=True,
        status=NewsRunStatus.INITIALIZED,
        created_at=NOW,
    )
    assert manifest.status is NewsRunStatus.INITIALIZED
