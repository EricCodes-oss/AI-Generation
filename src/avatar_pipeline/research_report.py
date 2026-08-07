"""Markdown rendering for the user-reviewed daily hotspot research report."""

from __future__ import annotations

from collections import Counter, defaultdict

from avatar_pipeline.models import ContentPillarSlug
from avatar_pipeline.research_models import (
    HotspotReviewCard,
    MetricVisibility,
    ResearchPlatform,
    ResearchReportSummary,
    ResearchRun,
    ResearchSource,
    TimeWindow,
)

_PLATFORM_LABELS = {
    ResearchPlatform.DOUYIN: "抖音",
    ResearchPlatform.WECHAT_CHANNELS: "视频号",
    ResearchPlatform.XIAOHONGSHU: "小红书",
    ResearchPlatform.ZHIHU: "知乎",
    ResearchPlatform.WEIBO: "微博",
    ResearchPlatform.BILIBILI: "B站",
    ResearchPlatform.TOUTIAO: "今日头条",
    ResearchPlatform.JIKE: "即刻",
    ResearchPlatform.WECHAT_OFFICIAL_ACCOUNTS: "公众号",
    ResearchPlatform.YOUTUBE: "YouTube",
    ResearchPlatform.REDDIT: "Reddit",
    ResearchPlatform.MANUAL_IMPORT: "人工导入",
    ResearchPlatform.OTHER: "其他",
}

_WINDOW_LABELS = {
    TimeWindow.LAST_72_HOURS: "最近 72 小时",
    TimeWindow.LAST_7_DAYS: "最近 7 天",
    TimeWindow.LAST_30_DAYS: "最近 30 天",
}

_PILLAR_LABELS = {
    ContentPillarSlug.CAREER_PRESSURE: "职场与现实压力",
    ContentPillarSlug.PARENT_CHILD_COMMUNICATION: "子女教育与家庭沟通",
    ContentPillarSlug.SELF_GROWTH: "自我成长与人生感悟",
}

_NEED_LABELS = {
    "being_seen": "被看见",
    "being_accepted": "被接纳",
    "being_comforted": "被安慰",
    "being_explained": "被解释",
    "being_guided": "被引导",
    "being_accompanied": "被陪伴",
}


def build_report_summary(run: ResearchRun) -> ResearchReportSummary:
    """Build deterministic report counts without comparing platform-scale metrics."""

    sources = run.sources
    limitations = [
        f"{failure.platform.value}/{failure.capability}: {failure.message}"
        for failure in run.failures
    ]
    if run.plan is None:
        limitations.append("daily research plan is missing")
    if not run.insight_cards:
        limitations.append("no A-grade comment insight cards are available")

    return ResearchReportSummary(
        valid_source_count=len(sources),
        a_grade_source_count=sum(source.grade.value == "A" for source in sources),
        insight_card_count=len(run.insight_cards),
        platform_counts=dict(Counter(source.platform for source in sources)),
        pillar_counts=dict(Counter(source.pillar for source in sources)),
        limitations=limitations,
    )


def render_report_markdown(run: ResearchRun) -> str:
    """Render a concise, provenance-rich report that remains inside research scope."""

    summary = build_report_summary(run)
    lines = [
        f"# {run.day.isoformat()} 每日热点内容检索报告",
        "",
        "## 一、采集说明",
        "",
        f"- 有效来源：{summary.valid_source_count} 条",
        f"- A 级来源：{summary.a_grade_source_count} 条",
        f"- 评论洞察卡：{summary.insight_card_count} 张",
        "- 互动数据只在各平台内部作为证据，不直接横向换算或排序。",
    ]
    lines.extend(_render_time_windows(run))
    lines.extend(_render_platform_counts(run))
    lines.extend(["", "## 二、分平台来源", ""])
    lines.extend(_render_sources(run.sources))
    lines.extend(["", "## 三、A 级内容评论洞察", ""])
    lines.extend(_render_insights(run))
    lines.extend(["", "## 四、初步跨平台信号", ""])
    lines.extend(_render_preliminary_signals(run))
    lines.extend(["", "## 五、风险与覆盖缺口", ""])
    lines.extend(_render_gaps(run, summary))
    lines.extend(
        [
            "",
            "## 六、用户决策",
            "",
            "请审阅本报告后明确选择一项：",
            "",
            "1. 批准进入下一环节；",
            "2. 要求修改并说明需要补充的平台、话题或评论；",
            "3. 重做本环节；",
            "4. 退回上一环节；",
            "5. 暂存，稍后继续。",
            "",
            "在收到明确批准前，工作流保持在热点研究环节。",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _render_time_windows(run: ResearchRun) -> list[str]:
    if run.plan is None:
        return ["- 时间窗口：未提供计划。"]
    lines = ["- 时间窗口："]
    for window in TimeWindow:
        share = run.plan.time_window_shares[window]
        lines.append(f"  - {_WINDOW_LABELS[window]}：{share:.0%}")
    return lines


def _render_platform_counts(run: ResearchRun) -> list[str]:
    successes = Counter(source.platform for source in run.sources)
    failures = Counter(failure.platform for failure in run.failures)
    platforms = sorted(set(successes) | set(failures), key=lambda item: item.value)
    lines = ["- 平台覆盖："]
    if not platforms:
        return [*lines, "  - 暂无平台采集结果。"]
    for platform in platforms:
        lines.append(
            f"  - {_PLATFORM_LABELS[platform]}：成功 {successes[platform]} 条，"
            f"失败 {failures[platform]} 项"
        )
    return lines


def _render_sources(sources: list[ResearchSource]) -> list[str]:
    if not sources:
        return ["暂无有效来源。"]
    grouped: dict[ResearchPlatform, list[ResearchSource]] = defaultdict(list)
    for source in sources:
        grouped[source.platform].append(source)

    lines: list[str] = []
    for platform in sorted(grouped, key=lambda item: item.value):
        lines.extend([f"### {_PLATFORM_LABELS[platform]}", ""])
        for source in grouped[platform]:
            lines.extend(
                [
                    f"- **{source.title}**",
                    f"  - 来源 ID：`{source.id}`；等级：{source.grade.value}；"
                    f"可信度：{source.confidence.value}",
                    f"  - 内容支柱：{_PILLAR_LABELS[source.pillar]}；"
                    f"查询组：`{source.query_group_id}`",
                    f"  - 原始产物：`{source.raw_artifact_path}`；"
                    f"采集器：{source.collector}@{source.collector_version}",
                ]
            )
            metric_text = _compact_metrics(source)
            if metric_text:
                lines.append(f"  - 平台内互动证据：{metric_text}")
        lines.append("")
    return lines[:-1]


def _compact_metrics(source: ResearchSource) -> str:
    labels = {
        "views": "播放/阅读",
        "likes": "点赞",
        "comments": "评论",
        "shares": "分享",
        "saves": "收藏",
        "platform_heat": "平台热度",
    }
    values = []
    for field, label in labels.items():
        value = getattr(source.metrics, field)
        if value is not None:
            values.append(f"{label} {value:g}")
    return "、".join(values)


def _render_insights(run: ResearchRun) -> list[str]:
    if not run.insight_cards:
        return ["暂无可审阅的 A 级评论洞察卡。"]
    source_by_id = {source.id: source for source in run.sources}
    lines: list[str] = []
    for card in run.insight_cards:
        source = source_by_id[card.source_id]
        lines.extend(
            [
                f"### {source.title}",
                "",
                f"- 来源 ID：`{card.source_id}`；有效评论：{card.sample_count} 条；"
                f"可信度：{card.confidence.value}",
                f"- 具体场景：{_join_or_none(card.scenes)}",
                f"- 主要情绪：{_join_or_none(card.emotions)}",
                f"- 内心冲突：{_join_or_none(card.inner_conflicts)}",
                f"- 显性问题：{_join_or_none(card.explicit_questions)}",
                "- 隐性需求："
                + _join_or_none([_NEED_LABELS[need.value] for need in card.implicit_needs]),
                f"- 不同意见：{_join_or_none(card.disagreement_signals)}",
                f"- 匿名化表达：{_join_or_none(card.representative_paraphrases)}",
                f"- 评论引用：{', '.join(f'`{ref}`' for ref in card.comment_refs[:5])}"
                + ("（其余引用保留在结构化产物中）" if len(card.comment_refs) > 5 else ""),
                "",
            ]
        )
    return lines[:-1]


def _render_preliminary_signals(run: ResearchRun) -> list[str]:
    if not run.sources:
        return ["暂无足够来源形成初步信号。"]
    pillar_counts = Counter(source.pillar for source in run.sources)
    platform_by_pillar: dict[ContentPillarSlug, set[ResearchPlatform]] = defaultdict(set)
    for source in run.sources:
        platform_by_pillar[source.pillar].add(source.platform)

    lines = ["以下仅为初步信号，不代表正式选题结论："]
    for pillar, count in pillar_counts.most_common():
        platforms = "、".join(
            _PLATFORM_LABELS[platform]
            for platform in sorted(platform_by_pillar[pillar], key=lambda item: item.value)
        )
        lines.append(f"- {_PILLAR_LABELS[pillar]}出现 {count} 条来源，涉及平台：{platforms}。")
    if run.insight_cards:
        needs = Counter(
            _NEED_LABELS[need.value] for card in run.insight_cards for need in card.implicit_needs
        )
        if needs:
            lines.append(
                "- 评论洞察中重复出现的需要："
                + "、".join(f"{need}（{count}）" for need, count in needs.most_common())
                + "。"
            )
    return lines


def _render_gaps(run: ResearchRun, summary: ResearchReportSummary) -> list[str]:
    lines: list[str] = []
    if run.failures:
        for failure in run.failures:
            lines.append(
                f"- **覆盖缺口**：{_PLATFORM_LABELS[failure.platform]} / "
                f"{failure.capability}：{failure.message}"
            )
    if summary.valid_source_count < 30:
        lines.append(
            f"- **数量缺口**：当前 {summary.valid_source_count} 条有效来源，低于每日 30–40 条目标。"
        )
    if summary.insight_card_count < 5:
        lines.append(
            f"- **评论缺口**：当前 {summary.insight_card_count} 张洞察卡，低于每日 5–8 张目标。"
        )
    if not lines:
        lines.append("- 未发现阻断性覆盖缺口；仍需用户审阅来源代表性和洞察质量。")
    return lines


def _join_or_none(values: list[str]) -> str:
    return "；".join(values) if values else "未形成可靠信号"


_HOTSPOT_METRIC_LABELS = {
    "views": "播放量",
    "likes": "点赞",
    "comments": "评论",
    "shares": "分享",
    "saves": "收藏",
}


def render_hotspot_review_markdown(cards: list[HotspotReviewCard]) -> str:
    """Render the first and only manual research confirmation payload."""

    lines = [
        "# Top 3 热点候选",
        "",
        f"- 本轮共有 {len(cards)} 个通过事实与风险门槛的候选。",
        "- 平台热点视频只作为热度证据，不直接使用平台热点视频进入成片。",
        "",
    ]
    if not cards:
        lines.extend(["暂无合格热点，不使用未核验内容补位。", ""])
    for index, card in enumerate(cards, start=1):
        lines.extend(
            [
                f"## 候选 {index}：{card.title}",
                "",
                f"- 候选 ID：`{card.cluster_id}`",
                f"- 事实摘要：{card.fact_summary}",
                f"- 总分：{card.total_score:.2f}",
                f"- 时间窗口：{_WINDOW_LABELS[card.time_window]}",
                f"- 建议讲解角度：{card.speaking_angle}",
                f"- 受众洞察：{card.audience_insight or '暂未形成可靠评论洞察'}",
                "- 风险提示："
                + ("、".join(card.risk_flags) if card.risk_flags else "未发现入池风险"),
                "- 平台证据：",
            ]
        )
        for source in card.platform_evidence:
            lines.append(
                f"  - {_PLATFORM_LABELS[source.platform]}｜{source.title_or_caption}｜"
                f"{source.canonical_url or source.content_id}"
            )
            for field_name, label in _HOTSPOT_METRIC_LABELS.items():
                value = getattr(source.visible_metrics, field_name)
                visibility = source.metric_visibility.get(field_name)
                if (
                    visibility
                    in {
                        MetricVisibility.VISIBLE_EXACT,
                        MetricVisibility.VISIBLE_APPROXIMATE,
                    }
                    and value is not None
                ):
                    display = f"{value:g}"
                else:
                    display = "unknown"
                lines.append(f"    - {label}：{display}")
        lines.append("- 权威核验：")
        for authority in card.authority_evidence:
            lines.append(
                f"  - {authority.publisher}｜{authority.title}｜"
                f"{authority.url_or_reference}｜{authority.summary}"
            )
        lines.extend(
            [
                f"- 核验结论：{card.verification_summary}",
                f"- 成片素材方案：{card.production_media_plan}",
                "",
            ]
        )
    lines.extend(
        [
            "## 用户确认",
            "",
            "请选择一个候选 ID；选择一个热点后才进入脚本生成。",
            "脚本确认之后才进入 TTS、数字主持人、Seedance 2.0、合成与质检。",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"
