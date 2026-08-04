"""Deterministic validation and structuring for audience comment insights."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from avatar_pipeline.models import utc_now
from avatar_pipeline.research_models import (
    CommentInsightCard,
    CommentSampleType,
    ConfidenceLevel,
    ImplicitNeed,
)

ShortText = Annotated[str, Field(min_length=1, max_length=80)]
InsightText = Annotated[str, Field(min_length=1, max_length=160)]

_RISK_TERMS = {
    "self_harm": ("不想活", "自杀", "轻生", "结束生命", "伤害自己"),
    "domestic_violence": ("家暴", "动手打", "殴打", "被打", "暴力控制"),
    "illegality": ("违法", "犯法", "非法渠道", "买凶", "报复"),
}


class InsightModel(BaseModel):
    """Strict base model for curated comment-analysis inputs and outputs."""

    model_config = ConfigDict(extra="forbid")


class CommentSample(InsightModel):
    """One already-labeled, source-local comment sample."""

    ref: str = Field(min_length=1, max_length=160)
    sample_type: CommentSampleType
    text: str = Field(max_length=500)
    is_valid: bool = True


class CommentInsightInput(InsightModel):
    """Human- or Skill-produced insight fields accepted by the validator."""

    role_or_life_stage_clues: list[InsightText] = Field(default_factory=list)
    scenes: list[InsightText] = Field(default_factory=list)
    emotions: list[ShortText] = Field(default_factory=list)
    inner_conflicts: list[InsightText] = Field(default_factory=list)
    explicit_questions: list[InsightText] = Field(default_factory=list)
    implicit_needs: list[ImplicitNeed] = Field(default_factory=list)
    failed_attempts: list[InsightText] = Field(default_factory=list)
    disliked_expressions: list[ShortText] = Field(default_factory=list)
    disagreement_signals: list[InsightText] = Field(default_factory=list)
    representative_paraphrases: list[ShortText] = Field(default_factory=list, max_length=8)
    privacy_notes: list[InsightText] = Field(default_factory=list)


class InsightBuildResult(InsightModel):
    """Validated card plus review warnings and safety signals."""

    card: CommentInsightCard
    warnings: list[str] = Field(default_factory=list)
    rejected_comment_count: int = Field(ge=0)
    risk_flags: list[str] = Field(default_factory=list)


def build_insight_card(
    source_id: str,
    samples: list[CommentSample],
    insight: CommentInsightInput,
    *,
    focused_deep_dive: bool = False,
    created_at: datetime | None = None,
) -> InsightBuildResult:
    """Validate samples and build one traceable comment-insight card."""

    accepted, rejected_count = _filter_samples(samples)
    sample_count = len(accepted)
    if focused_deep_dive and sample_count > 60:
        raise ValueError("focused deep dive cannot exceed 60 effective comments")
    if not focused_deep_dive and sample_count > 40:
        raise ValueError("standard comment sample cannot exceed 40 effective comments")
    if sample_count == 0:
        raise ValueError("at least one effective comment sample is required")

    counts = Counter(sample.sample_type for sample in accepted)
    warnings = _sample_warnings(counts, sample_count, focused_deep_dive)
    if not insight.disagreement_signals:
        warnings.append("no counter-opinion signal recorded")

    risk_flags = _detect_risks(accepted)
    if risk_flags:
        warnings.append(
            "high-risk comment signal requires human safety review before downstream use"
        )

    card = CommentInsightCard(
        source_id=source_id,
        sample_count=sample_count,
        sample_type_counts=dict(counts),
        role_or_life_stage_clues=insight.role_or_life_stage_clues,
        scenes=insight.scenes,
        emotions=insight.emotions,
        inner_conflicts=insight.inner_conflicts,
        explicit_questions=insight.explicit_questions,
        implicit_needs=insight.implicit_needs,
        failed_attempts=insight.failed_attempts,
        disliked_expressions=insight.disliked_expressions,
        disagreement_signals=insight.disagreement_signals,
        representative_paraphrases=insight.representative_paraphrases,
        comment_refs=[sample.ref for sample in accepted],
        privacy_notes=insight.privacy_notes,
        confidence=ConfidenceLevel.LOW,
        created_at=created_at or utc_now(),
    )
    card = card.model_copy(update={"confidence": classify_confidence(card)})
    return InsightBuildResult(
        card=card,
        warnings=warnings,
        rejected_comment_count=rejected_count,
        risk_flags=risk_flags,
    )


def classify_confidence(card: CommentInsightCard) -> ConfidenceLevel:
    """Classify confidence from sample size, diversity, and structured evidence."""

    present_types = sum(
        1 for sample_type in CommentSampleType if card.sample_type_counts.get(sample_type, 0) > 0
    )
    evidence_dimensions = sum(
        bool(values)
        for values in (
            card.scenes,
            card.emotions,
            card.inner_conflicts,
            card.explicit_questions,
            card.implicit_needs,
            card.failed_attempts,
        )
    )
    has_counter_opinion = bool(card.disagreement_signals)

    if (
        card.sample_count >= 20
        and present_types == len(CommentSampleType)
        and evidence_dimensions >= 5
        and has_counter_opinion
    ):
        return ConfidenceLevel.HIGH
    if (
        card.sample_count >= 15
        and present_types >= 4
        and evidence_dimensions >= 4
        and has_counter_opinion
    ):
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


def _filter_samples(samples: list[CommentSample]) -> tuple[list[CommentSample], int]:
    accepted: list[CommentSample] = []
    seen_refs: set[str] = set()
    rejected_count = 0
    for sample in samples:
        ref = sample.ref.strip()
        text = sample.text.strip()
        if not sample.is_valid or not ref or not text or ref in seen_refs:
            rejected_count += 1
            continue
        accepted.append(sample.model_copy(update={"ref": ref, "text": text}))
        seen_refs.add(ref)
    return accepted, rejected_count


def _sample_warnings(
    counts: Counter[CommentSampleType], sample_count: int, focused_deep_dive: bool
) -> list[str]:
    warnings: list[str] = []
    if sample_count < 20:
        warnings.append(f"sample count {sample_count} is below target 20")
    elif sample_count > 40 and focused_deep_dive:
        warnings.append("focused deep dive sample exceeds standard target 40")

    missing = [sample_type.value for sample_type in CommentSampleType if not counts[sample_type]]
    if missing:
        warnings.append(f"missing comment sample types: {', '.join(missing)}")
    return warnings


def _detect_risks(samples: list[CommentSample]) -> list[str]:
    combined = "\n".join(sample.text.casefold() for sample in samples)
    return [
        risk
        for risk, terms in _RISK_TERMS.items()
        if any(term.casefold() in combined for term in terms)
    ]
