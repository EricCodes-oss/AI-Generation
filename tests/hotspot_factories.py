from datetime import datetime

from avatar_pipeline.hotspot_models import (
    CandidateVerification,
    ContentNature,
    EditorialSignals,
    EventCluster,
    EventTrend,
    HotspotFailure,
    HotspotRecord,
    HotspotSnapshot,
    PlatformTrendLabel,
    TrendLabel,
    TrendObservation,
    VisualPlan,
)
from avatar_pipeline.models import NewsPillarSlug, SourceEvidence

DEFAULT_CAPTURED_AT = "2026-08-10T19:40:00+08:00"


def record(
    record_id: str,
    platform: str,
    rank: int,
    title: str,
    *,
    captured_at: str = DEFAULT_CAPTURED_AT,
    heat_value: float | None = None,
    nature: ContentNature = ContentNature.NATURAL,
) -> HotspotRecord:
    captured = datetime.fromisoformat(captured_at)
    return HotspotRecord(
        record_id=record_id,
        platform=platform,
        board_name=f"{platform}-hot",
        captured_at=captured,
        timezone="Asia/Shanghai",
        rank=rank,
        title=title,
        heat_raw=str(heat_value) if heat_value is not None else None,
        heat_value=heat_value,
        url_or_reference=f"{platform}:{record_id}",
        raw_snapshot_path=f"tmp/{record_id}.json",
        content_nature=nature,
    )


def snapshot(
    snapshot_id: str,
    captured_at: str,
    *,
    records: list[HotspotRecord] | None = None,
    failures: list[HotspotFailure] | None = None,
) -> HotspotSnapshot:
    captured = datetime.fromisoformat(captured_at)
    aligned = [item.model_copy(update={"captured_at": captured}) for item in (records or [])]
    aligned_failures = [
        item.model_copy(update={"captured_at": captured}) for item in (failures or [])
    ]
    return HotspotSnapshot(
        snapshot_id=snapshot_id,
        captured_at=captured,
        timezone="Asia/Shanghai",
        records=aligned,
        failures=aligned_failures,
    )


def cluster(
    records: list[HotspotRecord],
    *,
    event_id: str = "event-1",
    confidence: float = 0.9,
    needs_manual_review: bool = False,
) -> EventCluster:
    return EventCluster(
        event_id=event_id,
        representative_title=records[0].title,
        aliases=sorted({item.title for item in records}),
        record_ids=[item.record_id for item in records],
        platforms={item.platform for item in records},
        first_seen_at=min(item.captured_at for item in records),
        last_seen_at=max(item.captured_at for item in records),
        cluster_confidence=confidence,
        needs_manual_review=needs_manual_review,
    )


def trend(
    *,
    event_id: str = "event-1",
    label: TrendLabel = TrendLabel.RISING,
    consecutive_snapshot_count: int = 3,
    new_platform_count: int = 1,
) -> EventTrend:
    captured = datetime.fromisoformat(DEFAULT_CAPTURED_AT)
    return EventTrend(
        event_id=event_id,
        observations=[
            TrendObservation(
                snapshot_id="t0",
                captured_at=captured,
                platform_ranks={"weibo": 5, "baidu": 8, "zhihu": 10},
                platform_heat_values={"weibo": 100.0},
            )
        ],
        label=label,
        platform_trend_labels={
            "weibo": PlatformTrendLabel.SURGING,
            "baidu": PlatformTrendLabel.RISING,
            "zhihu": PlatformTrendLabel.UNKNOWN,
        },
        consecutive_snapshot_count=consecutive_snapshot_count,
        new_platform_count=new_platform_count,
        rank_delta_by_platform={"weibo": 4, "baidu": 3},
        heat_growth_by_platform={"weibo": 0.5},
    )


def verification(
    *,
    event_id: str = "event-1",
    occurred_at: str = "2026-08-10T12:00:00+08:00",
    cluster_review_approved: bool = False,
) -> CandidateVerification:
    sources = [
        SourceEvidence(
            source_id="official-1",
            platform="cma.gov.cn",
            title="官方通报",
            url_or_reference="https://official.example/notice",
            evidence_type="official",
        ),
        SourceEvidence(
            source_id="media-1",
            platform="news.cn",
            title="权威媒体报道",
            url_or_reference="https://media.example/report",
            evidence_type="reputable_media",
        ),
    ]
    return CandidateVerification(
        event_id=event_id,
        occurred_at=datetime.fromisoformat(occurred_at),
        core_fact="核心事实已由独立来源交叉核验",
        sources=sources,
        primary_source_ids=["official-1"],
        cluster_review_approved=cluster_review_approved,
        visual_plan=VisualPlan(
            has_usable_factual_visuals=True,
            assets=["official-path-map.png"],
            copyright_notes=["引用时标注官方来源"],
        ),
    )


def editorial_signals(*, event_id: str = "event-1") -> EditorialSignals:
    return EditorialSignals(
        event_id=event_id,
        pillar=NewsPillarSlug.SOCIAL_PHENOMENA,
        click_title="台风路径为什么突然转弯？",
        why_click="路线反常且会影响普通人的出行与安全判断。",
        opening_hook="它没有按大多数人以为的方向继续走。",
        audience_relevance="关系沿海居民出行与防灾准备。",
        expected_lifetime="12-24小时",
        conflict_suspense=0.9,
        public_interest=0.9,
        curiosity_gap=0.9,
        visual_impact=0.8,
        explanatory_depth=0.8,
    )
