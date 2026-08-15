from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from avatar_pipeline.hotspot_selection import (
    CandidatePoolStatus,
    DirectorRating,
    HotspotCandidatePool,
    HotspotPoolCandidate,
    HotspotSelectionRepository,
    HotspotSelectionService,
    HotspotTopicCategory,
    TopicSelectionApproval,
)
from avatar_pipeline.models import SourceEvidence

NOW = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)


def source(index: int = 1) -> SourceEvidence:
    return SourceEvidence(
        source_id=f"source-{index}",
        platform="news.cn",
        title=f"权威来源{index}",
        url_or_reference=f"https://example.com/{index}",
        evidence_type="reputable_media",
        published_at=NOW,
    )


def candidate(index: int, category: HotspotTopicCategory) -> HotspotPoolCandidate:
    return HotspotPoolCandidate(
        candidate_id=f"candidate-{index}",
        title=f"候选话题{index}",
        category=category,
        latest_development=f"2026年8月12日最新进展{index}",
        heat_basis=["多平台集中传播", "权威媒体当天更新"],
        authoritative_sources=[source(index)],
        why_watch="与公众利益直接相关，并有明确的新变化。",
        visual_material_plan=["权威媒体现场视频", "事件相关实景画面"],
        suggested_title=f"候选话题{index}出现新变化",
        risks=["正式制作前复核最新状态"],
        director_rating=DirectorRating.A,
    )


def pool() -> HotspotCandidatePool:
    categories = [
        HotspotTopicCategory.SOCIAL_LIVELIHOOD,
        HotspotTopicCategory.TECHNOLOGY,
        HotspotTopicCategory.FINANCE,
        HotspotTopicCategory.INTERNATIONAL,
        HotspotTopicCategory.POLICY,
        HotspotTopicCategory.CONSUMER,
        HotspotTopicCategory.EDUCATION,
        HotspotTopicCategory.ORDINARY_PEOPLE,
    ]
    return HotspotCandidatePool(
        day=date(2026, 8, 12),
        candidates=[candidate(i + 1, item) for i, item in enumerate(categories)],
        status=CandidatePoolStatus.AWAITING_USER_EVALUATION,
    )


def test_pool_allows_dynamic_candidates_without_category_padding():
    valid = pool()
    assert len(valid.candidates) == 8
    assert len(valid.covered_categories) == 8

    small = HotspotCandidatePool(
        day=date(2026, 8, 12),
        candidates=valid.candidates[:2],
        status=CandidatePoolStatus.AWAITING_USER_EVALUATION,
    )
    assert len(small.candidates) == 2
    assert len(small.covered_categories) == 2

    with pytest.raises(ValueError, match="at most 8"):
        HotspotCandidatePool(
            day=date(2026, 8, 12),
            candidates=valid.candidates + [candidate(9, HotspotTopicCategory.INFLUENCER)],
            status=CandidatePoolStatus.AWAITING_USER_EVALUATION,
        )


def test_selection_is_persisted_and_bound_to_pool_hash(tmp_path: Path):
    repository = HotspotSelectionRepository(tmp_path)
    service = HotspotSelectionService(repository)
    saved_pool = service.import_pool(date(2026, 8, 12), pool())
    approval = service.select(
        date(2026, 8, 12),
        candidate_id="candidate-2",
        actor="owner",
        reason="共同评估后确认",
    )
    assert approval.approved is True
    assert approval.candidate_id == "candidate-2"
    assert approval.pool_sha256 == repository.pool_sha256(date(2026, 8, 12))
    assert saved_pool.status is CandidatePoolStatus.AWAITING_USER_EVALUATION
    assert repository.load_selection(date(2026, 8, 12)) == approval


def test_selection_rejects_unknown_candidate(tmp_path: Path):
    repository = HotspotSelectionRepository(tmp_path)
    service = HotspotSelectionService(repository)
    service.import_pool(date(2026, 8, 12), pool())
    with pytest.raises(ValueError, match="not found"):
        service.select(
            date(2026, 8, 12),
            candidate_id="missing",
            actor="owner",
            reason="确认",
        )


def test_approval_json_round_trip():
    approval = TopicSelectionApproval(
        day=date(2026, 8, 12),
        candidate_id="candidate-1",
        title="候选话题1",
        category=HotspotTopicCategory.SOCIAL_LIVELIHOOD,
        pool_sha256="a" * 64,
        approved=True,
        actor="owner",
        reason="共同评估后确认",
        approved_at=NOW,
    )
    assert TopicSelectionApproval.model_validate_json(approval.model_dump_json()) == approval


def test_candidate_pool_markdown_exposes_joint_evaluation_gate_and_sources():
    from avatar_pipeline.hotspot_selection_report import render_candidate_pool_markdown

    report = render_candidate_pool_markdown(pool())
    assert "当前状态：等待用户共同评估" in report
    assert "未确认前禁止进入 V5 生产" in report
    assert "候选话题1" in report
    assert "权威来源1" in report
    assert "观看动机" in report
    assert "导演评级" in report


def ordinary_moment_assessment(**overrides):
    from avatar_pipeline.ordinary_moments import OrdinaryMomentAssessment, RecordingOrigin

    payload = {
        "recording_origin": RecordingOrigin.DASHCAM,
        "creator_is_professional_influencer": False,
        "account_is_personal_daily_recorder": True,
        "ordinary_people_are_primary_subjects": True,
        "event_was_creator_initiated": False,
        "event_preexisted_filming": True,
        "event_is_daily_life_context": True,
        "natural_reaction_evidence": ["行车记录仪连续拍下，参与者未面向镜头表演"],
        "human_warmth_evidence": ["陌生人看到老人需要帮助后自然上前搀扶"],
        "original_recorder_available": True,
        "ambient_audio_available": True,
        "continuous_scene_available": True,
        "staging_risk": 0.1,
    }
    payload.update(overrides)
    return OrdinaryMomentAssessment(**payload)


def natural_moment_candidate(index: int) -> HotspotPoolCandidate:
    payload = candidate(index, HotspotTopicCategory.ORDINARY_PEOPLE).model_dump()
    payload["category"] = HotspotTopicCategory.ORDINARY_LIFE_MOMENT
    payload["ordinary_moment_assessment"] = ordinary_moment_assessment()
    return HotspotPoolCandidate.model_validate(payload)


def test_ordinary_life_moment_accepts_only_natural_non_influencer_recording():
    validated = natural_moment_candidate(20)
    assert validated.ordinary_moment_assessment.eligible is True


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"creator_is_professional_influencer": True}, "professional influencer"),
        ({"account_is_personal_daily_recorder": False}, "personal daily recorder"),
        (
            {"ordinary_people_are_primary_subjects": False},
            "ordinary people must be the primary subjects",
        ),
        ({"event_was_creator_initiated": True}, "creator-initiated"),
        ({"event_preexisted_filming": False}, "preexist filming"),
        ({"event_is_daily_life_context": False}, "daily-life context"),
        (
            {"human_warmth_evidence": [], "natural_reaction_evidence": ["连续画面"]},
            "at least 1 item",
        ),
        ({"staging_risk": 0.6}, "staging risk"),
    ],
)
def test_ordinary_life_moment_rejects_creator_content_and_staging(overrides, message):
    with pytest.raises(ValueError, match=message):
        HotspotPoolCandidate(
            **candidate(21, HotspotTopicCategory.ORDINARY_PEOPLE).model_dump(
                exclude={"candidate_id", "category", "ordinary_moment_assessment"}
            ),
            candidate_id="natural-moment",
            category=HotspotTopicCategory.ORDINARY_LIFE_MOMENT,
            ordinary_moment_assessment=ordinary_moment_assessment(**overrides),
        )


def test_ordinary_life_moment_requires_audit_assessment():
    with pytest.raises(ValueError, match="ordinary moment assessment"):
        candidate(22, HotspotTopicCategory.ORDINARY_LIFE_MOMENT)


def test_candidate_pool_report_exposes_ordinary_moment_audit():
    from avatar_pipeline.hotspot_selection_report import render_candidate_pool_markdown

    item = natural_moment_candidate(23)
    report = render_candidate_pool_markdown(
        HotspotCandidatePool(day=date(2026, 8, 15), candidates=[item])
    )
    assert "普通人自然瞬间核验" in report
    assert "行车记录仪" in report
    assert "非职业博主/网红" in report
    assert "普通人个人生活记录账号" in report
    assert "普通人是画面主体" in report
    assert "真实日常生活场景" in report
    assert "自然真情/善意证据" in report
    assert "事件先于拍摄自然发生" in report
