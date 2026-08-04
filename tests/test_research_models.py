from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

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
    ResearchReportSummary,
    ResearchRun,
    ResearchRunStatus,
    ResearchSource,
    SkillExecutionRecord,
    TimeWindow,
)

NOW = datetime(2026, 8, 4, 1, 0, tzinfo=UTC)
PILLARS = (
    ContentPillarSlug.CAREER_PRESSURE,
    ContentPillarSlug.PARENT_CHILD_COMMUNICATION,
    ContentPillarSlug.SELF_GROWTH,
)


def make_group(index: int, pillar: ContentPillarSlug, *, expansion: bool = False) -> QueryGroup:
    return QueryGroup(
        id=f"q-{index}",
        pillar=pillar,
        intent=f"intent-{index}",
        scene=f"scene-{index}",
        platform_expressions={ResearchPlatform.XIAOHONGSHU: [f"query-{index}"]},
        time_window=TimeWindow.LAST_72_HOURS,
        is_expansion=expansion,
        parent_query_id="q-0" if expansion else None,
        expansion_reason="discovered term" if expansion else None,
    )


def make_plan(*, expansions: int = 0) -> DailyResearchPlan:
    core = [make_group(i, PILLARS[i // 3]) for i in range(9)]
    extra = [make_group(100 + i, PILLARS[i % 3], expansion=True) for i in range(expansions)]
    return DailyResearchPlan(
        day=date(2026, 8, 4),
        core_groups=core,
        expansion_groups=extra,
        time_window_shares={
            TimeWindow.LAST_72_HOURS: 0.5,
            TimeWindow.LAST_7_DAYS: 0.35,
            TimeWindow.LAST_30_DAYS: 0.15,
        },
        created_at=NOW,
    )


def make_source(index: int, *, grade: ResearchGrade = ResearchGrade.B) -> ResearchSource:
    return ResearchSource(
        id=f"source-{index}",
        platform=ResearchPlatform.XIAOHONGSHU,
        query_group_id=f"q-{index % 9}",
        title=f"source title {index}",
        excerpt=f"source excerpt {index}",
        url=f"https://example.com/source/{index}",
        platform_content_id=f"note-{index}",
        pillar=PILLARS[index % 3],
        grade=grade,
        metrics=EngagementMetrics(likes=index * 10),
        collector="fixture",
        collector_version="1.0.0",
        raw_artifact_path=f"raw/source-{index}.json",
        raw_artifact_sha256=f"{index:064x}",
        collected_at=NOW,
        confidence=ConfidenceLevel.HIGH,
    )


def make_insight(source_id: str) -> CommentInsightCard:
    return CommentInsightCard(
        source_id=source_id,
        sample_count=20,
        sample_type_counts={
            CommentSampleType.HIGH_LIKE: 6,
            CommentSampleType.LIVED_EXPERIENCE: 5,
            CommentSampleType.HELP_SEEKING: 4,
            CommentSampleType.DISAGREEMENT: 3,
            CommentSampleType.LATEST: 2,
        },
        scenes=["下班后仍在回复工作消息"],
        emotions=["疲惫"],
        inner_conflicts=["想休息但担心落后"],
        explicit_questions=["怎样停止内耗"],
        implicit_needs=[ImplicitNeed.BEING_SEEN],
        representative_paraphrases=["努力很久仍觉得自己不够好"],
        comment_refs=[f"{source_id}:comment-1"],
        confidence=ConfidenceLevel.HIGH,
        created_at=NOW,
    )


def test_daily_plan_requires_exactly_nine_core_groups_and_three_per_pillar():
    assert len(make_plan().core_groups) == 9

    with pytest.raises(ValidationError, match="exactly 9 core query groups"):
        DailyResearchPlan(
            day=date(2026, 8, 4),
            core_groups=[make_group(i, PILLARS[i % 3]) for i in range(8)],
            time_window_shares={
                TimeWindow.LAST_72_HOURS: 0.5,
                TimeWindow.LAST_7_DAYS: 0.35,
                TimeWindow.LAST_30_DAYS: 0.15,
            },
            created_at=NOW,
        )

    unbalanced = [make_group(i, ContentPillarSlug.CAREER_PRESSURE) for i in range(9)]
    with pytest.raises(ValidationError, match="3 core query groups per pillar"):
        DailyResearchPlan(
            day=date(2026, 8, 4),
            core_groups=unbalanced,
            time_window_shares={
                TimeWindow.LAST_72_HOURS: 0.5,
                TimeWindow.LAST_7_DAYS: 0.35,
                TimeWindow.LAST_30_DAYS: 0.15,
            },
            created_at=NOW,
        )


def test_plan_caps_expansions_and_requires_time_shares_to_sum_to_one():
    assert len(make_plan(expansions=3).expansion_groups) == 3
    with pytest.raises(ValidationError, match="at most 3 expansion"):
        make_plan(expansions=4)

    payload = make_plan().model_dump()
    payload["time_window_shares"] = {
        TimeWindow.LAST_72_HOURS: 0.5,
        TimeWindow.LAST_7_DAYS: 0.3,
        TimeWindow.LAST_30_DAYS: 0.1,
    }
    with pytest.raises(ValidationError, match="sum to 1.0"):
        DailyResearchPlan.model_validate(payload)


def test_grades_are_only_a_b_or_c_and_unknown_metrics_remain_none():
    assert {grade.value for grade in ResearchGrade} == {"A", "B", "C"}
    metrics = EngagementMetrics()
    assert metrics.likes is None
    assert metrics.comments is None
    assert metrics.views is None
    assert metrics.shares is None
    assert metrics.saves is None


def test_source_requires_complete_provenance_and_aware_collection_time():
    source = make_source(1)
    assert source.raw_artifact_path == "raw/source-1.json"

    payload = source.model_dump()
    del payload["raw_artifact_sha256"]
    with pytest.raises(ValidationError, match="raw_artifact_sha256"):
        ResearchSource.model_validate(payload)

    payload = source.model_dump()
    payload["collected_at"] = datetime(2026, 8, 4, 1, 0)
    with pytest.raises(ValidationError, match="timezone-aware"):
        ResearchSource.model_validate(payload)


def test_run_allows_partial_drafts_but_rejects_duplicate_source_ids():
    draft = ResearchRun(day=date(2026, 8, 4), plan=make_plan(), sources=[make_source(1)])
    assert draft.status is ResearchRunStatus.DRAFT
    assert draft.is_approvable() is False

    with pytest.raises(ValidationError, match="source ids must be unique"):
        ResearchRun(
            day=date(2026, 8, 4),
            plan=make_plan(),
            sources=[make_source(1), make_source(1)],
        )


def test_approvable_run_requires_30_to_40_sources_and_5_to_8_a_grade_insight_cards():
    sources = [
        make_source(i, grade=ResearchGrade.A if i < 5 else ResearchGrade.B) for i in range(30)
    ]
    insights = [make_insight(f"source-{i}") for i in range(5)]
    run = ResearchRun(
        day=date(2026, 8, 4),
        status=ResearchRunStatus.READY_FOR_REVIEW,
        revision=2,
        plan=make_plan(),
        sources=sources,
        insight_cards=insights,
        summary=ResearchReportSummary(
            valid_source_count=30,
            a_grade_source_count=5,
            insight_card_count=5,
            platform_counts={ResearchPlatform.XIAOHONGSHU: 30},
        ),
        failures=[
            CollectionFailure(
                platform=ResearchPlatform.WECHAT_CHANNELS,
                capability="search",
                message="manual import required",
                attempted_at=NOW,
            )
        ],
        skill_executions=[
            SkillExecutionRecord(
                skill_name="daily-hotspot-research",
                skill_version="1.0.0",
                started_at=NOW,
                completed_at=NOW,
                output_artifact="reports/daily.md",
            )
        ],
    )
    assert run.is_approvable() is True

    too_few_cards = run.model_copy(update={"insight_cards": insights[:4]})
    assert too_few_cards.is_approvable() is False

    non_a_source = [*sources]
    non_a_source[0] = make_source(0, grade=ResearchGrade.B)
    wrong_grade = run.model_copy(update={"sources": non_a_source})
    assert wrong_grade.is_approvable() is False


def test_eldercare_pillar_and_topic_or_script_fields_are_rejected():
    payload = make_group(1, ContentPillarSlug.CAREER_PRESSURE).model_dump()
    payload["pillar"] = "eldercare"
    with pytest.raises(ValidationError):
        QueryGroup.model_validate(payload)

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ResearchRun.model_validate(
            {
                "day": "2026-08-04",
                "topic_candidates": [],
                "script_text": "not allowed",
            }
        )
