import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from avatar_pipeline.hotspot_selection import (
    CandidatePoolStatus,
    DirectorRating,
    DisasterAssessment,
    DisasterEventType,
    HotspotCandidatePool,
    HotspotPoolCandidate,
    HotspotSelectionRepository,
    HotspotSelectionService,
    HotspotTopicCategory,
    LivelihoodAssessment,
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



def test_import_pool_excludes_recently_produced_semantic_duplicate(tmp_path: Path):
    workspace = tmp_path / "workspace"
    produced = tmp_path / "output" / "manual-news-2026-08-15-three-boys" / "production"
    produced.mkdir(parents=True)
    (produced / "topic-selection.json").write_text(
        """{
  "day": "2026-08-15",
  "candidate_id": "ordinary-moment-original",
  "title": "三个男孩得知小店即将闭店，凑出10.5元鼓励老板要挺住",
  "category": "ordinary_life_moment",
  "pool_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "approved": true,
  "actor": "owner",
  "reason": "confirmed",
  "approved_at": "2026-08-15T14:28:00+08:00"
}
""",
        encoding="utf-8",
    )
    repository = HotspotSelectionRepository(workspace)
    service = HotspotSelectionService(repository)
    current = HotspotCandidatePool(
        day=date(2026, 8, 17),
        candidates=[
            HotspotPoolCandidate(
                **candidate(30, HotspotTopicCategory.ORDINARY_PEOPLE).model_dump(
                    exclude={"candidate_id", "title", "latest_development"}
                ),
                candidate_id="resurfaced-three-boys",
                title="3名男孩10.5元为倒闭便利店融资",
                latest_development="旧事件再次进入平台热榜",
            ),
            candidate(31, HotspotTopicCategory.TECHNOLOGY),
        ],
    )

    imported = service.import_pool(date(2026, 8, 17), current)

    assert [item.candidate_id for item in imported.candidates] == ["candidate-31"]
    assert [item.candidate_id for item in repository.load_pool(date(2026, 8, 17)).candidates] == [
        "candidate-31"
    ]


def test_import_pool_keeps_old_topic_after_cooldown(tmp_path: Path):
    workspace = tmp_path / "workspace"
    selection_root = workspace / "hotspot-selections" / "2026-06-01"
    selection_root.mkdir(parents=True)
    approval = TopicSelectionApproval(
        day=date(2026, 6, 1),
        candidate_id="old-topic",
        title="候选话题1",
        category=HotspotTopicCategory.SOCIAL_LIVELIHOOD,
        pool_sha256="a" * 64,
        approved=True,
        actor="owner",
        reason="confirmed",
        approved_at=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
    )
    (selection_root / "topic-selection.json").write_text(
        approval.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    repository = HotspotSelectionRepository(workspace)
    service = HotspotSelectionService(repository)
    current = HotspotCandidatePool(
        day=date(2026, 8, 17),
        candidates=[candidate(1, HotspotTopicCategory.SOCIAL_LIVELIHOOD)],
    )

    imported = service.import_pool(date(2026, 8, 17), current)

    assert [item.candidate_id for item in imported.candidates] == ["candidate-1"]

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

@pytest.mark.parametrize(
    ("payload", "candidate_title"),
    [
        (
            {
                "date": "2026-08-14",
                "decision": "submit_one_only",
                "candidate": {
                    "topic": "西瓜少年母子通话后续",
                    "recommended_title": "一篇作文看哭全网，搬瓜少年终于收到妈妈的回应",
                },
            },
            "搬瓜少年母亲回应，一篇作文看哭全网",
        ),
        (
            {
                "run_id": "manual-news-2026-08-16-topic-v01",
                "selected_at": "2026-08-16T16:50:00+08:00",
                "topic": "秸秆露天焚烧管理转向科学精准管理",
                "approved": True,
            },
            "秸秆禁烧转向精准管理",
        ),
        (
            {
                "run_id": "manual-news-2026-08-17-topic-v01",
                "selected_at": "2026-08-17T09:20:00+08:00",
                "selected_title": "两台灭蚊机，为什么让打工人集体破防",
                "selection_mode": "user_supplied_and_approved",
            },
            "两台灭蚊机为何让打工人集体破防",
        ),
    ],
)
def test_import_pool_excludes_legacy_and_same_day_produced_topics(
    tmp_path: Path, payload: dict[str, object], candidate_title: str
):
    workspace = tmp_path / "workspace"
    produced = tmp_path / "output" / "manual-news-legacy" / "production"
    produced.mkdir(parents=True)
    (produced / "topic-selection.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    repository = HotspotSelectionRepository(workspace)
    service = HotspotSelectionService(repository)
    current = HotspotCandidatePool(
        day=date(2026, 8, 17),
        candidates=[
            HotspotPoolCandidate(
                **candidate(40, HotspotTopicCategory.SOCIAL_LIVELIHOOD).model_dump(
                    exclude={"candidate_id", "title", "latest_development"}
                ),
                candidate_id="legacy-resurface",
                title=candidate_title,
                latest_development="旧选题再次进入候选",
            )
        ],
    )

    imported = service.import_pool(date(2026, 8, 17), current)

    assert imported.candidates == []


def test_same_topic_matches_same_named_work_with_different_angles():
    from avatar_pipeline.hotspot_selection import _same_topic

    assert _same_topic("《牛来》网络口碑两极分化", "《牛来》观影吐槽视频") is True


def test_same_topic_rejects_conflicting_event_subjects():
    from avatar_pipeline.hotspot_selection import _same_topic

    assert _same_topic("全球最大全电动飞机完成首飞", "全球最大电动汽车完成首发") is False
    assert _same_topic("3名男孩10.5元为便利店融资", "3名女孩10.5元到便利店购物") is False


def livelihood_assessment(**overrides) -> LivelihoodAssessment:
    payload = {
        "affected_groups": ["普通居民", "上班族"],
        "direct_interest": "直接影响公共服务费用和办事权益",
        "effective_date": "2026-08-20",
        "previous_rule": "原规则按旧标准执行",
        "new_rule": "新规则按统一口径执行",
        "misconception_to_clarify": "并非所有人自动获得同额补贴",
        "required_action": "核对本地实施细则，无需抢办",
        "national_or_local_scope": "全国框架、地方细化",
        "exceptions_and_boundaries": "具体金额以当地公布为准",
        "direct_impact_score": 24,
        "recency_score": 18,
        "cognitive_conflict_score": 17,
        "affected_population_score": 13,
        "visual_material_score": 8,
        "authoritative_evidence_score": 9,
        "editorial_feedback_tags": ["明确实施日期", "政策变化", "误解澄清"],
    }
    payload.update(overrides)
    return LivelihoodAssessment(**payload)


def disaster_assessment(**overrides) -> DisasterAssessment:
    payload = {
        "event_type": DisasterEventType.FLOOD,
        "location": "某省某市",
        "occurred_at": "2026-08-18T03:00:00+08:00",
        "status_updated_at": "2026-08-18T10:30:00+08:00",
        "active": True,
        "casualties_or_missing_reported": False,
        "mass_evacuation_reported": True,
        "infrastructure_disruption_reported": False,
        "official_emergency_response_started": True,
        "secondary_risk_reported": True,
        "authoritative_fact_source_ids": ["source-90"],
        "footage_time_location_verified": True,
        "public_safety_value": "说明转移范围、道路中断和避险要求",
        "dignity_or_privacy_risk": "不使用伤亡特写和可识别受灾者隐私画面",
    }
    payload.update(overrides)
    return DisasterAssessment(**payload)


def assessed_candidate(
    index: int,
    category: HotspotTopicCategory,
    *,
    livelihood: LivelihoodAssessment | None = None,
    disaster: DisasterAssessment | None = None,
    rating: DirectorRating = DirectorRating.A,
) -> HotspotPoolCandidate:
    payload = candidate(index, category).model_dump()
    payload["director_rating"] = rating
    payload["livelihood_assessment"] = livelihood
    payload["disaster_assessment"] = disaster
    if disaster is not None:
        payload["authoritative_sources"] = [source(90)]
    return HotspotPoolCandidate.model_validate(payload)


def test_livelihood_assessment_scores_exact_weighted_total():
    assessment = livelihood_assessment()

    assert assessment.total_score == 89
    assert assessment.score_breakdown == {
        "direct_impact": 24,
        "recency": 18,
        "cognitive_conflict": 17,
        "affected_population": 13,
        "visual_material": 8,
        "authoritative_evidence": 9,
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("direct_impact_score", 26),
        ("recency_score", 21),
        ("cognitive_conflict_score", 21),
        ("affected_population_score", 16),
        ("visual_material_score", 11),
        ("authoritative_evidence_score", 11),
    ],
)
def test_livelihood_assessment_rejects_component_above_weight(field, value):
    with pytest.raises(ValueError):
        livelihood_assessment(**{field: value})


def test_disaster_fast_lane_requires_active_event_and_concrete_impact():
    assert disaster_assessment().qualifies_for_fast_lane is True
    assert disaster_assessment(active=False).qualifies_for_fast_lane is False
    assert (
        disaster_assessment(
            casualties_or_missing_reported=False,
            mass_evacuation_reported=False,
            infrastructure_disruption_reported=False,
            official_emergency_response_started=False,
            secondary_risk_reported=False,
        ).qualifies_for_fast_lane
        is False
    )


def test_disaster_candidate_rejects_unmatched_authoritative_source_reference():
    assessment = disaster_assessment(authoritative_fact_source_ids=["missing-source"])
    with pytest.raises(ValueError, match="authoritative disaster source"):
        assessed_candidate(
            90,
            HotspotTopicCategory.WEATHER_DISASTER,
            disaster=assessment,
        )


def test_import_pool_prioritizes_qualifying_disaster_then_livelihood_score(tmp_path: Path):
    repository = HotspotSelectionRepository(tmp_path / "workspace")
    service = HotspotSelectionService(repository)
    low = assessed_candidate(
        70,
        HotspotTopicCategory.CONSUMER,
        livelihood=livelihood_assessment(direct_impact_score=10),
        rating=DirectorRating.S,
    )
    high = assessed_candidate(
        71,
        HotspotTopicCategory.SOCIAL_LIVELIHOOD,
        livelihood=livelihood_assessment(direct_impact_score=25),
        rating=DirectorRating.A,
    )
    disaster = assessed_candidate(
        90,
        HotspotTopicCategory.WEATHER_DISASTER,
        livelihood=livelihood_assessment(direct_impact_score=12),
        disaster=disaster_assessment(),
        rating=DirectorRating.A,
    )
    pool = HotspotCandidatePool(
        day=date(2026, 8, 18),
        candidates=[low, high, disaster],
    )

    imported = service.import_pool(date(2026, 8, 18), pool)

    assert [item.candidate_id for item in imported.candidates] == [
        "candidate-90",
        "candidate-71",
        "candidate-70",
    ]


def test_candidate_report_exposes_livelihood_and_disaster_decision_evidence():
    from avatar_pipeline.hotspot_selection_report import render_candidate_pool_markdown

    item = assessed_candidate(
        90,
        HotspotTopicCategory.WEATHER_DISASTER,
        livelihood=livelihood_assessment(),
        disaster=disaster_assessment(),
    )
    report = render_candidate_pool_markdown(
        HotspotCandidatePool(day=date(2026, 8, 18), candidates=[item])
    )

    assert "民生利益评分：89/100" in report
    assert "影响人群：普通居民；上班族" in report
    assert "网络误解" in report
    assert "公众是否需要行动" in report
    assert "重大灾害突发通道：已进入" in report
    assert "2026-08-18T10:30:00+08:00" in report
    assert "素材时地核验：已完成" in report
