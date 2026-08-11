"""Fact, source, recency, visual, and safety verification for a clustered event."""

from datetime import datetime
from urllib.parse import urlparse

from avatar_pipeline.hotspot_models import (
    CandidateVerification,
    EventCluster,
    VerificationDecision,
)

_RELIABLE_TYPES = {"primary", "official", "reputable_media"}


def _source_origin(url_or_reference: str, platform: str) -> str:
    hostname = urlparse(url_or_reference).hostname
    return (hostname or platform).casefold()


def verify_candidate(
    cluster: EventCluster,
    evidence: CandidateVerification,
    *,
    as_of: datetime,
    max_age_hours: int,
) -> VerificationDecision:
    if evidence.event_id != cluster.event_id:
        raise ValueError("verification event_id must match cluster event_id")
    if as_of.tzinfo is None or evidence.occurred_at.tzinfo is None:
        raise ValueError("as_of and occurred_at must be timezone-aware")
    age_hours = max(0.0, (as_of - evidence.occurred_at).total_seconds() / 3600)
    reliable_origins = {
        _source_origin(item.url_or_reference, item.platform)
        for item in evidence.sources
        if item.evidence_type in _RELIABLE_TYPES
    }
    visuals_ok = evidence.visual_plan.has_usable_factual_visuals or (
        evidence.visual_plan.ai_demo_available
        and bool(evidence.visual_plan.ai_disclosure)
    )
    checks = {
        "within_24_hours": age_hours <= max_age_hours,
        "two_independent_reliable_sources": len(reliable_origins) >= 2,
        "production_visuals": visuals_ok,
        "not_old_news_rehash": not evidence.old_news_rehash,
        "no_major_fact_conflict": not evidence.major_fact_conflict,
        "no_exploitative_harm": not evidence.exploitative_harm,
        "no_unresolved_high_stakes_claim": not evidence.high_stakes_unresolved,
        "cluster_review": (
            not cluster.needs_manual_review or evidence.cluster_review_approved
        ),
    }
    reason_by_check = {
        "within_24_hours": "outside_24_hours",
        "two_independent_reliable_sources": "insufficient_independent_sources",
        "production_visuals": "missing_production_visuals",
        "not_old_news_rehash": "old_news_rehash",
        "no_major_fact_conflict": "major_fact_conflict",
        "no_exploitative_harm": "exploitative_harm",
        "no_unresolved_high_stakes_claim": "high_stakes_unresolved",
        "cluster_review": "cluster_review_required",
    }
    reasons = [
        reason_by_check[name] for name, passed in checks.items() if not passed
    ]
    return VerificationDecision(
        event_id=cluster.event_id,
        passed=not reasons,
        age_hours=round(age_hours, 2),
        independent_reliable_source_count=len(reliable_origins),
        checks=checks,
        reasons=reasons,
    )
