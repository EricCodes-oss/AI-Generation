from datetime import date

from avatar_pipeline.config import load_config
from avatar_pipeline.event_clusterer import cluster_events
from avatar_pipeline.hotspot_models import CollectionStatus, HotspotFailure, TrendLabel
from avatar_pipeline.hotspot_repository import HotspotRepository
from avatar_pipeline.hotspot_service import HotspotService
from avatar_pipeline.models import DailyTask, HostProfile, TaskStatus
from avatar_pipeline.repository import DailyTaskRepository
from avatar_pipeline.service import DailyWorkflowService
from avatar_pipeline.workflow_refresh import topic_candidates_from_report
from tests.hotspot_factories import editorial_signals, record, snapshot, verification

DAY = date(2026, 8, 10)
CONFIG = load_config("configs/default.yaml").hotspot
TITLES = ["白海豚路径变化", "存款利率调整", "机器人赛事反转", "城市夜市新规"]


def _three_snapshots():
    snapshots = []
    for offset, captured_at in enumerate((
        "2026-08-10T19:40:00+08:00",
        "2026-08-10T19:50:00+08:00",
        "2026-08-10T20:00:00+08:00",
    )):
        records = []
        for event_index, title in enumerate(TITLES):
            for platform_index, platform in enumerate(("weibo", "baidu", "zhihu")):
                records.append(record(
                    f"{event_index}-{platform}-{offset}",
                    platform,
                    5 + platform_index - offset,
                    title,
                    captured_at=captured_at,
                    heat_value=100 * (offset + 1) * (event_index + 1),
                ))
        failures = []
        if offset == 1:
            failures = [HotspotFailure(
                platform="bilibili",
                captured_at=records[0].captured_at,
                reason="api returned -352",
                raw_snapshot_path="tmp/bilibili.json",
                status=CollectionStatus.RESTRICTED,
            )]
        snapshots.append(snapshot(f"t{offset}", captured_at, records=records, failures=failures))
    return snapshots


def _save_reviews(repository, snapshots):
    records = [item for shot in snapshots for item in shot.records]
    events = cluster_events(records, aliases={})
    repository.save_verifications(DAY, [verification(event_id=item.event_id) for item in events])
    repository.save_editorial_signals(
        DAY, [editorial_signals(event_id=item.event_id) for item in events]
    )


def test_three_snapshots_produce_only_top_three_and_preserve_failure_reason(tmp_path):
    repository = HotspotRepository(tmp_path)
    snapshots = _three_snapshots()
    for item in snapshots:
        repository.save_snapshot(DAY, item)
    _save_reviews(repository, snapshots)
    report = HotspotService(repository, CONFIG).build_report(DAY)
    assert report.outcome == "qualified_candidates"
    assert len(report.candidates) == 3
    assert all(item.score.total >= 75 for item in report.candidates)
    assert all(item.trend_label is not TrendLabel.INITIAL_SCREEN for item in report.candidates)
    assert report.collection_failures[0].reason == "api returned -352"


def test_single_platform_event_and_single_snapshot_cannot_claim_viral_growth(tmp_path):
    repository = HotspotRepository(tmp_path)
    only = record("w0", "weibo", 1, "单平台事件", heat_value=100)
    shot = snapshot("t0", "2026-08-10T19:40:00+08:00", records=[only])
    repository.save_snapshot(DAY, shot)
    _save_reviews(repository, [shot])
    report = HotspotService(repository, CONFIG).build_report(DAY)
    assert report.outcome == "no_qualified_hotspot"
    rejected = report.rejected_events[0]
    assert "three_independent_platforms" in rejected.reasons
    assert "two_consecutive_snapshots" in rejected.reasons


def test_no_qualified_hotspot_stops_before_production_refresh(tmp_path):
    repository = HotspotRepository(tmp_path)
    repository.save_snapshot(DAY, snapshot("t0", "2026-08-10T19:40:00+08:00"))
    report = HotspotService(repository, CONFIG).build_report(DAY)
    assert report.outcome == "no_qualified_hotspot"
    try:
        topic_candidates_from_report(report)
    except ValueError as error:
        assert "no qualified" in str(error)
    else:
        raise AssertionError("empty report must not enter production")


def test_verified_report_refresh_keeps_c2_host_and_creates_no_generation_assets(tmp_path):
    hotspot_repository = HotspotRepository(tmp_path)
    snapshots = _three_snapshots()
    for item in snapshots:
        hotspot_repository.save_snapshot(DAY, item)
    _save_reviews(hotspot_repository, snapshots)
    report = HotspotService(hotspot_repository, CONFIG).build_report(DAY)

    host = HostProfile(
        id="host-c2-pro-candidate-2-final",
        display_name="C2-Pro 新闻主持人",
        reference_image="output/host-v12-c2-pro/GPT-Image-2-Pro-C2-Pro-主持人最终选定.png",
        studio_reference="蓝色演播室、近景胸像、白衬衣、深藏青西装、无桌、避免手臂入镜",
        visual_style="知性亲和、专业克制、低AI感、五官清晰稳定",
        is_new=False,
        version=12,
    )
    production_repository = DailyTaskRepository(tmp_path)
    production_repository.create(
        DailyTask(day=DAY, host_profile=host, status=TaskStatus.TOPIC_SCRIPT_REVIEW)
    )
    refreshed = DailyWorkflowService(production_repository).refresh_unapproved_hotspots(
        DAY,
        topic_candidates_from_report(report),
        archive_reason="旧候选传播性不足",
        confirmed_host=host,
    )
    assert refreshed.host_profile == host
    assert refreshed.status is TaskStatus.TOPIC_SCRIPT_REVIEW
    assert refreshed.selected_topic_id is None
    assert refreshed.news_script is None
    assert refreshed.media_plan is None
    assert refreshed.artifacts == []
