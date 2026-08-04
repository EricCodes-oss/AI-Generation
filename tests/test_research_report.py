from datetime import UTC, date, datetime

from avatar_pipeline.models import ContentPillarSlug
from avatar_pipeline.research_models import (
    CollectionFailure,
    CommentInsightCard,
    CommentSampleType,
    ConfidenceLevel,
    DailyResearchPlan,
    EngagementMetrics,
    ImplicitNeed,
    QueryGroup,
    ResearchGrade,
    ResearchPlatform,
    ResearchRun,
    ResearchSource,
    TimeWindow,
)
from avatar_pipeline.research_report import build_report_summary, render_report_markdown

NOW = datetime(2026, 8, 4, 1, 0, tzinfo=UTC)
LONG_EXCERPT = "这是一段只应该存在于原始产物中的长正文。" * 30


def make_plan() -> DailyResearchPlan:
    pillars = tuple(ContentPillarSlug)
    groups = [
        QueryGroup(
            id=f"q-{index}",
            pillar=pillars[index // 3],
            intent=f"intent-{index}",
            scene=f"scene-{index}",
            natural_query=f"natural-query-{index}",
            platform_expressions={ResearchPlatform.XIAOHONGSHU: [f"query-{index}"]},
            time_window=(
                TimeWindow.LAST_72_HOURS
                if index < 5
                else TimeWindow.LAST_7_DAYS
                if index < 8
                else TimeWindow.LAST_30_DAYS
            ),
        )
        for index in range(9)
    ]
    return DailyResearchPlan(
        day=date(2026, 8, 4),
        core_groups=groups,
        time_window_shares={
            TimeWindow.LAST_72_HOURS: 0.5,
            TimeWindow.LAST_7_DAYS: 0.35,
            TimeWindow.LAST_30_DAYS: 0.15,
        },
        created_at=NOW,
    )


def make_source(
    index: int,
    platform: ResearchPlatform,
    pillar: ContentPillarSlug,
    *,
    grade: ResearchGrade = ResearchGrade.B,
) -> ResearchSource:
    return ResearchSource(
        id=f"source-{index}",
        platform=platform,
        query_group_id=f"q-{index}",
        title=f"来源标题 {index}",
        excerpt=LONG_EXCERPT,
        url=f"https://example.com/{index}",
        platform_content_id=f"content-{index}",
        pillar=pillar,
        grade=grade,
        metrics=EngagementMetrics(likes=index * 100),
        collector="fixture",
        collector_version="fixture-v1",
        raw_artifact_path=f"raw/source-{index}.json",
        raw_artifact_sha256=f"{index:064x}",
        collected_at=NOW,
        confidence=ConfidenceLevel.HIGH if index == 0 else ConfidenceLevel.MEDIUM,
    )


def make_run() -> ResearchRun:
    sources = [
        make_source(
            0,
            ResearchPlatform.DOUYIN,
            ContentPillarSlug.CAREER_PRESSURE,
            grade=ResearchGrade.A,
        ),
        make_source(
            1,
            ResearchPlatform.XIAOHONGSHU,
            ContentPillarSlug.CAREER_PRESSURE,
        ),
        make_source(
            2,
            ResearchPlatform.WECHAT_CHANNELS,
            ContentPillarSlug.PARENT_CHILD_COMMUNICATION,
        ),
    ]
    insight = CommentInsightCard(
        source_id="source-0",
        sample_count=20,
        sample_type_counts={sample_type: 4 for sample_type in CommentSampleType},
        scenes=["下班后仍在回复工作消息"],
        emotions=["疲惫"],
        inner_conflicts=["想休息又怕落后"],
        explicit_questions=["怎样停止内耗"],
        implicit_needs=[ImplicitNeed.BEING_SEEN],
        disagreement_signals=["少数人认为应先调整工作方式"],
        representative_paraphrases=["停下来时反而更不安"],
        comment_refs=[f"comment-{index}" for index in range(20)],
        privacy_notes=["已移除用户身份"],
        confidence=ConfidenceLevel.HIGH,
        created_at=NOW,
    )
    return ResearchRun(
        day=date(2026, 8, 4),
        plan=make_plan(),
        sources=sources,
        insight_cards=[insight],
        failures=[
            CollectionFailure(
                platform=ResearchPlatform.WECHAT_CHANNELS,
                capability="comments",
                message="评论不可稳定读取，需人工补充",
                error_code="manual_import_required",
                attempted_at=NOW,
            )
        ],
        created_at=NOW,
        updated_at=NOW,
    )


def test_summary_counts_sources_grades_platforms_pillars_and_limitations():
    summary = build_report_summary(make_run())

    assert summary.valid_source_count == 3
    assert summary.a_grade_source_count == 1
    assert summary.insight_card_count == 1
    assert summary.platform_counts == {
        ResearchPlatform.DOUYIN: 1,
        ResearchPlatform.XIAOHONGSHU: 1,
        ResearchPlatform.WECHAT_CHANNELS: 1,
    }
    assert summary.pillar_counts[ContentPillarSlug.CAREER_PRESSURE] == 2
    assert any("wechat_channels" in limitation for limitation in summary.limitations)


def test_report_contains_six_review_sections_counts_windows_and_provenance():
    report = render_report_markdown(make_run())

    for heading in (
        "## 一、采集说明",
        "## 二、分平台来源",
        "## 三、A 级内容评论洞察",
        "## 四、初步跨平台信号",
        "## 五、风险与覆盖缺口",
        "## 六、用户决策",
    ):
        assert heading in report

    assert "抖音：成功 1 条，失败 0 项" in report
    assert "视频号：成功 1 条，失败 1 项" in report
    assert "最近 72 小时：50%" in report
    assert "最近 7 天：35%" in report
    assert "最近 30 天：15%" in report
    assert "source-0" in report
    assert "raw/source-0.json" in report
    assert "可信度：high" in report
    assert "仅为初步信号" in report


def test_report_stays_in_research_scope_and_does_not_copy_long_bodies():
    report = render_report_markdown(make_run())

    assert "Top 3" not in report
    assert "TOP 3" not in report
    assert "脚本" not in report
    assert "跨平台原始互动量对比" not in report
    assert LONG_EXCERPT not in report
    assert "这是一段只应该存在于原始产物中的长正文" not in report
    assert "批准进入下一环节" in report
    assert "要求修改" in report
    assert "重做" in report
    assert "退回" in report
    assert "暂存" in report
