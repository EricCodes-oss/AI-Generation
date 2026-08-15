from datetime import date, datetime

import pytest
from pydantic import ValidationError

from avatar_pipeline.news_intelligence_models import (
    AttentionSignal,
    AttentionSourceKind,
    DirectorTopicCard,
    EditorialGrade,
    EditorialOpportunityPool,
    EditorialOpportunityScore,
    FactEvidence,
    FactEvidenceStatus,
    FactSourceTier,
    PoolQualityStatus,
    ScoreComponent,
)

NOW = datetime.fromisoformat("2026-08-13T10:00:00+08:00")


def test_attention_signal_cannot_claim_fact_evidence_role():
    with pytest.raises(ValidationError, match="attention signals cannot be fact evidence"):
        AttentionSignal(
            signal_id="signal-1",
            source_kind=AttentionSourceKind.DOMESTIC_BOARD,
            platform="baidu",
            captured_at=NOW,
            url_or_reference="baidu:topic",
            roles=["attention_signal", "fact_evidence"],
            raw_snapshot_path="raw/baidu.json",
            confidence=0.9,
        )


def test_fact_evidence_requires_first_party_tier_when_marked_first_party():
    with pytest.raises(ValidationError, match="first-party evidence"):
        FactEvidence(
            evidence_id="fact-1",
            claim_id="claim-1",
            claim_text="核心事实",
            source_name="媒体转载",
            source_tier=FactSourceTier.REPUTABLE_MEDIA,
            url_or_reference="https://example.test/report",
            status=FactEvidenceStatus.SUPPORTED,
            is_first_party=True,
            independent_source_group="media-a",
        )


def test_editorial_score_total_and_maximum_are_auditable():
    score = EditorialOpportunityScore(
        real_heat=ScoreComponent(score=30, maximum=30, reasons=["跨平台升温"]),
        content_attractiveness=ScoreComponent(score=35, maximum=35, reasons=["强知识缺口"]),
        fact_reliability=ScoreComponent(score=20, maximum=20, reasons=["第一方核验"]),
        video_potential=ScoreComponent(score=15, maximum=15, reasons=["真实连续素材"]),
    )
    assert score.total == 100
    assert score.maximum == 100


def test_pool_allows_fewer_than_three_candidates_and_reports_no_s_tier():
    card = DirectorTopicCard(
        opportunity_id="topic-a",
        candidate_title="A候选",
        category="technology",
        latest_development="今日发布最新进展",
        why_today="搜索需求与社交讨论同步上升",
        heat_evidence=["百度与X同时升温"],
        strongest_tension="高关注与信息缺口并存",
        ordinary_people_relevance="影响普通用户的选择",
        viewer_payoff="看懂事件原因和影响",
        three_second_hook="一项看似普通的更新，为什么突然引发争议？",
        reliable_fact_sources=["第一方公告"],
        footage_candidates=["发布会连续画面"],
        footage_risks=[],
        expected_heat_lifetime="24小时",
        grade=EditorialGrade.A,
        score=82,
        do_not_produce_reasons=[],
    )
    pool = EditorialOpportunityPool(
        day=date(2026, 8, 13),
        candidates=[card],
        quality_status=PoolQualityStatus.NO_S_TIER,
    )
    assert len(pool.candidates) == 1
    assert pool.quality_status is PoolQualityStatus.NO_S_TIER


def test_pool_rejects_more_than_eight_user_visible_candidates():
    cards = []
    for index in range(9):
        cards.append(
            DirectorTopicCard(
                opportunity_id=f"topic-{index}",
                candidate_title=f"候选{index}",
                category="technology",
                latest_development="今日进展",
                why_today="今天升温",
                heat_evidence=["多平台"],
                strongest_tension="反差",
                ordinary_people_relevance="相关",
                viewer_payoff="获得解释",
                three_second_hook="为什么突然发生？",
                reliable_fact_sources=["官方"],
                footage_candidates=["真实画面"],
                expected_heat_lifetime="24小时",
                grade=EditorialGrade.A,
                score=80,
            )
        )
    with pytest.raises(ValidationError):
        EditorialOpportunityPool(
            day=date(2026, 8, 13),
            candidates=cards,
            quality_status=PoolQualityStatus.NO_S_TIER,
        )
