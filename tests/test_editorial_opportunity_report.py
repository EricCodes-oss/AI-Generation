from datetime import date

from avatar_pipeline.editorial_opportunity_report import render_editorial_opportunity_report
from avatar_pipeline.news_intelligence_models import (
    DirectorTopicCard,
    EditorialGrade,
    EditorialOpportunityPool,
    PoolQualityStatus,
)


def card(grade: EditorialGrade = EditorialGrade.S) -> DirectorTopicCard:
    return DirectorTopicCard(
        opportunity_id="odyssey",
        candidate_title="《奥德赛》为什么突然刷屏？",
        category="culture_entertainment",
        latest_development="影片进入上映窗口",
        why_today="解释型搜索和视频传播同步增加",
        heat_evidence=["跨平台讨论升温", "搜索问题集中出现"],
        strongest_tension="三千年史诗与现代电影工业的反差",
        ordinary_people_relevance="帮助观众理解刷屏内容",
        viewer_payoff="看懂原作、改编难点和当下热度原因",
        three_second_hook="一部三千年前的史诗，为什么突然刷屏？",
        reliable_fact_sources=["片方资料", "权威媒体报道"],
        footage_candidates=["官方预告片", "主创采访"],
        footage_risks=["预告片版权需记录"],
        expected_heat_lifetime="上映前后两周",
        grade=grade,
        score=89,
    )


def test_report_contains_director_review_fields_and_s_tier_status():
    pool = EditorialOpportunityPool(
        day=date(2026, 8, 13),
        candidates=[card()],
        quality_status=PoolQualityStatus.HAS_S_TIER,
    )
    report = render_editorial_opportunity_report(pool)
    assert "存在 S 级选题" in report
    assert "为什么是今天" in report
    assert "前三秒开场" in report
    assert "观众看完能得到什么" in report
    assert "素材清晰度与年代风险" in report


def test_report_explicitly_says_when_no_s_tier_exists():
    pool = EditorialOpportunityPool(
        day=date(2026, 8, 13),
        candidates=[card(EditorialGrade.A)],
        quality_status=PoolQualityStatus.NO_S_TIER,
    )
    assert "暂无 S 级选题" in render_editorial_opportunity_report(pool)
