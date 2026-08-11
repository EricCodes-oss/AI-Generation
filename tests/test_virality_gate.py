from datetime import datetime

import pytest

from avatar_pipeline.candidate_verifier import verify_candidate
from avatar_pipeline.config import load_config
from avatar_pipeline.hotspot_models import ContentNature
from avatar_pipeline.virality_gate import evaluate_virality_gate
from tests.hotspot_factories import cluster, record, trend, verification

CONFIG = load_config("configs/default.yaml").hotspot
AS_OF = datetime.fromisoformat("2026-08-10T20:00:00+08:00")


def _decision(records, *, consecutive=3):
    event = cluster(records)
    verified = verify_candidate(event, verification(), as_of=AS_OF, max_age_hours=24)
    return evaluate_virality_gate(
        event,
        trend(consecutive_snapshot_count=consecutive),
        records,
        verified,
        CONFIG,
    )


def test_valid_three_platform_event_passes_all_seven_gates():
    records = [
        record("w", "weibo", 4, "事件"),
        record("b", "baidu", 8, "事件"),
        record("z", "zhihu", 10, "事件"),
    ]
    decision = _decision(records)
    assert decision.passed is True
    assert set(decision.checks) == {
        "three_independent_platforms",
        "core_rank",
        "within_24_hours",
        "two_consecutive_snapshots",
        "natural_heat",
        "two_independent_reliable_sources",
        "production_visuals",
    }


@pytest.mark.parametrize(
    ("records", "consecutive", "failed_check"),
    [
        ([record("w", "weibo", 1, "事件")], 3, "three_independent_platforms"),
        (
            [
                record("w", "weibo", 11, "事件"),
                record("b", "baidu", 12, "事件"),
                record("z", "zhihu", 13, "事件"),
            ],
            3,
            "core_rank",
        ),
        (
            [
                record("w", "weibo", 1, "事件"),
                record("b", "baidu", 2, "事件"),
                record("z", "zhihu", 3, "事件"),
            ],
            1,
            "two_consecutive_snapshots",
        ),
        (
            [
                record(
                    "w",
                    "weibo",
                    1,
                    "事件",
                    nature=ContentNature.COMMERCIAL_PROMOTION,
                ),
                record(
                    "b",
                    "baidu",
                    2,
                    "事件",
                    nature=ContentNature.COMMERCIAL_PROMOTION,
                ),
                record(
                    "z",
                    "zhihu",
                    3,
                    "事件",
                    nature=ContentNature.COMMERCIAL_PROMOTION,
                ),
            ],
            3,
            "natural_heat",
        ),
    ],
)
def test_each_popularity_gate_fails_explicitly(records, consecutive, failed_check):
    decision = _decision(records, consecutive=consecutive)
    assert decision.passed is False
    assert decision.checks[failed_check] is False
