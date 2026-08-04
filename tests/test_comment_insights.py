from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from avatar_pipeline.comment_insights import (
    CommentInsightInput,
    CommentSample,
    InsightBuildResult,
    build_insight_card,
    classify_confidence,
)
from avatar_pipeline.research_models import CommentSampleType, ConfidenceLevel, ImplicitNeed

NOW = datetime(2026, 8, 4, 1, 0, tzinfo=UTC)


def samples(count=20, *, include_all_types=True):
    types = list(CommentSampleType) if include_all_types else [CommentSampleType.HIGH_LIKE]
    return [
        CommentSample(
            ref=f"comment-{index}",
            sample_type=types[index % len(types)],
            text=f"匿名化评论 {index}",
        )
        for index in range(count)
    ]


def insight(**updates):
    data = {
        "role_or_life_stage_clues": ["可能同时承担工作与家庭责任"],
        "scenes": ["下班后仍在回复工作消息"],
        "emotions": ["疲惫"],
        "inner_conflicts": ["想休息又怕落后"],
        "explicit_questions": ["怎样停止内耗"],
        "implicit_needs": [ImplicitNeed.BEING_SEEN],
        "failed_attempts": ["强迫自己不去想"],
        "disliked_expressions": ["你就是想太多"],
        "disagreement_signals": ["少数人认为应先调整工作方式"],
        "representative_paraphrases": ["停下来时反而更不安"],
        "privacy_notes": ["仅保留匿名评论引用"],
    }
    data.update(updates)
    return CommentInsightInput(**data)


def test_removes_blank_duplicate_and_invalid_comments_and_counts_five_types():
    raw = samples(20) + [
        CommentSample(ref="blank", sample_type=CommentSampleType.LATEST, text="   "),
        CommentSample(ref="comment-0", sample_type=CommentSampleType.HIGH_LIKE, text="重复"),
        CommentSample(
            ref="spam", sample_type=CommentSampleType.LATEST, text="加微信领资料", is_valid=False
        ),
    ]

    result = build_insight_card("source-1", raw, insight(), created_at=NOW)

    assert isinstance(result, InsightBuildResult)
    assert result.card.sample_count == 20
    assert set(result.card.sample_type_counts) == set(CommentSampleType)
    assert result.rejected_comment_count == 3
    assert result.card.comment_refs == [f"comment-{index}" for index in range(20)]


def test_warns_outside_twenty_to_forty_and_allows_marked_deep_dive_up_to_sixty():
    sparse = build_insight_card("source-1", samples(12), insight(), created_at=NOW)
    assert "sample count 12 is below target 20" in sparse.warnings

    deep = build_insight_card(
        "source-1", samples(60), insight(), focused_deep_dive=True, created_at=NOW
    )
    assert deep.card.sample_count == 60
    assert "focused deep dive sample exceeds standard target 40" in deep.warnings

    with pytest.raises(ValueError, match="cannot exceed 60"):
        build_insight_card(
            "source-1", samples(61), insight(), focused_deep_dive=True, created_at=NOW
        )


def test_requires_counter_opinion_and_warns_when_any_sample_type_is_missing():
    result = build_insight_card(
        "source-1",
        samples(20, include_all_types=False),
        insight(disagreement_signals=[]),
        created_at=NOW,
    )

    assert "missing comment sample types" in " ".join(result.warnings)
    assert "no counter-opinion signal recorded" in result.warnings
    assert result.card.confidence is ConfidenceLevel.LOW


def test_confidence_thresholds_use_sample_diversity_and_evidence():
    high = build_insight_card("source-1", samples(25), insight(), created_at=NOW)
    medium = build_insight_card("source-1", samples(18), insight(), created_at=NOW)
    low = build_insight_card(
        "source-1",
        samples(8, include_all_types=False),
        insight(disagreement_signals=[]),
        created_at=NOW,
    )

    assert classify_confidence(high.card) is ConfidenceLevel.HIGH
    assert classify_confidence(medium.card) is ConfidenceLevel.MEDIUM
    assert classify_confidence(low.card) is ConfidenceLevel.LOW


def test_rejects_identity_diagnosis_fields_and_long_copied_comment_text():
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        CommentInsightInput.model_validate({**insight().model_dump(), "exact_age": 42})

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        CommentInsightInput.model_validate({**insight().model_dump(), "diagnosis": "抑郁症"})

    with pytest.raises(ValidationError, match="at most 80 characters"):
        insight(representative_paraphrases=["这是一段过长的原评论" * 20])


def test_flags_high_risk_signals_without_diagnosing_the_audience():
    risk_samples = samples(20)
    risk_samples[0] = risk_samples[0].model_copy(update={"text": "有时真的不想活了"})
    risk_samples[1] = risk_samples[1].model_copy(update={"text": "伴侣动手打人"})
    risk_samples[2] = risk_samples[2].model_copy(update={"text": "想找违法渠道报复"})

    result = build_insight_card("source-1", risk_samples, insight(), created_at=NOW)

    assert set(result.risk_flags) == {"self_harm", "domestic_violence", "illegality"}
    assert any("requires human safety review" in warning for warning in result.warnings)
