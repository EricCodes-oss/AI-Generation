"""Selection and rendering for auditable viral-hotspot candidate reports."""

from collections.abc import Sequence
from datetime import date

from avatar_pipeline.hotspot_models import (
    DirectorAction,
    EvaluatedHotspot,
    HotspotCandidateReport,
    HotspotFailure,
    HotspotRejectedEvent,
    HotspotReport,
    ViralityBand,
)


def _platform_evidence(item: EvaluatedHotspot) -> list[str]:
    evidence = []
    for observation in item.trend.observations:
        for platform, rank in sorted(observation.platform_ranks.items()):
            heat = observation.platform_heat_values.get(platform)
            heat_text = f", heat={heat:g}" if heat is not None else ""
            evidence.append(
                f"{observation.captured_at.isoformat()} {platform} rank={rank}{heat_text}"
            )
    return evidence


def _candidate(
    item: EvaluatedHotspot,
    *,
    strong_score_min: int,
    director_score_min: int,
) -> HotspotCandidateReport:
    assert item.score is not None
    assert item.verification is not None
    assert item.editorial_signals is not None
    editorial = item.editorial_signals
    verification = item.verification
    return HotspotCandidateReport(
        event_id=item.cluster.event_id,
        representative_title=item.cluster.representative_title,
        click_title=editorial.click_title,
        collected_from=item.cluster.first_seen_at,
        collected_to=item.cluster.last_seen_at,
        platform_evidence=_platform_evidence(item),
        trend_label=item.trend.label,
        platform_trend_labels=item.trend.platform_trend_labels,
        related_subtopic_count=item.trend.related_subtopic_count,
        score=item.score,
        score_band=(
            ViralityBand.DIRECTOR_FIRST
            if item.score.total >= director_score_min
            else ViralityBand.STRONG_CANDIDATE
            if item.score.total >= strong_score_min
            else ViralityBand.BACKUP
        ),
        why_click=editorial.why_click,
        opening_hook=editorial.opening_hook,
        audience_relevance=editorial.audience_relevance,
        visual_assets=verification.visual_plan.assets,
        copyright_notes=verification.visual_plan.copyright_notes,
        expected_lifetime=editorial.expected_lifetime,
        risks=[*verification.unresolved_claims, *item.gate.reasons],
        wording_to_avoid=verification.wording_to_avoid,
        director_action=(
            DirectorAction.DO_NOW
            if item.score.total >= director_score_min
            else DirectorAction.WATCH
        ),
        pillar=editorial.pillar,
        source_evidence=verification.sources,
        verification_summary=verification.core_fact,
    )


def build_hotspot_report(
    *,
    day: date,
    rule_version: str,
    snapshot_ids: list[str],
    failures: list[HotspotFailure],
    evaluations: Sequence[EvaluatedHotspot],
    display_score_min: int,
    strong_score_min: int,
    director_score_min: int,
    max_candidates: int,
) -> HotspotReport:
    eligible = [
        item
        for item in evaluations
        if item.gate.passed
        and item.score is not None
        and item.score.total >= display_score_min
        and item.verification is not None
        and item.editorial_signals is not None
    ]
    eligible.sort(key=lambda item: (-item.score.total, item.cluster.event_id))
    candidates = [
        _candidate(item, strong_score_min=strong_score_min, director_score_min=director_score_min)
        for item in eligible[:max_candidates]
    ]
    recommendation = candidates[0].event_id if candidates else None
    candidate_ids = {candidate.event_id for candidate in candidates}
    rejected = [
        HotspotRejectedEvent(
            event_id=item.cluster.event_id,
            representative_title=item.cluster.representative_title,
            reasons=(
                (item.gate.reasons or ["hard_gate_rejected"])
                if not item.gate.passed
                else [f"score_below_{display_score_min}"]
                if item.score is None or item.score.total < display_score_min
                else [f"outside_top_{max_candidates}"]
            ),
        )
        for item in evaluations
        if item.cluster.event_id not in candidate_ids
    ]
    return HotspotReport(
        day=day.isoformat(),
        rule_version=rule_version,
        snapshot_ids=snapshot_ids,
        collection_failures=failures,
        rejected_events=rejected,
        candidates=candidates,
        director_recommendation_event_id=recommendation,
        outcome="qualified_candidates" if candidates else "no_qualified_hotspot",
    )


def render_hotspot_markdown(report: HotspotReport) -> str:
    lines = [f"# {report.day} 跨平台热点候选", "", f"规则版本：{report.rule_version}", ""]
    if report.outcome == "no_qualified_hotspot":
        lines.extend(["## 结果", "", "今日暂无合格爆点，流程安全停止。", ""])
    for index, item in enumerate(report.candidates, start=1):
        badge = (
            "（本轮跨平台综合评分第一）"
            if item.event_id == report.director_recommendation_event_id
            else ""
        )
        lines.extend(
            [
                f"## 候选{index}：{item.click_title}{badge}",
                "",
                f"- 采集区间：{item.collected_from.isoformat()} 至 {item.collected_to.isoformat()}",
                f"- 传播潜力：{item.score.total}/100（{item.score_band.value}）",
                "- 分项："
                f"跨平台{item.score.cross_platform_resonance}/25，"
                f"排名与增速{item.score.trend_velocity}/20，"
                f"冲突悬念{item.score.conflict_suspense}/15，"
                f"普通人利益{item.score.public_interest}/10，"
                f"认知缺口{item.score.curiosity_gap}/10，"
                f"视觉冲击{item.score.visual_impact}/10，"
                f"解释深度{item.score.explanatory_depth}/5，"
                f"事实安全{item.score.fact_safety}/5",
                f"- 趋势：{item.trend_label.value}",
                "- 各平台趋势："
                + "；".join(
                    f"{platform}={label.value}"
                    for platform, label in sorted(item.platform_trend_labels.items())
                ),
                f"- 相关子话题扩散：{item.related_subtopic_count}",
                f"- 点击理由：{item.why_click}",
                f"- 开场钩子：{item.opening_hook}",
                f"- 普通人关联：{item.audience_relevance}",
                f"- 传播寿命：{item.expected_lifetime}",
                f"- 导演建议：{item.director_action.value}",
                f"- 平台证据：{'；'.join(item.platform_evidence)}",
                f"- 视觉素材：{'；'.join(item.visual_assets)}",
                f"- 版权边界：{'；'.join(item.copyright_notes) or '需在生产前确认'}",
                f"- 事实核验：{item.verification_summary}",
                f"- 禁用措辞：{'；'.join(item.wording_to_avoid) or '无新增禁用措辞'}",
                f"- 风险：{'；'.join(item.risks) or '无新增风险'}",
                "",
            ]
        )
    if report.collection_failures:
        lines.extend(["## 采集失败与受限平台", ""])
        lines.extend(
            f"- {item.platform}：{item.reason}（{item.captured_at.isoformat()}）"
            for item in report.collection_failures
        )
    return "\n".join(lines).rstrip() + "\n"
