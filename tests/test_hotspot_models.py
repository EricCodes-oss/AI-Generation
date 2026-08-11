from datetime import datetime

import pytest
from pydantic import ValidationError

from avatar_pipeline.hotspot_models import (
    CollectionStatus,
    ContentNature,
    HotspotFailure,
    HotspotRecord,
    HotspotSnapshot,
)

CAPTURED_AT = datetime.fromisoformat("2026-08-10T19:40:00+08:00")


def test_snapshot_keeps_success_and_failure_evidence_separate():
    record = HotspotRecord(
        record_id="weibo-1",
        platform="weibo",
        board_name="微博热搜",
        captured_at=CAPTURED_AT,
        timezone="Asia/Shanghai",
        rank=1,
        title="白海豚突然大拐弯",
        heat_raw="311万",
        heat_value=3_110_000,
        url_or_reference="weibo:白海豚突然大拐弯",
        raw_snapshot_path="tmp/t0/tophub.json",
        collection_status=CollectionStatus.SUCCESS,
        content_nature=ContentNature.NATURAL,
    )
    snapshot = HotspotSnapshot(
        snapshot_id="20260810-t0",
        captured_at=CAPTURED_AT,
        timezone="Asia/Shanghai",
        records=[record],
        failures=[
            HotspotFailure(
                platform="bilibili",
                captured_at=CAPTURED_AT,
                reason="api returned -352",
                raw_snapshot_path="tmp/t0/bilibili.json",
            )
        ],
    )
    assert snapshot.successful_platforms == {"weibo"}
    assert snapshot.failed_platforms == {"bilibili"}


def test_snapshot_rejects_record_with_a_different_capture_time():
    with pytest.raises(ValidationError, match="captured_at"):
        HotspotSnapshot(
            snapshot_id="bad",
            captured_at=CAPTURED_AT,
            timezone="Asia/Shanghai",
            records=[
                HotspotRecord(
                    record_id="x",
                    platform="baidu",
                    board_name="百度热搜",
                    captured_at=datetime.fromisoformat("2026-08-10T19:50:00+08:00"),
                    timezone="Asia/Shanghai",
                    rank=1,
                    title="事件",
                    url_or_reference="baidu:事件",
                    raw_snapshot_path="raw.json",
                )
            ],
        )
