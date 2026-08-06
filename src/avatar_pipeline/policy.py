"""Deterministic admission rules for safe, verified hotspot candidates."""

from collections.abc import Sequence
from dataclasses import dataclass

from avatar_pipeline.models import FactStatus, TopicCandidate


@dataclass(frozen=True)
class AdmissionDecision:
    status: FactStatus
    publishable: bool
    reasons: list[str]


def evaluate_candidate(candidate: TopicCandidate) -> AdmissionDecision:
    reasons: list[str] = []
    if candidate.fact_status is not FactStatus.VERIFIED:
        reasons.append(f"fact_status:{candidate.fact_status.value}")
    if candidate.risk_flags:
        reasons.extend(f"risk:{flag}" for flag in candidate.risk_flags)
    if candidate.fact_status is FactStatus.VERIFIED and len(candidate.source_evidence) < 2:
        reasons.append("insufficient_independent_evidence")
    if candidate.fact_status is FactStatus.VERIFIED and not candidate.verification_summary:
        reasons.append("missing_verification_summary")
    publishable = not reasons and candidate.fact_status is FactStatus.VERIFIED
    return AdmissionDecision(candidate.fact_status, publishable, reasons)


def screen_candidates(
    candidates: Sequence[TopicCandidate],
) -> tuple[list[TopicCandidate], list[TopicCandidate]]:
    accepted: list[TopicCandidate] = []
    skipped: list[TopicCandidate] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = candidate.dedupe_key or candidate.id
        if key in seen:
            skipped.append(
                candidate.model_copy(
                    update={
                        "publishable": False,
                        "risk_flags": [*candidate.risk_flags, "duplicate_candidate"],
                    }
                )
            )
            continue
        seen.add(key)
        decision = evaluate_candidate(candidate)
        if decision.publishable:
            accepted.append(candidate.model_copy(update={"publishable": True}))
        else:
            skipped.append(
                candidate.model_copy(
                    update={
                        "publishable": False,
                        "risk_flags": [*candidate.risk_flags, *decision.reasons],
                    }
                )
            )
    return accepted, skipped


def rank_verified_candidates(
    candidates: Sequence[TopicCandidate], limit: int = 3
) -> list[TopicCandidate]:
    accepted, _ = screen_candidates(candidates)
    return sorted(accepted, key=lambda item: item.score, reverse=True)[:limit]
