from datetime import datetime

import pytest

from avatar_pipeline.candidate_verifier import verify_candidate
from tests.hotspot_factories import cluster, record, verification

AS_OF = datetime.fromisoformat("2026-08-10T20:00:00+08:00")


@pytest.mark.parametrize(
    ("updates", "reason"),
    [
        ({"old_news_rehash": True}, "old_news_rehash"),
        ({"major_fact_conflict": True}, "major_fact_conflict"),
        ({"exploitative_harm": True}, "exploitative_harm"),
        ({"high_stakes_unresolved": True}, "high_stakes_unresolved"),
    ],
)
def test_disqualifying_fact_risks_fail_verification(updates, reason):
    item = record("w", "weibo", 1, "事件")
    evidence = verification().model_copy(update=updates)
    decision = verify_candidate(cluster([item]), evidence, as_of=AS_OF, max_age_hours=24)
    assert decision.passed is False
    assert reason in decision.reasons


def test_old_event_and_one_independent_source_fail():
    item = record("w", "weibo", 1, "事件")
    evidence = verification(occurred_at="2026-08-08T12:00:00+08:00")
    evidence = evidence.model_copy(update={"sources": evidence.sources[:1]})
    decision = verify_candidate(cluster([item]), evidence, as_of=AS_OF, max_age_hours=24)
    assert decision.checks["within_24_hours"] is False
    assert decision.checks["two_independent_reliable_sources"] is False


def test_low_confidence_cluster_requires_explicit_human_review():
    item = record("w", "weibo", 1, "事件")
    low_confidence = cluster([item], confidence=0.62, needs_manual_review=True)
    rejected = verify_candidate(
        low_confidence, verification(), as_of=AS_OF, max_age_hours=24
    )
    accepted = verify_candidate(
        low_confidence,
        verification(cluster_review_approved=True),
        as_of=AS_OF,
        max_age_hours=24,
    )
    assert rejected.checks["cluster_review"] is False
    assert accepted.checks["cluster_review"] is True


def test_visual_plan_requires_factual_assets_or_disclosed_ai_demo():
    item = record("w", "weibo", 1, "事件")
    evidence = verification()
    no_visual = evidence.model_copy(
        update={
            "visual_plan": evidence.visual_plan.model_copy(
                update={"assets": [], "has_usable_factual_visuals": False}
            )
        }
    )
    decision = verify_candidate(cluster([item]), no_visual, as_of=AS_OF, max_age_hours=24)
    assert decision.checks["production_visuals"] is False
