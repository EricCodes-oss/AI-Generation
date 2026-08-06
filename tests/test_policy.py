import pytest

from avatar_pipeline.models import FactStatus, SourceEvidence, TopicCandidate
from avatar_pipeline.policy import evaluate_candidate, rank_verified_candidates, screen_candidates


def evidence():
    return [
        SourceEvidence(
            source_id="a",
            platform="official",
            title="官方",
            url_or_reference="a",
            evidence_type="primary",
        ),
        SourceEvidence(
            source_id="b",
            platform="media",
            title="媒体",
            url_or_reference="b",
            evidence_type="corroboration",
        ),
    ]


def candidate(id, status="verified", **kwargs):
    return TopicCandidate(
        id=id,
        title=id,
        pillar="social_phenomena",
        score=kwargs.pop("score", 90),
        fact_status=status,
        source_evidence=kwargs.pop("source_evidence", evidence() if status == "verified" else []),
        risk_flags=kwargs.pop("risk_flags", []),
        verification_summary="经两个独立来源交叉确认" if status == "verified" else None,
        publishable=status == "verified",
        **kwargs,
    )


def test_verified_multi_source_candidate_is_admitted():
    decision = evaluate_candidate(candidate("safe"))
    assert decision.publishable is True
    assert decision.status is FactStatus.VERIFIED


@pytest.mark.parametrize("status", ["pending", "unverified", "high_risk", "malicious"])
def test_unready_or_risky_candidate_is_skipped(status):
    decision = evaluate_candidate(candidate(status, status=status))
    assert decision.publishable is False


def test_screening_returns_formal_pool_and_skipped_audit():
    accepted, skipped = screen_candidates(
        [
            candidate("safe"),
            candidate("pending", status="pending"),
            candidate("bad", status="malicious"),
        ]
    )
    assert [item.id for item in accepted] == ["safe"]
    assert {item.id for item in skipped} == {"pending", "bad"}


def test_ranking_never_returns_unverified_candidates():
    ranked = rank_verified_candidates(
        [
            candidate("low", score=70),
            candidate("high", score=95),
            candidate("pending", status="pending"),
        ],
        limit=3,
    )
    assert [item.id for item in ranked] == ["high", "low"]
