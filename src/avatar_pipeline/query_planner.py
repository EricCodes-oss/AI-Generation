"""Deterministic daily query planning for the hotspot-research stage."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from hashlib import sha1

from avatar_pipeline.config import ResearchConfig
from avatar_pipeline.models import ContentPillarSlug
from avatar_pipeline.research_models import (
    DailyResearchPlan,
    QueryGroup,
    ResearchPlatform,
    TimeWindow,
)

CORE_PLATFORMS = (
    ResearchPlatform.DOUYIN,
    ResearchPlatform.WECHAT_CHANNELS,
    ResearchPlatform.XIAOHONGSHU,
)
_EXPANSION_REASON = "discovered during collection"
_DEFAULT_EXCLUDED_TERMS = ("父母养老与照护压力", "养老", "照护老人")


@dataclass(frozen=True)
class QueryTemplate:
    """One curated, platform-aware audience situation."""

    key: str
    pillar: ContentPillarSlug
    intent: str
    scene: str
    natural_query: str
    douyin: str
    wechat_channels: str
    xiaohongshu: str

    def platform_expressions(self) -> dict[ResearchPlatform, list[str]]:
        return {
            ResearchPlatform.DOUYIN: [self.douyin],
            ResearchPlatform.WECHAT_CHANNELS: [self.wechat_channels],
            ResearchPlatform.XIAOHONGSHU: [self.xiaohongshu],
        }


_QUERY_PACK: tuple[QueryTemplate, ...] = (
    QueryTemplate(
        "career-after-hours-messages",
        ContentPillarSlug.CAREER_PRESSURE,
        "识别工作边界消失带来的持续疲惫",
        "下班后仍在回复工作消息",
        "下班后还在回复工作消息的人为什么越来越累",
        "下班后还要回工作消息 情绪内耗",
        "成年人的职场疲惫 下班后仍无法休息",
        "下班后领导发消息怎么停止内耗",
    ),
    QueryTemplate(
        "career-invisible-effort",
        ContentPillarSlug.CAREER_PRESSURE,
        "理解努力未被看见时的失落",
        "项目中承担很多却没有被认可",
        "为什么越努力的人越容易觉得自己的付出没人看见",
        "职场付出没人看见 努力没有回报",
        "成年人最委屈的时刻 付出没有被看见",
        "工作做了很多却不被认可怎么办",
    ),
    QueryTemplate(
        "career-meeting-silence",
        ContentPillarSlug.CAREER_PRESSURE,
        "缓解公开表达时的自我怀疑",
        "会议中有想法却不敢开口",
        "开会不敢表达的人真正害怕的是什么",
        "开会不敢说话 职场自我怀疑",
        "职场表达困境 有想法却沉默",
        "开会紧张不敢表达怎么调整",
    ),
    QueryTemplate(
        "career-sunday-anxiety",
        ContentPillarSlug.CAREER_PRESSURE,
        "识别周末结束前的工作焦虑",
        "周日晚上提前为上班焦虑",
        "为什么一到周日晚上就开始害怕上班",
        "周日晚上焦虑 明天上班",
        "成年人周末最后一晚的隐形压力",
        "周日晚上想到上班就焦虑怎么办",
    ),
    QueryTemplate(
        "career-comparison",
        ContentPillarSlug.CAREER_PRESSURE,
        "减少同龄比较造成的失速感",
        "看到同龄人升职后怀疑自己",
        "看到同龄人升职时怎样停止否定自己",
        "同龄人升职 自己很失败",
        "成年人被同龄比较刺痛的瞬间",
        "同事升职后很焦虑怎么停止比较",
    ),
    QueryTemplate(
        "career-redundancy-fear",
        ContentPillarSlug.CAREER_PRESSURE,
        "面对职业不确定性保持行动感",
        "行业变化时担心自己被替代",
        "害怕被时代淘汰的人怎样找回确定感",
        "35岁职场危机 害怕被替代",
        "行业变化中的普通人如何稳住自己",
        "担心失业被替代该怎么提升自己",
    ),
    QueryTemplate(
        "career-over-responsibility",
        ContentPillarSlug.CAREER_PRESSURE,
        "看见过度负责背后的心理负担",
        "团队出问题时总把责任揽到自己身上",
        "总替所有人负责的人为什么活得特别累",
        "职场过度负责 什么都怪自己",
        "成年人别把所有责任都背在身上",
        "工作中总是过度负责怎么建立边界",
    ),
    QueryTemplate(
        "career-commute-exhaustion",
        ContentPillarSlug.CAREER_PRESSURE,
        "理解通勤途中积累的身心损耗",
        "早晚通勤耗尽一天精力",
        "每天通勤很久的人如何留住自己的生活",
        "长时间通勤 精力被掏空",
        "通勤路上的成年人到底有多累",
        "通勤两小时怎么减少疲惫感",
    ),
    QueryTemplate(
        "career-rest-guilt",
        ContentPillarSlug.CAREER_PRESSURE,
        "解除休息时仍感到愧疚的循环",
        "难得休息却觉得自己不够努力",
        "为什么很多成年人一休息就有负罪感",
        "休息有负罪感 不敢停下来",
        "成年人不会休息是一种什么体验",
        "一休息就焦虑觉得浪费时间怎么办",
    ),
    QueryTemplate(
        "family-homework-conflict",
        ContentPillarSlug.PARENT_CHILD_COMMUNICATION,
        "降低陪写作业时的对抗",
        "陪孩子写作业时反复失去耐心",
        "陪孩子写作业为什么最容易伤害亲子关系",
        "陪孩子写作业 忍不住发火",
        "父母的焦虑为什么总在作业桌前爆发",
        "陪写作业总吼孩子怎么沟通",
    ),
    QueryTemplate(
        "family-teen-silence",
        ContentPillarSlug.PARENT_CHILD_COMMUNICATION,
        "理解青春期孩子沉默背后的需要",
        "孩子回家后不愿和父母说话",
        "孩子越来越沉默时父母最不该做什么",
        "青春期孩子不说话 亲子沟通",
        "孩子关上房门后父母如何靠近",
        "孩子回家不愿交流怎么办",
    ),
    QueryTemplate(
        "family-grade-anxiety",
        ContentPillarSlug.PARENT_CHILD_COMMUNICATION,
        "区分成绩焦虑与真实成长需要",
        "考试成绩出来后全家气氛紧张",
        "父母盯着成绩时孩子真正失去的是什么",
        "孩子成绩下降 家长焦虑",
        "一次考试不该定义一个孩子",
        "孩子没考好父母应该怎么说",
    ),
    QueryTemplate(
        "family-phone-conflict",
        ContentPillarSlug.PARENT_CHILD_COMMUNICATION,
        "从手机争夺转向规则协商",
        "因为孩子玩手机反复争吵",
        "抢走孩子手机为什么解决不了沉迷问题",
        "孩子玩手机 亲子冲突",
        "手机背后的亲子关系问题",
        "孩子沉迷手机怎么制定家庭规则",
    ),
    QueryTemplate(
        "family-listening",
        ContentPillarSlug.PARENT_CHILD_COMMUNICATION,
        "帮助父母从说教转向倾听",
        "孩子诉苦时父母立刻讲道理",
        "孩子需要安慰时父母为什么总在讲道理",
        "孩子倾诉 父母别急着说教",
        "亲子沟通里先听见比讲道理更重要",
        "孩子抱怨时父母怎么回应",
    ),
    QueryTemplate(
        "family-comparison",
        ContentPillarSlug.PARENT_CHILD_COMMUNICATION,
        "停止用别人家的孩子制造羞耻",
        "父母无意中拿孩子和同学比较",
        "被父母比较的孩子心里会发生什么",
        "不要拿孩子和别人比较",
        "别人家的孩子正在伤害谁",
        "总忍不住比较孩子怎么办",
    ),
    QueryTemplate(
        "family-parent-apology",
        ContentPillarSlug.PARENT_CHILD_COMMUNICATION,
        "建立父母犯错后修复关系的能力",
        "对孩子发火后不知道怎样道歉",
        "父母向孩子道歉会失去权威吗",
        "对孩子发火后怎么道歉",
        "会修复关系的父母更有力量",
        "父母做错事如何向孩子道歉",
    ),
    QueryTemplate(
        "family-independence",
        ContentPillarSlug.PARENT_CHILD_COMMUNICATION,
        "在保护与放手之间建立信任",
        "孩子想独立做决定而父母不放心",
        "父母真正的放手不是不管而是信任",
        "孩子要独立 父母不放心",
        "养育的终点是允许孩子成为自己",
        "孩子想自己做决定父母怎么沟通",
    ),
    QueryTemplate(
        "family-couple-parenting",
        ContentPillarSlug.PARENT_CHILD_COMMUNICATION,
        "减少夫妻教育分歧对孩子的拉扯",
        "夫妻在孩子面前争论教育方式",
        "教育孩子时父母意见不一致该先解决什么",
        "夫妻教育分歧 当孩子面争吵",
        "家庭教育最怕父母互相拆台",
        "夫妻育儿观念不一致怎么办",
    ),
    QueryTemplate(
        "growth-self-criticism",
        ContentPillarSlug.SELF_GROWTH,
        "松动习惯性自我否定",
        "一件小事没做好就全面否定自己",
        "总是否定自己的人怎样重新看见价值",
        "停止自我否定 接纳不完美",
        "成年人要学会对自己温柔一点",
        "总觉得自己不够好怎么改变",
    ),
    QueryTemplate(
        "growth-people-pleasing",
        ContentPillarSlug.SELF_GROWTH,
        "理解讨好背后的关系恐惧",
        "明明不愿意却不敢拒绝别人",
        "不敢拒绝别人的人到底在害怕什么",
        "不会拒绝 讨好型人格内耗",
        "成年人学会拒绝不是自私",
        "不敢拒绝别人怎么建立边界",
    ),
    QueryTemplate(
        "growth-midlife-reset",
        ContentPillarSlug.SELF_GROWTH,
        "帮助中年人接纳重新开始",
        "到了中年想换一种生活却不敢行动",
        "人到中年还有没有重新开始的勇气",
        "中年重新开始 人生选择",
        "四十岁以后也可以重新安排人生",
        "中年迷茫想改变从哪里开始",
    ),
    QueryTemplate(
        "growth-friendship-distance",
        ContentPillarSlug.SELF_GROWTH,
        "接受成年关系自然变化",
        "曾经亲近的朋友慢慢失去联系",
        "成年人的朋友走散了要不要追回来",
        "朋友渐行渐远 成年人的友情",
        "有些关系淡了不是谁的错",
        "朋友疏远后很难过怎么释怀",
    ),
    QueryTemplate(
        "growth-slow-progress",
        ContentPillarSlug.SELF_GROWTH,
        "在进步缓慢时维持耐心",
        "努力很久仍看不到明显改变",
        "成长很慢的时候怎样相信自己没有白走",
        "努力没有结果 坚持还是放弃",
        "人生不是每一段努力都立刻有回音",
        "长期努力看不到进步怎么办",
    ),
    QueryTemplate(
        "growth-emotional-boundary",
        ContentPillarSlug.SELF_GROWTH,
        "区分共情与替别人承担情绪",
        "身边人不开心时立刻责怪自己",
        "为什么你总在为别人的情绪负责",
        "为别人情绪负责 情绪边界",
        "别把所有人的不开心都算在自己身上",
        "总被别人的情绪影响怎么办",
    ),
    QueryTemplate(
        "growth-solitude",
        ContentPillarSlug.SELF_GROWTH,
        "把独处转化为稳定自己的空间",
        "热闹结束后独自面对空落感",
        "一个人生活时怎样不把独处变成孤独",
        "学会独处 内心稳定",
        "成年人的独处是重新认识自己",
        "一个人时总觉得空虚怎么办",
    ),
    QueryTemplate(
        "growth-past-regret",
        ContentPillarSlug.SELF_GROWTH,
        "减少对过去选择的反复惩罚",
        "夜深时反复后悔过去的决定",
        "总为过去后悔的人怎样放过自己",
        "后悔过去的选择 放过自己",
        "人生没有一条路能提前证明正确",
        "反复后悔以前的决定怎么办",
    ),
    QueryTemplate(
        "growth-age-anxiety",
        ContentPillarSlug.SELF_GROWTH,
        "缓解年龄节点带来的时间焦虑",
        "生日或新年时担心自己来不及了",
        "觉得人生来不及的人真正需要放下什么",
        "年龄焦虑 人生来不及",
        "人生没有统一的进度表",
        "年龄越来越大很焦虑怎么办",
    ),
)


def _contains_excluded(text: str, excluded_terms: Iterable[str]) -> bool:
    normalized = text.casefold()
    return any(term.strip().casefold() in normalized for term in excluded_terms if term.strip())


def _template_text(template: QueryTemplate) -> str:
    return " ".join(
        (
            template.intent,
            template.scene,
            template.natural_query,
            template.douyin,
            template.wechat_channels,
            template.xiaohongshu,
        )
    )


def _recent_history(
    day: date, history: Sequence[DailyResearchPlan], maximum_age_days: int
) -> list[DailyResearchPlan]:
    return sorted(
        (
            plan
            for plan in history
            if 0 < (day - plan.day).days <= maximum_age_days
        ),
        key=lambda plan: plan.day,
        reverse=True,
    )


def _all_expressions(group: QueryGroup) -> set[str]:
    return {
        expression
        for expressions in group.platform_expressions.values()
        for expression in expressions
    }


def _empty_result_cooldown_queries(
    day: date, history: Sequence[DailyResearchPlan], config: ResearchConfig
) -> set[str]:
    recent = _recent_history(day, history, config.query.empty_result_cooldown_days)
    observations: dict[str, list[int | None]] = {}
    for plan in recent:
        for group in plan.core_groups:
            observations.setdefault(group.natural_query, []).append(group.result_count)

    threshold = config.query.empty_result_threshold
    return {
        query
        for query, results in observations.items()
        if len(results) >= threshold and all(result == 0 for result in results[:threshold])
    }


def _rotated_templates(day: date, pillar: ContentPillarSlug) -> list[QueryTemplate]:
    candidates = [template for template in _QUERY_PACK if template.pillar is pillar]
    offset = day.toordinal() % len(candidates)
    return [*candidates[offset:], *candidates[:offset]]


def _choose_templates(
    day: date,
    pillar: ContentPillarSlug,
    config: ResearchConfig,
    history: Sequence[DailyResearchPlan],
    planning_notes: list[str],
) -> list[QueryTemplate]:
    excluded = tuple(dict.fromkeys([*config.excluded_topics, *_DEFAULT_EXCLUDED_TERMS]))
    exact_history = _recent_history(day, history, config.query.exact_query_cooldown_days)
    scene_history = _recent_history(day, history, config.query.scene_cooldown_days)
    topic_history = _recent_history(day, history, config.query.history_days)

    used_expressions = {
        expression
        for plan in exact_history
        for group in plan.core_groups
        for expression in _all_expressions(group)
    }
    used_scenes = {group.scene for plan in scene_history for group in plan.core_groups}
    produced_terms = {term for plan in topic_history for term in plan.produced_topic_terms}
    empty_cooldown = _empty_result_cooldown_queries(day, history, config)

    candidates = [
        template
        for template in _rotated_templates(day, pillar)
        if not _contains_excluded(_template_text(template), excluded)
        and not (
            {
                expression
                for expressions in template.platform_expressions().values()
                for expression in expressions
            }
            & used_expressions
        )
        and template.scene not in used_scenes
        and template.natural_query not in empty_cooldown
    ]

    preferred = [
        template for template in candidates if template.natural_query not in produced_terms
    ]
    if len(preferred) < config.query.groups_per_pillar:
        planning_notes.append(
            "relaxed produced-topic deprioritization for pillar "
            f"{pillar.value} due to candidate supply"
        )
        preferred.extend(
            template for template in candidates if template.natural_query in produced_terms
        )

    selected = preferred[: config.query.groups_per_pillar]
    if len(selected) != config.query.groups_per_pillar:
        raise ValueError(
            f"not enough eligible query templates for {pillar.value}; "
            "review cooldowns or expand the curated query pack"
        )
    return selected


def _time_window_for(index: int) -> TimeWindow:
    windows = (
        TimeWindow.LAST_72_HOURS,
        TimeWindow.LAST_72_HOURS,
        TimeWindow.LAST_7_DAYS,
        TimeWindow.LAST_72_HOURS,
        TimeWindow.LAST_7_DAYS,
        TimeWindow.LAST_30_DAYS,
        TimeWindow.LAST_72_HOURS,
        TimeWindow.LAST_7_DAYS,
        TimeWindow.LAST_72_HOURS,
    )
    return windows[index % len(windows)]


def build_daily_plan(
    day: date,
    config: ResearchConfig,
    history: Sequence[DailyResearchPlan],
    user_directive: str | None = None,
) -> DailyResearchPlan:
    """Build nine deterministic, history-aware core query groups."""

    planning_notes: list[str] = []
    if user_directive and _contains_excluded(
        user_directive, [*config.excluded_topics, *_DEFAULT_EXCLUDED_TERMS]
    ):
        planning_notes.append("ignored excluded topic in user directive")

    templates: list[QueryTemplate] = []
    for pillar in ContentPillarSlug:
        templates.extend(_choose_templates(day, pillar, config, history, planning_notes))

    groups = [
        QueryGroup(
            id=f"core-{index + 1:02d}-{template.key}",
            pillar=template.pillar,
            intent=template.intent,
            scene=template.scene,
            natural_query=template.natural_query,
            platform_expressions=template.platform_expressions(),
            time_window=_time_window_for(index),
            history_notes=[],
        )
        for index, template in enumerate(templates)
    ]

    return DailyResearchPlan(
        day=day,
        core_groups=groups,
        time_window_shares={
            TimeWindow.LAST_72_HOURS: config.time_window_shares.last_72_hours,
            TimeWindow.LAST_7_DAYS: config.time_window_shares.last_7_days,
            TimeWindow.LAST_30_DAYS: config.time_window_shares.last_30_days,
        },
        user_directive=user_directive,
        planning_notes=planning_notes,
        created_at=datetime(day.year, day.month, day.day, tzinfo=UTC),
    )


def _expansion_id(parent_id: str, term: str) -> str:
    digest = sha1(f"{parent_id}\0{term}".encode()).hexdigest()[:10]
    return f"exp-{digest}"


def expand_plan(
    plan: DailyResearchPlan, discovered_terms: Mapping[str, Sequence[str]]
) -> DailyResearchPlan:
    """Append at most three valid expansion groups, preserving parent provenance."""

    parent_by_id = {group.id: group for group in plan.core_groups}
    excluded_terms = {
        term
        for group in plan.core_groups
        for term in [*group.exclusions, *_DEFAULT_EXCLUDED_TERMS]
        if term.strip()
    }
    expansions = list(plan.expansion_groups)
    existing_terms = {group.natural_query for group in expansions}

    for parent_id, terms in discovered_terms.items():
        parent = parent_by_id.get(parent_id)
        if parent is None:
            continue
        for raw_term in terms:
            term = raw_term.strip()
            if (
                not term
                or term in existing_terms
                or _contains_excluded(term, excluded_terms)
            ):
                continue
            if len(expansions) >= 3:
                break
            expansions.append(
                QueryGroup(
                    id=_expansion_id(parent_id, term),
                    pillar=parent.pillar,
                    intent=f"扩展检索：{term}",
                    scene=parent.scene,
                    natural_query=term,
                    platform_expressions={platform: [term] for platform in CORE_PLATFORMS},
                    time_window=parent.time_window,
                    is_expansion=True,
                    parent_query_id=parent.id,
                    expansion_reason=_EXPANSION_REASON,
                )
            )
            existing_terms.add(term)
        if len(expansions) >= 3:
            break

    return plan.model_copy(update={"expansion_groups": expansions})
