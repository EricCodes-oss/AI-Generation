from datetime import date, timedelta
from pathlib import Path

from avatar_pipeline.config import load_config
from avatar_pipeline.models import ContentPillarSlug
from avatar_pipeline.query_planner import build_daily_plan, expand_plan
from avatar_pipeline.research_models import DailyResearchPlan, ResearchPlatform, TimeWindow

CONFIG = load_config(Path("configs/default.yaml"))
DAY = date(2026, 8, 4)
CORE_PLATFORMS = {
    ResearchPlatform.DOUYIN,
    ResearchPlatform.WECHAT_CHANNELS,
    ResearchPlatform.XIAOHONGSHU,
}


def expressions(plan: DailyResearchPlan) -> set[str]:
    return {
        expression
        for group in plan.core_groups
        for platform_expressions in group.platform_expressions.values()
        for expression in platform_expressions
    }


def replace_groups(
    plan: DailyResearchPlan,
    *,
    day: date,
    expression_suffix: str = "",
    result_count: int | None = None,
) -> DailyResearchPlan:
    groups = []
    for group in plan.core_groups:
        updated_expressions = {
            platform: [f"{value}{expression_suffix}" for value in values]
            for platform, values in group.platform_expressions.items()
        }
        groups.append(
            group.model_copy(
                update={
                    "platform_expressions": updated_expressions,
                    "result_count": result_count,
                }
            )
        )
    return plan.model_copy(update={"day": day, "core_groups": groups})


def test_builds_nine_balanced_platform_aware_groups_with_approved_windows():
    plan = build_daily_plan(DAY, CONFIG.research, history=[])

    assert len(plan.core_groups) == 9
    assert {
        pillar: sum(group.pillar is pillar for group in plan.core_groups)
        for pillar in ContentPillarSlug
    } == {pillar: 3 for pillar in ContentPillarSlug}
    assert all(set(group.platform_expressions) >= CORE_PLATFORMS for group in plan.core_groups)
    assert plan.time_window_shares == {
        TimeWindow.LAST_72_HOURS: 0.5,
        TimeWindow.LAST_7_DAYS: 0.35,
        TimeWindow.LAST_30_DAYS: 0.15,
    }
    assert all("养老" not in str(group.model_dump()) for group in plan.core_groups)
    assert build_daily_plan(DAY, CONFIG.research, history=[]) == plan


def test_exact_queries_used_within_seven_days_are_not_repeated():
    baseline = build_daily_plan(DAY, CONFIG.research, history=[])
    history = [replace_groups(baseline, day=DAY - timedelta(days=1))]

    rotated = build_daily_plan(DAY, CONFIG.research, history=history)

    assert expressions(rotated).isdisjoint(expressions(baseline))


def test_scenes_used_within_three_days_are_not_selected_even_with_different_expressions():
    baseline = build_daily_plan(DAY, CONFIG.research, history=[])
    history = [
        replace_groups(
            baseline,
            day=DAY - timedelta(days=2),
            expression_suffix="-different-query",
        )
    ]

    rotated = build_daily_plan(DAY, CONFIG.research, history=history)

    assert {group.scene for group in rotated.core_groups}.isdisjoint(
        {group.scene for group in baseline.core_groups}
    )


def test_recent_produced_topic_terms_are_deprioritized_for_thirty_days():
    baseline = build_daily_plan(DAY, CONFIG.research, history=[])
    produced_term = baseline.core_groups[0].natural_query
    old_plan = baseline.model_copy(
        update={
            "day": DAY - timedelta(days=20),
            "produced_topic_terms": [produced_term],
            "core_groups": [
                group.model_copy(
                    update={
                        "platform_expressions": {
                            platform: [f"historical-{group.id}-{platform.value}"]
                            for platform in group.platform_expressions
                        },
                        "scene": f"historical-{group.scene}",
                    }
                )
                for group in baseline.core_groups
            ],
        }
    )

    rotated = build_daily_plan(DAY, CONFIG.research, history=[old_plan])

    assert produced_term not in {group.natural_query for group in rotated.core_groups}


def test_query_with_two_empty_runs_stays_on_fourteen_day_cooldown():
    baseline = build_daily_plan(DAY, CONFIG.research, history=[])
    history = [
        replace_groups(baseline, day=DAY - timedelta(days=9), result_count=0),
        replace_groups(baseline, day=DAY - timedelta(days=12), result_count=0),
    ]

    rotated = build_daily_plan(DAY, CONFIG.research, history=history)

    assert expressions(rotated).isdisjoint(expressions(baseline))


def test_user_directive_cannot_reintroduce_eldercare():
    plan = build_daily_plan(
        DAY,
        CONFIG.research,
        history=[],
        user_directive="重点增加父母养老与照护压力，并排除职场",
    )

    assert plan.user_directive == "重点增加父母养老与照护压力，并排除职场"
    assert all(group.pillar in set(ContentPillarSlug) for group in plan.core_groups)
    assert all("养老" not in group.natural_query for group in plan.core_groups)
    assert any("ignored excluded topic" in note for note in plan.planning_notes)


def test_expand_plan_records_parent_and_reason_and_caps_at_three():
    plan = build_daily_plan(DAY, CONFIG.research, history=[])
    parent = plan.core_groups[0]

    expanded = expand_plan(
        plan,
        {
            parent.id: ["下班后情绪断电", "已读不回的内耗", "周末也不敢休息", "第四个应被截断"]
        },
    )

    assert len(expanded.expansion_groups) == 3
    assert all(group.is_expansion for group in expanded.expansion_groups)
    assert all(group.parent_query_id == parent.id for group in expanded.expansion_groups)
    assert all(
        group.expansion_reason == "discovered during collection"
        for group in expanded.expansion_groups
    )
    assert {group.natural_query for group in expanded.expansion_groups} == {
        "下班后情绪断电",
        "已读不回的内耗",
        "周末也不敢休息",
    }


def test_expand_plan_ignores_unknown_parent_and_excluded_terms():
    plan = build_daily_plan(DAY, CONFIG.research, history=[])
    expanded = expand_plan(
        plan,
        {
            "unknown": ["有效但无父级"],
            plan.core_groups[0].id: ["父母养老压力"],
        },
    )

    assert expanded.expansion_groups == []
