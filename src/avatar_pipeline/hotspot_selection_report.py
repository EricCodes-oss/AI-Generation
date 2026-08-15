"""Human-readable reports for the cross-domain hotspot selection gate."""

from __future__ import annotations

from avatar_pipeline.hotspot_selection import HotspotCandidatePool

_CATEGORY_LABELS = {
    "social_livelihood": "社会民生",
    "technology": "科技",
    "finance": "财经",
    "international": "国际",
    "policy": "政策",
    "consumer": "消费",
    "education": "教育",
    "influencer": "网红热点",
    "ordinary_people": "普通人热议",
    "ordinary_life_moment": "普通人自然瞬间",
    "culture_entertainment": "文娱文化",
    "weather_disaster": "天气灾害",
}

_RECORDING_ORIGIN_LABELS = {
    "family_phone": "家庭手机随手拍",
    "passerby_phone": "路人手机偶遇",
    "dashcam": "行车记录仪",
    "cctv": "公共场所监控",
    "shop_camera": "店铺监控",
    "public_scene": "日常公共现场",
    "other_natural_recording": "其他自然记录",
}


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")


def _list_cell(values: list[str], *, empty: str = "—") -> str:
    return _cell("；".join(values)) if values else empty


def render_candidate_pool_markdown(pool: HotspotCandidatePool) -> str:
    """Render a review-first candidate report without implying topic approval."""

    lines = [
        f"# {pool.day.isoformat()} 跨领域热点候选池",
        "",
        "**当前状态：等待用户共同评估**",
        "",
        (
            "**未确认前禁止进入 V5 生产。** 用户确认候选编号后，才保存选题批准记录；"
            "此后事实核验、稿件、TTS、数字人、素材、剪辑和 QC 按 V5 流程自动推进。"
        ),
        "",
        f"- 候选数量：{len(pool.candidates)}",
        f"- 覆盖领域：{len(pool.covered_categories)}",
        f"- 生成时间：{pool.generated_at.isoformat()}",
        f"- 规则：{pool.selection_rule}",
        "",
        "## 候选总览",
        "",
        "| 排名 | 候选编号 | 类型 | 话题 | 最新进展 | 热度依据 | 观看动机 | 导演评级 |",
        "|---:|---|---|---|---|---|---|:---:|",
    ]
    for rank, candidate in enumerate(pool.candidates, start=1):
        lines.append(
            "| "
            + " | ".join(
                [
                    str(rank),
                    _cell(candidate.candidate_id),
                    _CATEGORY_LABELS[candidate.category.value],
                    _cell(candidate.title),
                    _cell(candidate.latest_development),
                    _list_cell(candidate.heat_basis),
                    _cell(candidate.why_watch),
                    candidate.director_rating.value,
                ]
            )
            + " |"
        )

    lines.extend(["", "## 逐项导演评估", ""])
    for rank, candidate in enumerate(pool.candidates, start=1):
        sources = [
            f"{source.title}（{source.platform}；{source.evidence_type}；{source.url_or_reference}）"
            for source in candidate.authoritative_sources
        ]
        lines.extend(
            [
                f"### {rank}. {candidate.title}（{candidate.candidate_id}）",
                "",
                f"- **类型：** {_CATEGORY_LABELS[candidate.category.value]}",
                f"- **最新进展：** {candidate.latest_development}",
                f"- **热度依据：** {_list_cell(candidate.heat_basis)}",
                f"- **观看动机：** {candidate.why_watch}",
                f"- **建议标题：** {candidate.suggested_title}",
                f"- **权威来源：** {_list_cell(sources)}",
                f"- **画面条件：** {_list_cell(candidate.visual_material_plan)}",
                f"- **推荐素材来源：** {_list_cell(candidate.preferred_media_sources)}",
                f"- **风险：** {_list_cell(candidate.risks)}",
                f"- **导演评级：** {candidate.director_rating.value}",
            ]
        )
        assessment = candidate.ordinary_moment_assessment
        if assessment is not None:
            lines.extend(
                [
                    "- **普通人自然瞬间核验：** 通过",
                    f"  - 记录方式：{_RECORDING_ORIGIN_LABELS[assessment.recording_origin.value]}",
                    "  - 账号属性：非职业博主/网红；普通人个人生活记录账号",
                    "  - 画面主体：普通人是画面主体，不是博主表演或栏目主角",
                    "  - 场景属性：真实日常生活场景，不是为内容生产搭建的场景",
                    "  - 事件关系：事件先于拍摄自然发生，非拍摄者主动策划",
                    f"  - 自然反应证据：{_list_cell(assessment.natural_reaction_evidence)}",
                    f"  - 自然真情/善意证据：{_list_cell(assessment.human_warmth_evidence)}",
                    (
                        "  - 原始记录者可追溯："
                        f"{'是' if assessment.original_recorder_available else '否'}"
                    ),
                    f"  - 连续现场画面：{'是' if assessment.continuous_scene_available else '否'}",
                    f"  - 现场声：{'有' if assessment.ambient_audio_available else '无/待核'}",
                    f"  - 摆拍风险：{assessment.staging_risk:.2f}",
                ]
            )
        lines.append("")

    lines.extend(
        [
            "## 素材准入说明",
            "",
            (
                "新华网、新华社、人民日报及其 B 站官方账号、中国青年报及其 B 站官方账号，"
                "均可作为热点信号、事实来源或素材候选；使用前仍须核验账号真实性、"
                "对应事实原文、画面相关性、水印/烧录文字、来源 URL、下载时间、文件哈希"
                "及版权或使用依据。无水印不等于已获版权授权。"
            ),
            "",
        ]
    )
    return "\n".join(lines)
