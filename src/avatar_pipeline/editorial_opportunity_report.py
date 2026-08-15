"""Markdown renderer for editorial-opportunity v2 director topic cards."""

from __future__ import annotations

from avatar_pipeline.news_intelligence_models import (
    EditorialOpportunityPool,
    PoolQualityStatus,
)


def _items(values: list[str], *, empty: str = "—") -> str:
    return "；".join(values) if values else empty


def render_editorial_opportunity_report(pool: EditorialOpportunityPool) -> str:
    status = (
        "存在 S 级选题，可与用户共同评估后确认制作"
        if pool.quality_status is PoolQualityStatus.HAS_S_TIER
        else "暂无 S 级选题；不强行补齐弱候选"
    )
    lines = [
        f"# {pool.day.isoformat()} 双漏斗新闻选题报告",
        "",
        f"**当前判断：{status}**",
        "",
        "**选题确认前禁止进入视频生产。确认后按 V5 流程自动推进，不逐步重复询问。**",
        "",
        f"- 规则版本：{pool.rule_version}",
        f"- 内部评审：{pool.reviewed_count} 条",
        f"- 合格候选：{len(pool.candidates)} 条",
        f"- 生成时间：{pool.generated_at.isoformat()}",
        "",
    ]
    if not pool.candidates:
        lines.extend(["本轮没有达到 A 级或 S 级且通过硬性核验的题目。", ""])
    for rank, candidate in enumerate(pool.candidates, start=1):
        lines.extend(
            [
                f"## {rank}. {candidate.candidate_title}",
                "",
                f"- **导演评级：** {candidate.grade.value}（{candidate.score:g}/100）",
                f"- **类型：** {candidate.category}",
                f"- **事件最新进展：** {candidate.latest_development}",
                f"- **为什么是今天：** {candidate.why_today}",
                f"- **跨平台热度证据：** {_items(candidate.heat_evidence)}",
                f"- **最强反差或悬念：** {candidate.strongest_tension}",
                f"- **普通人为什么关心：** {candidate.ordinary_people_relevance}",
                f"- **观众看完能得到什么：** {candidate.viewer_payoff}",
                f"- **建议的前三秒开场：** {candidate.three_second_hook}",
                f"- **可靠事实来源：** {_items(candidate.reliable_fact_sources)}",
                f"- **可用插播素材：** {_items(candidate.footage_candidates)}",
                f"- **素材清晰度与年代风险：** {_items(candidate.footage_risks)}",
                f"- **预计热度寿命：** {candidate.expected_heat_lifetime}",
                f"- **不推荐制作的理由：** {_items(candidate.do_not_produce_reasons)}",
                "",
            ]
        )
        if candidate.score_breakdown is not None:
            score = candidate.score_breakdown
            lines.extend(
                [
                    "### 评分拆解",
                    "",
                    f"- 真实热度：{score.real_heat.score:g}/30",
                    f"- 内容吸引力：{score.content_attractiveness.score:g}/35",
                    f"- 事实可靠性：{score.fact_reliability.score:g}/20",
                    f"- 视频潜力：{score.video_potential.score:g}/15",
                    "",
                ]
            )
    if pool.rejected_reasons:
        lines.extend(["## 内部淘汰与观察记录", ""])
        for opportunity_id, reasons in sorted(pool.rejected_reasons.items()):
            lines.append(f"- `{opportunity_id}`：{_items(reasons)}")
        lines.append("")
    lines.extend(
        [
            "## 证据边界",
            "",
            "平台热度只用于证明注意力变化，不能替代事实核验。核心口播断言必须由第一方、官方或独立可靠来源支持。素材可下载、无水印或带水印，均不自动等于获得转载授权。",
            "",
        ]
    )
    return "\n".join(lines)
