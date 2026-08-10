# Cross-Platform Viral Hotspot Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an auditable, deterministic hotspot engine that imports timestamped multi-platform snapshots, clusters one event across differing headlines, measures persistence and acceleration, applies hard popularity and verification gates, ranks no more than three high-click-potential candidates, and safely replaces the unapproved August 10 plan without changing the selected host or entering paid generation.

**Architecture:** Add a separate hotspot bounded context rather than stretching the existing three-pillar research workflow. Immutable snapshot evidence is normalized and persisted first; pure functions then cluster records, calculate time-series trends, enforce hard gates, score eligible events, and render a JSON/Markdown candidate report. A final explicit bridge converts verified report entries into the existing production `TopicCandidate` model and archives the unapproved plan before resetting only the topic/script/media fields.

**Tech Stack:** Python 3.11+, Pydantic 2, PyYAML, JSON file storage, pytest, Ruff; standard-library HTML/JSON/Unicode/date handling only.

---

## Global Constraints

- Keep the confirmed C2-Pro Candidate 2 identity and `output/host-v12-c2-pro/GPT-Image-2-Pro-C2-Pro-主持人最终选定.png` unchanged; the locked image SHA256 is `939324593eb718cd2a39be4c171f74178a6a48442f7e0d61afe8a875011e8a47`. The active task receives the audited `host_profile` only through the explicit reconciliation rule below.
- The saved V2 task currently has `host_profile: null` even though its media plan and `output/manual-run-2026-08-10/planning/host-profile.json` identify the confirmed host. V2→V3 migration must not invent it; `hotspot-refresh` must explicitly reconcile that null from the audited profile, reject any conflicting non-null host, and preserve the exact image path above.
- Do not call TTS, avatar, insert-generation, compositing, or other paid generation commands in this plan.
- Keep the 2026-08-10 production task at `topic_script_review` until a new topic, full script, and media plan are explicitly approved.
- Treat failed or restricted platforms as failures with reasons, never as zero heat.
- Never sum heat numbers across platforms; compare ranks and within-platform changes only.
- Do not label a single snapshot as rising or exploding. Two valid observations are the minimum for trend language.
- Return zero candidates when none pass all hard gates and the 75-point display threshold.
- Do not add fuzzy/embedding dependencies in V1. Deterministic aliases, entity tokens, headline tokens, and explicit review flags are sufficient.

## File structure

| File | Responsibility |
|---|---|
| `src/avatar_pipeline/hotspot_models.py` | Strict hotspot snapshot, event, trend, gate, score, verification, and report contracts. |
| `src/avatar_pipeline/hotspot_normalizer.py` | Platform mapping, rank/heat parsing, natural-content classification, and title token normalization. |
| `src/avatar_pipeline/hotspot_collectors.py` | Auditable local import adapters for canonical JSON and TopHub structured JSON; transparent failure ingestion. |
| `src/avatar_pipeline/hotspot_repository.py` | Atomic snapshot, verification, scoring-input, and report persistence under `workspace/hotspots/<date>/`. |
| `src/avatar_pipeline/event_clusterer.py` | Deterministic same-event grouping and low-confidence review flags. |
| `src/avatar_pipeline/trend_analyzer.py` | Per-event snapshot observations, persistence, rank movement, platform growth, and trend labels. |
| `src/avatar_pipeline/candidate_verifier.py` | Validate independent sources, recency, fact risk, and usable/AI-disclosed visual plans. |
| `src/avatar_pipeline/virality_gate.py` | Seven non-negotiable popularity/verification/production gates with explicit reasons. |
| `src/avatar_pipeline/virality_scorer.py` | Versioned 100-point scoring with reproducible component calculations. |
| `src/avatar_pipeline/hotspot_report.py` | Maximum-three candidate selection plus JSON and Markdown reporting. |
| `src/avatar_pipeline/hotspot_service.py` | Orchestrate stored snapshots through clustering, trend, gate, score, and report. |
| `src/avatar_pipeline/workflow_refresh.py` | Convert approved report candidates and safely archive/replace an unapproved production plan. |
| `src/avatar_pipeline/models.py` | Add an explicit archived-plan audit model and bump production task schema. |
| `src/avatar_pipeline/migration.py` | Migrate schema V2 tasks to V3 without inventing approvals or evidence. |
| `src/avatar_pipeline/service.py` | Expose safe unapproved-hotspot refresh through the existing workflow service. |
| `src/avatar_pipeline/cli.py` | Add snapshot import, build/report/status, and production refresh commands. |
| `src/avatar_pipeline/config.py` | Validate hotspot thresholds, weights, platform aliases, and rule version. |
| `configs/default.yaml` | Lock the confirmed thresholds and score weights. |
| `tests/hotspot_factories.py` | Shared deterministic snapshot/event/verification test builders. |
| `tests/fixtures/hotspots/` | Canonical, TopHub, failure, verification, and scoring fixtures. |
| `tests/test_hotspot_*.py` | Unit tests for each new module. |
| `tests/test_hotspot_end_to_end.py` | Three-snapshot acceptance flow and no-qualified-event flow. |
| `docs/runbooks/manual-hotspot-sampling.md` | Exact T0/T+10/T+20 import, review, refresh, and safety commands. |

### Task 1: Lock hotspot configuration and domain contracts

**Files:**
- Create: `src/avatar_pipeline/hotspot_models.py`
- Create: `tests/hotspot_factories.py`
- Create: `tests/test_hotspot_models.py`
- Modify: `src/avatar_pipeline/config.py:73-160`
- Modify: `configs/default.yaml`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Write failing configuration and model tests**

```python
# tests/test_hotspot_models.py
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
```

```python
# additions to tests/test_config.py
def test_default_config_locks_confirmed_hotspot_rules():
    config = load_config(Path("configs/default.yaml"))
    assert config.hotspot.rule_version == "viral-v1.0"
    assert config.hotspot.core_platforms == [
        "weibo", "douyin", "baidu", "toutiao",
        "kuaishou", "zhihu", "bilibili", "wechat",
    ]
    assert config.hotspot.platform_categories["weibo"] == "social"
    assert config.hotspot.platform_categories["baidu"] == "search"
    assert config.hotspot.snapshot_interval_minutes == 10
    assert config.hotspot.snapshot_count == 3
    assert config.hotspot.min_platforms == 3
    assert config.hotspot.min_consecutive_snapshots == 2
    assert config.hotspot.display_score_min == 75
    assert sum(config.hotspot.score_weights.model_dump().values()) == 100
```

- [ ] **Step 2: Run the tests and verify the missing-module/config failure**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_hotspot_models.py tests/test_config.py -v`

Expected: FAIL during collection because `avatar_pipeline.hotspot_models` and `AppConfig.hotspot` do not exist.

- [ ] **Step 3: Add strict hotspot models**

Create `src/avatar_pipeline/hotspot_models.py` with these exact public contracts; all models inherit `DomainModel` from `models.py` so unknown fields remain forbidden:

```python
"""Auditable contracts for cross-platform viral hotspot discovery."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from avatar_pipeline.models import DomainModel, NewsPillarSlug, SourceEvidence, utc_now


class CollectionStatus(StrEnum):
    SUCCESS = "success"
    RESTRICTED = "restricted"
    FAILED = "failed"


class ContentNature(StrEnum):
    NATURAL = "natural"
    ADVERTISEMENT = "advertisement"
    PLATFORM_ACTIVITY = "platform_activity"
    COMMERCIAL_PROMOTION = "commercial_promotion"
    PINNED = "pinned"
    UNKNOWN = "unknown"


class PlatformTrendLabel(StrEnum):
    SURGING = "surging"
    RISING = "rising"
    STABLE = "stable"
    FALLING = "falling"
    UNKNOWN = "unknown"


class TrendLabel(StrEnum):
    INITIAL_SCREEN = "initial_screen"
    SURGING = "surging"
    RISING = "rising"
    STABLE = "stable"
    FALLING = "falling"
    VOLATILE = "volatile"


class DirectorAction(StrEnum):
    DO_NOW = "do_now"
    WATCH = "watch"
    DROP = "drop"


class ViralityBand(StrEnum):
    DIRECTOR_FIRST = "director_first"
    STRONG_CANDIDATE = "strong_candidate"
    BACKUP = "backup"


class HotspotRecord(DomainModel):
    record_id: str = Field(min_length=1)
    platform: str = Field(min_length=1)
    board_name: str = Field(min_length=1)
    captured_at: datetime
    timezone: str = Field(min_length=1)
    rank: int = Field(ge=1)
    title: str = Field(min_length=1)
    heat_raw: str | None = None
    heat_value: float | None = Field(default=None, ge=0)
    url_or_reference: str = Field(min_length=1)
    raw_snapshot_path: str = Field(min_length=1)
    collection_status: CollectionStatus = CollectionStatus.SUCCESS
    content_nature: ContentNature = ContentNature.UNKNOWN
    is_top: bool = False
    published_at: datetime | None = None
    aliases: list[str] = Field(default_factory=list)


class HotspotFailure(DomainModel):
    platform: str = Field(min_length=1)
    captured_at: datetime
    reason: str = Field(min_length=1)
    raw_snapshot_path: str = Field(min_length=1)
    status: CollectionStatus = CollectionStatus.FAILED


class HotspotSnapshot(DomainModel):
    snapshot_id: str = Field(min_length=1)
    captured_at: datetime
    timezone: str = Field(min_length=1)
    records: list[HotspotRecord] = Field(default_factory=list)
    failures: list[HotspotFailure] = Field(default_factory=list)
    imported_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_capture_identity(self) -> "HotspotSnapshot":
        if any(item.captured_at != self.captured_at for item in self.records):
            raise ValueError("record captured_at must equal snapshot captured_at")
        if any(item.captured_at != self.captured_at for item in self.failures):
            raise ValueError("failure captured_at must equal snapshot captured_at")
        ids = [item.record_id for item in self.records]
        if len(ids) != len(set(ids)):
            raise ValueError("record ids must be unique inside a snapshot")
        return self

    @property
    def successful_platforms(self) -> set[str]:
        return {item.platform for item in self.records}

    @property
    def failed_platforms(self) -> set[str]:
        return {item.platform for item in self.failures}


class EventCluster(DomainModel):
    event_id: str = Field(min_length=1)
    representative_title: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    record_ids: list[str] = Field(min_length=1)
    platforms: set[str] = Field(min_length=1)
    first_seen_at: datetime
    last_seen_at: datetime
    cluster_confidence: float = Field(ge=0, le=1)
    needs_manual_review: bool = False


class TrendObservation(DomainModel):
    snapshot_id: str = Field(min_length=1)
    captured_at: datetime
    platform_ranks: dict[str, int] = Field(default_factory=dict)
    platform_heat_values: dict[str, float] = Field(default_factory=dict)


class EventTrend(DomainModel):
    event_id: str = Field(min_length=1)
    observations: list[TrendObservation] = Field(min_length=1)
    label: TrendLabel
    platform_trend_labels: dict[str, PlatformTrendLabel] = Field(default_factory=dict)
    consecutive_snapshot_count: int = Field(ge=1)
    new_platform_count: int = Field(ge=0)
    related_subtopic_count: int = Field(default=0, ge=0)
    rank_delta_by_platform: dict[str, int] = Field(default_factory=dict)
    heat_growth_by_platform: dict[str, float] = Field(default_factory=dict)


class VisualPlan(DomainModel):
    has_usable_factual_visuals: bool = False
    ai_demo_available: bool = False
    ai_disclosure: str | None = None
    assets: list[str] = Field(default_factory=list)
    copyright_notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_ai_disclosure(self) -> "VisualPlan":
        if self.ai_demo_available and not self.ai_disclosure:
            raise ValueError("AI demo requires an explicit disclosure")
        return self


class CandidateVerification(DomainModel):
    event_id: str = Field(min_length=1)
    occurred_at: datetime
    core_fact: str = Field(min_length=1)
    sources: list[SourceEvidence] = Field(default_factory=list)
    primary_source_ids: list[str] = Field(default_factory=list)
    unresolved_claims: list[str] = Field(default_factory=list)
    old_news_rehash: bool = False
    major_fact_conflict: bool = False
    exploitative_harm: bool = False
    high_stakes_unresolved: bool = False
    wording_to_avoid: list[str] = Field(default_factory=list)
    cluster_review_approved: bool = False
    related_subtopic_ids: list[str] = Field(default_factory=list)
    visual_plan: VisualPlan
    verified_at: datetime = Field(default_factory=utc_now)


class VerificationDecision(DomainModel):
    event_id: str = Field(min_length=1)
    passed: bool
    age_hours: float = Field(ge=0)
    independent_reliable_source_count: int = Field(ge=0)
    checks: dict[str, bool]
    reasons: list[str] = Field(default_factory=list)


class EditorialSignals(DomainModel):
    event_id: str = Field(min_length=1)
    pillar: NewsPillarSlug
    click_title: str = Field(min_length=1)
    why_click: str = Field(min_length=1)
    opening_hook: str = Field(min_length=1)
    audience_relevance: str = Field(min_length=1)
    expected_lifetime: str = Field(min_length=1)
    conflict_suspense: float = Field(ge=0, le=1)
    public_interest: float = Field(ge=0, le=1)
    curiosity_gap: float = Field(ge=0, le=1)
    visual_impact: float = Field(ge=0, le=1)
    explanatory_depth: float = Field(ge=0, le=1)


class GateDecision(DomainModel):
    event_id: str = Field(min_length=1)
    passed: bool
    checks: dict[str, bool]
    reasons: list[str] = Field(default_factory=list)


class ViralityScore(DomainModel):
    event_id: str = Field(min_length=1)
    rule_version: str = Field(min_length=1)
    cross_platform_resonance: float = Field(ge=0, le=25)
    trend_velocity: float = Field(ge=0, le=20)
    conflict_suspense: float = Field(ge=0, le=15)
    public_interest: float = Field(ge=0, le=10)
    curiosity_gap: float = Field(ge=0, le=10)
    visual_impact: float = Field(ge=0, le=10)
    explanatory_depth: float = Field(ge=0, le=5)
    fact_safety: float = Field(ge=0, le=5)
    total: float = Field(ge=0, le=100)

    @model_validator(mode="after")
    def validate_total(self) -> "ViralityScore":
        components = (
            self.cross_platform_resonance,
            self.trend_velocity,
            self.conflict_suspense,
            self.public_interest,
            self.curiosity_gap,
            self.visual_impact,
            self.explanatory_depth,
            self.fact_safety,
        )
        if abs(self.total - sum(components)) > 0.01:
            raise ValueError("virality total must equal component sum")
        return self


class HotspotCandidateReport(DomainModel):
    event_id: str
    representative_title: str
    click_title: str
    collected_from: datetime
    collected_to: datetime
    platform_evidence: list[str]
    trend_label: TrendLabel
    platform_trend_labels: dict[str, PlatformTrendLabel] = Field(default_factory=dict)
    related_subtopic_count: int = Field(default=0, ge=0)
    score: ViralityScore
    score_band: ViralityBand
    why_click: str
    opening_hook: str
    audience_relevance: str
    visual_assets: list[str]
    copyright_notes: list[str]
    expected_lifetime: str
    risks: list[str]
    wording_to_avoid: list[str]
    director_action: DirectorAction
    pillar: NewsPillarSlug
    source_evidence: list[SourceEvidence]
    verification_summary: str


class EvaluatedHotspot(DomainModel):
    cluster: EventCluster
    trend: EventTrend
    gate: GateDecision
    score: ViralityScore | None = None
    verification: CandidateVerification | None = None
    editorial_signals: EditorialSignals | None = None


class HotspotRejectedEvent(DomainModel):
    event_id: str
    representative_title: str
    reasons: list[str] = Field(min_length=1)


class HotspotReport(DomainModel):
    day: str
    rule_version: str
    generated_at: datetime = Field(default_factory=utc_now)
    snapshot_ids: list[str]
    collection_failures: list[HotspotFailure]
    rejected_events: list[HotspotRejectedEvent] = Field(default_factory=list)
    candidates: list[HotspotCandidateReport] = Field(max_length=3)
    director_recommendation_event_id: str | None = None
    outcome: Literal["qualified_candidates", "no_qualified_hotspot"]
```

- [ ] **Step 4: Add deterministic test factories used by every later task**

Create `tests/hotspot_factories.py` with the complete helpers below. Keep all defaults fixed to August 10 so tests never depend on the machine clock:

```python
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
```

- [ ] **Step 5: Add versioned configuration**

Add these strict models to `src/avatar_pipeline/config.py` and add `hotspot: HotspotConfig` to `AppConfig`:

```python
class HotspotScoreWeights(StrictModel):
    cross_platform_resonance: Literal[25]
    trend_velocity: Literal[20]
    conflict_suspense: Literal[15]
    public_interest: Literal[10]
    curiosity_gap: Literal[10]
    visual_impact: Literal[10]
    explanatory_depth: Literal[5]
    fact_safety: Literal[5]


class HotspotConfig(StrictModel):
    rule_version: str = Field(min_length=1)
    core_platforms: list[str] = Field(min_length=3)
    platform_aliases: dict[str, str]
    platform_categories: dict[str, str]
    event_aliases: dict[str, list[str]] = Field(default_factory=dict)
    snapshot_interval_minutes: int = Field(gt=0)
    snapshot_count: int = Field(ge=2)
    min_platforms: int = Field(ge=2)
    top_rank_single: int = Field(gt=0)
    top_rank_multi: int = Field(gt=0)
    min_top_rank_multi_platforms: int = Field(ge=2)
    max_event_age_hours: int = Field(gt=0)
    min_consecutive_snapshots: int = Field(ge=2)
    display_score_min: int = Field(ge=0, le=100)
    strong_score_min: int = Field(ge=0, le=100)
    director_score_min: int = Field(ge=0, le=100)
    max_candidates: Literal[3]
    score_weights: HotspotScoreWeights
```

Append this exact YAML block to `configs/default.yaml`:

```yaml
hotspot:
  rule_version: viral-v1.0
  core_platforms: [weibo, douyin, baidu, toutiao, kuaishou, zhihu, bilibili, wechat]
  platform_aliases:
    微博: weibo
    抖音: douyin
    百度: baidu
    今日头条: toutiao
    快手: kuaishou
    知乎: zhihu
    哔哩哔哩: bilibili
    B站: bilibili
    微信: wechat
  platform_categories:
    weibo: social
    douyin: short_video
    baidu: search
    toutiao: news_feed
    kuaishou: short_video
    zhihu: knowledge
    bilibili: long_video
    wechat: social_content
  event_aliases: {}
  snapshot_interval_minutes: 10
  snapshot_count: 3
  min_platforms: 3
  top_rank_single: 5
  top_rank_multi: 10
  min_top_rank_multi_platforms: 2
  max_event_age_hours: 24
  min_consecutive_snapshots: 2
  display_score_min: 75
  strong_score_min: 80
  director_score_min: 85
  max_candidates: 3
  score_weights:
    cross_platform_resonance: 25
    trend_velocity: 20
    conflict_suspense: 15
    public_interest: 10
    curiosity_gap: 10
    visual_impact: 10
    explanatory_depth: 5
    fact_safety: 5
```

- [ ] **Step 6: Run focused tests**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_hotspot_models.py tests/test_config.py -v`

Expected: PASS.

- [ ] **Step 7: Commit the contracts**

```bash
git add configs/default.yaml src/avatar_pipeline/config.py src/avatar_pipeline/hotspot_models.py tests/hotspot_factories.py tests/test_hotspot_models.py tests/test_config.py
git commit -m "feat: add viral hotspot domain contracts"
```

### Task 2: Persist immutable snapshots and report inputs

**Files:**
- Create: `src/avatar_pipeline/hotspot_repository.py`
- Create: `tests/test_hotspot_repository.py`

- [ ] **Step 1: Write repository round-trip and immutability tests**

```python
# tests/test_hotspot_repository.py
from datetime import date

import pytest

from avatar_pipeline.hotspot_repository import HotspotRepository, SnapshotAlreadyExists
from tests.hotspot_factories import snapshot


def test_repository_round_trips_snapshot_and_lists_chronologically(tmp_path):
    repository = HotspotRepository(tmp_path)
    later = snapshot("t1", "2026-08-10T19:50:00+08:00")
    earlier = snapshot("t0", "2026-08-10T19:40:00+08:00")
    repository.save_snapshot(date(2026, 8, 10), later)
    repository.save_snapshot(date(2026, 8, 10), earlier)
    assert [item.snapshot_id for item in repository.list_snapshots(date(2026, 8, 10))] == [
        "t0", "t1"
    ]


def test_repository_refuses_to_overwrite_raw_snapshot(tmp_path):
    repository = HotspotRepository(tmp_path)
    item = snapshot("t0", "2026-08-10T19:40:00+08:00")
    repository.save_snapshot(date(2026, 8, 10), item)
    with pytest.raises(SnapshotAlreadyExists, match="t0"):
        repository.save_snapshot(date(2026, 8, 10), item)
```

- [ ] **Step 2: Run the test and verify the missing repository failure**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_hotspot_repository.py -v`

Expected: FAIL because `avatar_pipeline.hotspot_repository` does not exist.

- [ ] **Step 3: Implement atomic JSON persistence**

Create `src/avatar_pipeline/hotspot_repository.py` exactly as follows:

```python
"""Atomic, auditable persistence for imported hotspot evidence and reports."""

import json
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from pydantic import BaseModel

from avatar_pipeline.hotspot_models import (
    CandidateVerification,
    EditorialSignals,
    HotspotReport,
    HotspotSnapshot,
)


class SnapshotAlreadyExists(RuntimeError):
    """Raised when immutable raw evidence would be overwritten."""


class HotspotRepository:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def save_snapshot(self, day: date, snapshot: HotspotSnapshot) -> Path:
        path = self._day_root(day) / "snapshots" / f"{snapshot.snapshot_id}.json"
        if path.exists():
            raise SnapshotAlreadyExists(snapshot.snapshot_id)
        self._write_model(path, snapshot)
        return path

    def list_snapshots(self, day: date) -> list[HotspotSnapshot]:
        paths = (self._day_root(day) / "snapshots").glob("*.json")
        snapshots = [
            HotspotSnapshot.model_validate_json(path.read_text(encoding="utf-8"))
            for path in paths
        ]
        return sorted(snapshots, key=lambda item: item.captured_at)

    def save_verifications(
        self, day: date, items: list[CandidateVerification]
    ) -> Path:
        return self._write_json(
            self._day_root(day) / "verification.json",
            [item.model_dump(mode="json") for item in items],
        )

    def load_verifications(self, day: date) -> dict[str, CandidateVerification]:
        path = self._day_root(day) / "verification.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        items = [CandidateVerification.model_validate(item) for item in payload]
        return {item.event_id: item for item in items}

    def save_editorial_signals(
        self, day: date, items: list[EditorialSignals]
    ) -> Path:
        return self._write_json(
            self._day_root(day) / "editorial-signals.json",
            [item.model_dump(mode="json") for item in items],
        )

    def load_editorial_signals(self, day: date) -> dict[str, EditorialSignals]:
        path = self._day_root(day) / "editorial-signals.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        items = [EditorialSignals.model_validate(item) for item in payload]
        return {item.event_id: item for item in items}

    def save_report(
        self, day: date, report: HotspotReport, markdown: str
    ) -> tuple[Path, Path]:
        root = self._day_root(day) / "reports"
        json_path = root / "candidate-report.json"
        markdown_path = root / "candidate-report.md"
        self._write_model(json_path, report)
        self._atomic_text(markdown_path, markdown)
        return json_path, markdown_path

    def _day_root(self, day: date) -> Path:
        return self.root / "hotspots" / day.isoformat()

    def _write_model(self, path: Path, model: BaseModel) -> Path:
        return self._write_json(path, model.model_dump(mode="json"))

    def _write_json(self, path: Path, payload: Any) -> Path:
        text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        return self._atomic_text(path, text)

    @staticmethod
    def _atomic_text(path: Path, text: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        normalized = text.rstrip("\n") + "\n"
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(normalized)
            temporary_path = Path(handle.name)
        temporary_path.replace(path)
        return path
```

- [ ] **Step 4: Run repository tests**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_hotspot_repository.py -v`

Expected: PASS.

- [ ] **Step 5: Commit persistence**

```bash
git add src/avatar_pipeline/hotspot_repository.py tests/test_hotspot_repository.py
git commit -m "feat: persist auditable hotspot snapshots"
```

### Task 3: Import and normalize auditable local evidence

**Files:**
- Create: `src/avatar_pipeline/hotspot_normalizer.py`
- Create: `src/avatar_pipeline/hotspot_collectors.py`
- Create: `tests/fixtures/hotspots/tophub-t0.json`
- Create: `tests/fixtures/hotspots/canonical-t0.json`
- Create: `tests/test_hotspot_normalizer.py`
- Create: `tests/test_hotspot_collectors.py`

- [ ] **Step 1: Write failing heat, advertising, alias, and failure tests**

```python
# tests/test_hotspot_normalizer.py
from avatar_pipeline.hotspot_normalizer import classify_nature, normalize_platform, parse_heat


def test_parse_heat_keeps_platform_value_without_cross_platform_conversion():
    assert parse_heat("311万") == 3_110_000
    assert parse_heat("80455303次播放") == 80_455_303
    assert parse_heat(9620000) == 9_620_000
    assert parse_heat("") is None


def test_platform_alias_and_commercial_filter_are_deterministic():
    aliases = {"微博": "weibo", "淘宝 ‧ 天猫": "commerce"}
    assert normalize_platform("微博", aliases) == "weibo"
    assert classify_nature("淘宝 ‧ 天猫", "券后19.9元") == "commercial_promotion"
    assert classify_nature("微博", "白海豚突然大拐弯") == "natural"
```

```python
# tests/test_hotspot_collectors.py
from datetime import datetime
from pathlib import Path

from avatar_pipeline.hotspot_collectors import (
    import_canonical_snapshot,
    import_tophub_snapshot,
)


def test_canonical_import_round_trips_the_auditable_snapshot():
    snapshot = import_canonical_snapshot(
        Path("tests/fixtures/hotspots/canonical-t0.json")
    )
    assert snapshot.snapshot_id == "t0"
    assert snapshot.captured_at == datetime.fromisoformat("2026-08-10T19:40:00+08:00")
    assert snapshot.records == []
    assert snapshot.failures == []


def test_tophub_import_records_restricted_platform_instead_of_zero_heat():
    snapshot = import_tophub_snapshot(
        path=Path("tests/fixtures/hotspots/tophub-t0.json"),
        snapshot_id="t0",
        captured_at=datetime.fromisoformat("2026-08-10T19:40:00+08:00"),
        timezone="Asia/Shanghai",
        platform_aliases={"微博": "weibo", "百度": "baidu"},
        failures={"bilibili": ("api returned -352", "tmp/t0/bilibili.json")},
    )
    assert {item.platform for item in snapshot.records} == {"weibo", "baidu"}
    assert snapshot.failures[0].platform == "bilibili"
    assert snapshot.failures[0].reason == "api returned -352"
```

- [ ] **Step 2: Run focused tests and verify missing modules**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_hotspot_normalizer.py tests/test_hotspot_collectors.py -v`

Expected: FAIL because the normalizer and collector modules do not exist.

- [ ] **Step 3: Implement normalization primitives**

Create `src/avatar_pipeline/hotspot_normalizer.py` with:

```python
"""Deterministic normalization without cross-platform heat conversion."""

import re
import unicodedata

from avatar_pipeline.hotspot_models import ContentNature


_HEAT_PATTERN = re.compile(r"([0-9]+(?:\.[0-9]+)?)")
_MULTIPLIERS = {"万": 10_000.0, "w": 10_000.0, "W": 10_000.0, "亿": 100_000_000.0}
_COMMERCIAL_TERMS = ("券后", "原价", "到手价", "热销", "优惠", "购买", "促销")
_ACTIVITY_TERMS = ("平台活动", "签到活动", "挑战赛入口")
_PINNED_TERMS = ("置顶", "推荐位")


def parse_heat(value: str | int | float | None) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    compact = value.replace(",", "").replace(" ", "")
    match = _HEAT_PATTERN.search(compact)
    if not match:
        return None
    number = float(match.group(1))
    multiplier = next((factor for marker, factor in _MULTIPLIERS.items() if marker in compact), 1.0)
    return number * multiplier


def normalize_platform(name: str, aliases: dict[str, str]) -> str:
    return aliases.get(name.strip(), name.strip().casefold().replace(" ", "_"))


def classify_nature(platform: str, title: str) -> ContentNature:
    text = f"{platform} {title}"
    if any(term in text for term in _COMMERCIAL_TERMS):
        return ContentNature.COMMERCIAL_PROMOTION
    if any(term in text for term in _ACTIVITY_TERMS):
        return ContentNature.PLATFORM_ACTIVITY
    if any(term in text for term in _PINNED_TERMS):
        return ContentNature.PINNED
    return ContentNature.NATURAL


def normalize_title_tokens(title: str) -> set[str]:
    cleaned = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]", "", unicodedata.normalize("NFKC", title))
    return {cleaned[index:index + 2] for index in range(max(0, len(cleaned) - 1))}
```

- [ ] **Step 4: Implement canonical and TopHub import adapters**

Create `src/avatar_pipeline/hotspot_collectors.py` with two public functions:

```python
"""Adapters that import already-captured local evidence; no network access."""

import json
from datetime import datetime
from pathlib import Path

from avatar_pipeline.hotspot_models import (
    CollectionStatus,
    HotspotFailure,
    HotspotRecord,
    HotspotSnapshot,
)
from avatar_pipeline.hotspot_normalizer import (
    classify_nature,
    normalize_platform,
    parse_heat,
)


def import_canonical_snapshot(path: Path) -> HotspotSnapshot:
    return HotspotSnapshot.model_validate_json(path.read_text(encoding="utf-8"))


def import_tophub_snapshot(
    *,
    path: Path,
    snapshot_id: str,
    captured_at: datetime,
    timezone: str,
    platform_aliases: dict[str, str],
    failures: dict[str, tuple[str, str]],
) -> HotspotSnapshot:
    boards = json.loads(path.read_text(encoding="utf-8"))
    records: list[HotspotRecord] = []
    for board in boards:
        source_platform = str(board["platform"])
        platform = normalize_platform(source_platform, platform_aliases)
        if platform not in set(platform_aliases.values()):
            continue
        for index, item in enumerate(board.get("items", []), start=1):
            rank_text = str(item.get("rank") or index)
            if not rank_text.isdigit():
                continue
            title = str(item.get("title", "")).strip()
            if not title:
                continue
            records.append(HotspotRecord(
                record_id=f"{snapshot_id}:{platform}:{rank_text}:{index}",
                platform=platform,
                board_name=source_platform,
                captured_at=captured_at,
                timezone=timezone,
                rank=int(rank_text),
                title=title,
                heat_raw=str(item.get("heat") or "") or None,
                heat_value=parse_heat(item.get("heat")),
                url_or_reference=str(item.get("url") or f"{platform}:{title}"),
                raw_snapshot_path=str(path),
                content_nature=classify_nature(source_platform, title),
            ))
    failure_items = [
        HotspotFailure(
            platform=platform,
            captured_at=captured_at,
            reason=reason,
            raw_snapshot_path=raw_path,
            status=CollectionStatus.RESTRICTED,
        )
        for platform, (reason, raw_path) in sorted(failures.items())
    ]
    return HotspotSnapshot(
        snapshot_id=snapshot_id,
        captured_at=captured_at,
        timezone=timezone,
        records=records,
        failures=failure_items,
    )
```

Create `tests/fixtures/hotspots/tophub-t0.json` with this exact payload:

```json
[
  {
    "platform": "微博",
    "items": [
      {"rank": "1", "title": "白海豚突然大拐弯", "heat": "311万", "url": "weibo:1"},
      {"rank": "2", "title": "城市公园夜间开放", "heat": "120万", "url": "weibo:2"}
    ]
  },
  {
    "platform": "百度",
    "items": [
      {"rank": "2", "title": "台风白海豚走出罕见路线", "heat": "781万", "url": "baidu:1"},
      {"rank": "3", "title": "暑期铁路客流增长", "heat": "650万", "url": "baidu:2"}
    ]
  }
]
```

Create `tests/fixtures/hotspots/canonical-t0.json` with this exact payload:

```json
{
  "snapshot_id": "t0",
  "captured_at": "2026-08-10T19:40:00+08:00",
  "timezone": "Asia/Shanghai",
  "records": [],
  "failures": [],
  "imported_at": "2026-08-10T19:40:01+08:00"
}
```

- [ ] **Step 5: Run focused tests and lint**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_hotspot_normalizer.py tests/test_hotspot_collectors.py -v`

Expected: PASS.

Run: `.venv/bin/ruff check src/avatar_pipeline/hotspot_normalizer.py src/avatar_pipeline/hotspot_collectors.py tests/test_hotspot_normalizer.py tests/test_hotspot_collectors.py`

Expected: PASS with no diagnostics.

- [ ] **Step 6: Commit import adapters**

```bash
git add src/avatar_pipeline/hotspot_normalizer.py src/avatar_pipeline/hotspot_collectors.py tests/fixtures/hotspots tests/test_hotspot_normalizer.py tests/test_hotspot_collectors.py
git commit -m "feat: import and normalize hotspot evidence"
```

### Task 4: Cluster differing headlines into auditable events

**Files:**
- Create: `src/avatar_pipeline/event_clusterer.py`
- Create: `tests/test_event_clusterer.py`

- [ ] **Step 1: Write failing event-clustering tests**

```python
# tests/test_event_clusterer.py
from avatar_pipeline.event_clusterer import cluster_events
from tests.hotspot_factories import record


def test_typhoon_alias_headlines_form_one_event():
    records = [
        record("w1", "weibo", 1, "白海豚突然大拐弯"),
        record("b1", "baidu", 2, "台风白海豚走出罕见路线"),
        record("z1", "zhihu", 4, "台风白海豚为何出现神走位"),
    ]
    clusters = cluster_events(records, aliases={"白海豚": ["台风白海豚"]})
    assert len(clusters) == 1
    assert clusters[0].platforms == {"weibo", "baidu", "zhihu"}
    assert set(clusters[0].aliases) == {item.title for item in records}


def test_event_id_stays_stable_when_a_later_alias_headline_is_added():
    aliases = {"白海豚": ["台风白海豚"]}
    initial = [
        record("w0", "weibo", 1, "白海豚突然大拐弯"),
        record("b0", "baidu", 2, "台风白海豚走出罕见路线"),
    ]
    later = record(
        "z1",
        "zhihu",
        4,
        "神走位，白海豚路径急转",
        captured_at="2026-08-10T19:50:00+08:00",
    )
    initial_event_id = cluster_events(initial, aliases=aliases)[0].event_id
    expanded_event_id = cluster_events([*initial, later], aliases=aliases)[0].event_id
    assert expanded_event_id == initial_event_id


def test_low_confidence_related_impact_does_not_silently_merge():
    records = [
        record("a", "weibo", 1, "台风白海豚走出罕见路线"),
        record("b", "baidu", 3, "强降雨导致城区积水"),
    ]
    clusters = cluster_events(records, aliases={"白海豚": ["台风白海豚"]})
    assert len(clusters) == 2
```

- [ ] **Step 2: Run the test and verify the missing clusterer failure**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_event_clusterer.py -v`

Expected: FAIL because `avatar_pipeline.event_clusterer` does not exist.

- [ ] **Step 3: Implement deterministic pair matching and stable event identities**

Create `src/avatar_pipeline/event_clusterer.py` exactly as follows:

```python
"""Deterministic event clustering with auditable, stable event identifiers."""

import hashlib
import re
import unicodedata
from collections import defaultdict
from collections.abc import Sequence

from avatar_pipeline.hotspot_models import ContentNature, EventCluster, HotspotRecord
from avatar_pipeline.hotspot_normalizer import normalize_title_tokens


_MATCH_THRESHOLD = 0.58
_REVIEW_THRESHOLD = 0.68


def _canonical_text(title: str, aliases: dict[str, list[str]]) -> str:
    normalized = unicodedata.normalize("NFKC", title)
    for canonical, variants in aliases.items():
        for variant in sorted([canonical, *variants], key=len, reverse=True):
            normalized = normalized.replace(variant, canonical)
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]", "", normalized)


def _matched_aliases(title: str, aliases: dict[str, list[str]]) -> set[str]:
    canonical = _canonical_text(title, aliases)
    return {key for key in aliases if key in canonical}


def _similarity(left: str, right: str, aliases: dict[str, list[str]]) -> float:
    left_text = _canonical_text(left, aliases)
    right_text = _canonical_text(right, aliases)
    left_tokens = normalize_title_tokens(left_text)
    right_tokens = normalize_title_tokens(right_text)
    union = left_tokens | right_tokens
    jaccard = len(left_tokens & right_tokens) / len(union) if union else 0.0
    shared_alias = bool(
        _matched_aliases(left, aliases) & _matched_aliases(right, aliases)
    )
    return min(1.0, jaccard + (0.50 if shared_alias else 0.0))


def _event_key(
    members: Sequence[HotspotRecord], aliases: dict[str, list[str]]
) -> str:
    shared_aliases = set.intersection(
        *(_matched_aliases(item.title, aliases) for item in members)
    )
    if shared_aliases:
        return "alias:" + "|".join(sorted(shared_aliases))
    anchor = min(members, key=lambda item: (item.captured_at, item.record_id))
    return "anchor:" + _canonical_text(anchor.title, aliases)


def cluster_events(
    records: Sequence[HotspotRecord], *, aliases: dict[str, list[str]]
) -> list[EventCluster]:
    natural = [
        item for item in records if item.content_nature is ContentNature.NATURAL
    ]
    parents = list(range(len(natural)))

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parents[right_root] = left_root

    for left in range(len(natural)):
        for right in range(left + 1, len(natural)):
            similarity = _similarity(
                natural[left].title, natural[right].title, aliases
            )
            if similarity >= _MATCH_THRESHOLD:
                union(left, right)

    grouped: dict[int, list[HotspotRecord]] = defaultdict(list)
    for index, item in enumerate(natural):
        grouped[find(index)].append(item)

    clusters: list[EventCluster] = []
    for members in grouped.values():
        titles = sorted({item.title for item in members})
        pair_scores = [
            _similarity(members[left].title, members[right].title, aliases)
            for left in range(len(members))
            for right in range(left + 1, len(members))
        ]
        confidence = min(pair_scores, default=1.0)
        event_key = _event_key(members, aliases)
        clusters.append(
            EventCluster(
                event_id=hashlib.sha256(event_key.encode("utf-8")).hexdigest()[:16],
                representative_title=min(
                    members, key=lambda item: (item.rank, len(item.title), item.title)
                ).title,
                aliases=titles,
                record_ids=sorted(item.record_id for item in members),
                platforms={item.platform for item in members},
                first_seen_at=min(item.captured_at for item in members),
                last_seen_at=max(item.captured_at for item in members),
                cluster_confidence=round(confidence, 4),
                needs_manual_review=confidence < _REVIEW_THRESHOLD,
            )
        )
    return sorted(clusters, key=lambda item: item.event_id)
```

The alias key is the durable identity when every member shares a configured canonical entity. Otherwise the first-observed record is the deterministic anchor, so adding later snapshots does not rename an event. Never use Python's process-randomized `hash()`. A cluster with confidence from `0.58` through `<0.68` is provisional only: it may be displayed for human review, but Task 6's `cluster_review` verification check prevents it from passing hard gates or scoring until `cluster_review_approved=True`. Records below `0.58` remain separate events.

- [ ] **Step 4: Run cluster tests**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_event_clusterer.py -v`

Expected: PASS.

- [ ] **Step 5: Commit clustering**

```bash
git add src/avatar_pipeline/event_clusterer.py tests/test_event_clusterer.py
git commit -m "feat: cluster cross-platform hotspot events"
```

### Task 5: Calculate persistence and within-platform trend without inventing zeroes

**Files:**
- Create: `src/avatar_pipeline/trend_analyzer.py`
- Create: `tests/test_trend_analyzer.py`

**Interfaces:**
- Consumes: `EventCluster`, chronological `Sequence[HotspotSnapshot]`, the cluster's `record_ids`, and optional audited `related_subtopic_ids: Sequence[str]` from candidate review.
- Produces: `analyze_event_trend(cluster: EventCluster, snapshots: Sequence[HotspotSnapshot], *, related_subtopic_ids: Sequence[str] = ()) -> EventTrend` with per-platform `surging/rising/stable/falling/unknown` labels and one event-level aggregate label.

- [ ] **Step 1: Write failing tests for single-snapshot wording, platform labels, weighted event trend, subtopic diffusion, and failed-platform handling**

```python
# tests/test_trend_analyzer.py
from avatar_pipeline.hotspot_models import (
    CollectionStatus,
    HotspotFailure,
    PlatformTrendLabel,
    TrendLabel,
)
from avatar_pipeline.trend_analyzer import analyze_event_trend
from tests.hotspot_factories import cluster, record, snapshot


def test_one_observation_is_initial_screen_and_platform_unknown():
    item = record("w0", "weibo", 5, "白海豚路径变化", heat_value=100)
    result = analyze_event_trend(
        cluster([item]),
        [snapshot("t0", "2026-08-10T19:40:00+08:00", records=[item])],
    )
    assert result.label is TrendLabel.INITIAL_SCREEN
    assert result.platform_trend_labels == {
        "weibo": PlatformTrendLabel.UNKNOWN,
    }
    assert result.consecutive_snapshot_count == 1
    assert result.rank_delta_by_platform == {}
    assert result.heat_growth_by_platform == {}


def test_three_snapshots_measure_only_within_platform_changes_and_subtopics():
    t0_records = [
        record("w0", "weibo", 5, "白海豚路径变化", heat_value=100),
        record("b0", "baidu", 9, "白海豚路径变化", heat_value=1_000),
    ]
    t1_records = [
        record("w1", "weibo", 3, "白海豚路径变化", heat_value=150),
        record("b1", "baidu", 7, "白海豚路径变化", heat_value=900),
        record("z1", "zhihu", 10, "白海豚路径变化", heat_value=20_000),
    ]
    t2_records = [
        record("w2", "weibo", 1, "白海豚路径变化", heat_value=200),
        record("b2", "baidu", 8, "白海豚路径变化", heat_value=1_100),
        record("z2", "zhihu", 4, "白海豚路径变化", heat_value=25_000),
    ]
    all_records = t0_records + t1_records + t2_records
    result = analyze_event_trend(
        cluster(all_records),
        [
            snapshot("t0", "2026-08-10T19:40:00+08:00", records=t0_records),
            snapshot("t1", "2026-08-10T19:50:00+08:00", records=t1_records),
            snapshot("t2", "2026-08-10T20:00:00+08:00", records=t2_records),
        ],
        related_subtopic_ids=["路径影响", "停航影响", "路径影响"],
    )
    assert result.consecutive_snapshot_count == 3
    assert result.new_platform_count == 1
    assert result.related_subtopic_count == 2
    assert result.rank_delta_by_platform == {"baidu": 1, "weibo": 4, "zhihu": 6}
    assert result.heat_growth_by_platform == {"baidu": 0.1, "weibo": 1.0, "zhihu": 0.25}
    assert result.platform_trend_labels == {
        "baidu": PlatformTrendLabel.RISING,
        "weibo": PlatformTrendLabel.SURGING,
        "zhihu": PlatformTrendLabel.SURGING,
    }
    assert result.label is TrendLabel.SURGING


def test_failed_platform_is_omitted_instead_of_becoming_zero_heat():
    first = record("w0", "weibo", 2, "事件", heat_value=100)
    second = record("w1", "weibo", 2, "事件", heat_value=100)
    failure = HotspotFailure(
        platform="baidu",
        captured_at=first.captured_at,
        reason="login required",
        raw_snapshot_path="tmp/baidu.json",
        status=CollectionStatus.RESTRICTED,
    )
    result = analyze_event_trend(
        cluster([first, second]),
        [
            snapshot("t0", "2026-08-10T19:40:00+08:00", records=[first]),
            snapshot(
                "t1", "2026-08-10T19:50:00+08:00", records=[second], failures=[failure]
            ),
        ],
    )
    assert "baidu" not in result.platform_trend_labels
    assert "baidu" not in result.rank_delta_by_platform
    assert "baidu" not in result.heat_growth_by_platform
    assert result.platform_trend_labels["weibo"] is PlatformTrendLabel.STABLE
    assert result.label is TrendLabel.STABLE


def test_mixed_platform_directions_are_volatile():
    t0_records = [
        record("w0", "weibo", 8, "事件", heat_value=100),
        record("b0", "baidu", 1, "事件", heat_value=200),
    ]
    t1_records = [
        record("w1", "weibo", 2, "事件", heat_value=180),
        record("b1", "baidu", 7, "事件", heat_value=100),
    ]
    result = analyze_event_trend(
        cluster(t0_records + t1_records),
        [
            snapshot("t0", "2026-08-10T19:40:00+08:00", records=t0_records),
            snapshot("t1", "2026-08-10T19:50:00+08:00", records=t1_records),
        ],
    )
    assert result.platform_trend_labels == {
        "baidu": PlatformTrendLabel.FALLING,
        "weibo": PlatformTrendLabel.SURGING,
    }
    assert result.label is TrendLabel.VOLATILE


def test_two_snapshots_can_report_a_falling_event():
    first = record("w0", "weibo", 1, "事件", heat_value=200)
    second = record("w1", "weibo", 5, "事件", heat_value=100)
    result = analyze_event_trend(
        cluster([first, second]),
        [
            snapshot("t0", "2026-08-10T19:40:00+08:00", records=[first]),
            snapshot("t1", "2026-08-10T19:50:00+08:00", records=[second]),
        ],
    )
    assert result.rank_delta_by_platform == {"weibo": -4}
    assert result.heat_growth_by_platform == {"weibo": -0.5}
    assert result.platform_trend_labels["weibo"] is PlatformTrendLabel.FALLING
    assert result.label is TrendLabel.FALLING
```

- [ ] **Step 2: Run the focused test and verify the missing analyzer failure**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_trend_analyzer.py -v`

Expected: FAIL because `avatar_pipeline.trend_analyzer` does not exist.

- [ ] **Step 3: Implement chronological observations and explicit platform/event trend rules**

Create `src/avatar_pipeline/trend_analyzer.py`:

```python
"""Time-series analysis that never compares heat values across platforms."""

from collections.abc import Sequence

from avatar_pipeline.hotspot_models import (
    EventCluster,
    EventTrend,
    HotspotSnapshot,
    PlatformTrendLabel,
    TrendLabel,
    TrendObservation,
)


def _longest_consecutive_presence(presence: list[bool]) -> int:
    longest = current = 0
    for present in presence:
        current = current + 1 if present else 0
        longest = max(longest, current)
    return longest


def _platform_label(
    *, observation_count: int, rank_delta: int | None, heat_growth: float | None
) -> PlatformTrendLabel:
    if observation_count < 2:
        return PlatformTrendLabel.UNKNOWN
    movements = [value for value in (rank_delta, heat_growth) if value is not None]
    if (rank_delta is not None and rank_delta >= 5) or (
        heat_growth is not None and heat_growth >= 0.5
    ):
        return PlatformTrendLabel.SURGING
    if any(value > 0 for value in movements):
        return PlatformTrendLabel.RISING
    if any(value < 0 for value in movements):
        return PlatformTrendLabel.FALLING
    return PlatformTrendLabel.STABLE


def _event_label(
    *,
    observation_count: int,
    platform_labels: dict[str, PlatformTrendLabel],
    observation_count_by_platform: dict[str, int],
    new_platform_count: int,
) -> TrendLabel:
    if observation_count == 1:
        return TrendLabel.INITIAL_SCREEN
    points = {
        PlatformTrendLabel.SURGING: 2.0,
        PlatformTrendLabel.RISING: 1.0,
        PlatformTrendLabel.STABLE: 0.0,
        PlatformTrendLabel.FALLING: -1.0,
        PlatformTrendLabel.UNKNOWN: 0.0,
    }
    known = {
        platform: label
        for platform, label in platform_labels.items()
        if label is not PlatformTrendLabel.UNKNOWN
    }
    has_positive = any(points[label] > 0 for label in known.values()) or new_platform_count > 0
    has_negative = any(points[label] < 0 for label in known.values())
    if has_positive and has_negative:
        return TrendLabel.VOLATILE
    total_weight = sum(observation_count_by_platform[item] for item in known)
    weighted = (
        sum(
            points[label] * observation_count_by_platform[platform]
            for platform, label in known.items()
        )
        / total_weight
        if total_weight
        else 0.0
    )
    if new_platform_count > 0:
        weighted += min(0.5, 0.25 * new_platform_count)
    if weighted >= 1.5:
        return TrendLabel.SURGING
    if weighted > 0:
        return TrendLabel.RISING
    if weighted < 0:
        return TrendLabel.FALLING
    return TrendLabel.STABLE


def analyze_event_trend(
    cluster: EventCluster,
    snapshots: Sequence[HotspotSnapshot],
    *,
    related_subtopic_ids: Sequence[str] = (),
) -> EventTrend:
    member_ids = set(cluster.record_ids)
    ordered = sorted(snapshots, key=lambda item: item.captured_at)
    observations: list[TrendObservation] = []
    presence: list[bool] = []
    for item in ordered:
        members = [record for record in item.records if record.record_id in member_ids]
        presence.append(bool(members))
        if not members:
            continue
        best_by_platform = {}
        for record in members:
            previous = best_by_platform.get(record.platform)
            if previous is None or record.rank < previous.rank:
                best_by_platform[record.platform] = record
        observations.append(
            TrendObservation(
                snapshot_id=item.snapshot_id,
                captured_at=item.captured_at,
                platform_ranks={
                    platform: record.rank
                    for platform, record in sorted(best_by_platform.items())
                },
                platform_heat_values={
                    platform: record.heat_value
                    for platform, record in sorted(best_by_platform.items())
                    if record.heat_value is not None
                },
            )
        )
    if not observations:
        raise ValueError(f"event {cluster.event_id} is absent from all snapshots")

    first_seen: dict[str, tuple[int, float | None]] = {}
    last_seen: dict[str, tuple[int, float | None]] = {}
    observation_count_by_platform: dict[str, int] = {}
    for observation in observations:
        for platform, rank in observation.platform_ranks.items():
            heat = observation.platform_heat_values.get(platform)
            first_seen.setdefault(platform, (rank, heat))
            last_seen[platform] = (rank, heat)
            observation_count_by_platform[platform] = (
                observation_count_by_platform.get(platform, 0) + 1
            )

    rank_delta = {
        platform: first_seen[platform][0] - last_seen[platform][0]
        for platform in sorted(first_seen)
        if observation_count_by_platform[platform] >= 2
        and first_seen[platform][0] != last_seen[platform][0]
    }
    heat_growth = {}
    for platform in sorted(first_seen):
        first_heat, last_heat = first_seen[platform][1], last_seen[platform][1]
        if (
            observation_count_by_platform[platform] >= 2
            and first_heat is not None
            and first_heat > 0
            and last_heat is not None
        ):
            heat_growth[platform] = round((last_heat - first_heat) / first_heat, 4)

    platform_labels = {
        platform: _platform_label(
            observation_count=observation_count_by_platform[platform],
            rank_delta=rank_delta.get(platform),
            heat_growth=heat_growth.get(platform),
        )
        for platform in sorted(first_seen)
    }
    first_platforms = set(observations[0].platform_ranks)
    later_platforms = set().union(
        *(set(item.platform_ranks) for item in observations[1:])
    )
    new_platform_count = len(later_platforms - first_platforms)

    return EventTrend(
        event_id=cluster.event_id,
        observations=observations,
        label=_event_label(
            observation_count=len(observations),
            platform_labels=platform_labels,
            observation_count_by_platform=observation_count_by_platform,
            new_platform_count=new_platform_count,
        ),
        platform_trend_labels=platform_labels,
        consecutive_snapshot_count=max(1, _longest_consecutive_presence(presence)),
        new_platform_count=new_platform_count,
        related_subtopic_count=len({item.strip() for item in related_subtopic_ids if item.strip()}),
        rank_delta_by_platform=rank_delta,
        heat_growth_by_platform=heat_growth,
    )
```

`rank_delta_by_platform` is `first_rank - last_rank`, so a positive value means improvement. `heat_growth_by_platform` is calculated only between observations from the same platform. A platform observed once is `unknown`; a failed or missing platform creates no synthetic observation, label, or zero value. Related-subtopic IDs are explicit reviewed inputs rather than inferred from raw title count. The event label uses each platform's number of valid observations as its weight, adds a bounded new-platform signal, and returns `volatile` when reliable platforms move in opposite directions.

- [ ] **Step 4: Run tests and lint**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_trend_analyzer.py -v`

Expected: PASS.

Run: `.venv/bin/ruff check src/avatar_pipeline/trend_analyzer.py tests/test_trend_analyzer.py`

Expected: PASS with no diagnostics.

- [ ] **Step 5: Commit trend analysis**

```bash
git add src/avatar_pipeline/trend_analyzer.py tests/test_trend_analyzer.py
git commit -m "feat: analyze hotspot persistence and velocity"
```

### Task 6: Verify facts and enforce every non-negotiable gate

**Files:**
- Create: `src/avatar_pipeline/candidate_verifier.py`
- Create: `src/avatar_pipeline/virality_gate.py`
- Create: `tests/test_candidate_verifier.py`
- Create: `tests/test_virality_gate.py`

**Interfaces:**
- Consumes: `EventCluster`, `EventTrend`, event member records, saved `CandidateVerification`, `HotspotConfig`, and an explicit timezone-aware `as_of`.
- Produces: `verify_candidate(...) -> VerificationDecision` and `evaluate_virality_gate(...) -> GateDecision`.

- [ ] **Step 1: Write failing verification tests covering recency, independent sources, visuals, fact conflicts, harm, high-stakes risk, old-news rehash, and manual cluster review**

```python
# tests/test_candidate_verifier.py
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
    rejected = verify_candidate(low_confidence, verification(), as_of=AS_OF, max_age_hours=24)
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
        update={"visual_plan": evidence.visual_plan.model_copy(update={"assets": [], "has_usable_factual_visuals": False})}
    )
    decision = verify_candidate(cluster([item]), no_visual, as_of=AS_OF, max_age_hours=24)
    assert decision.checks["production_visuals"] is False
```

- [ ] **Step 2: Write failing hard-gate tests for platform count, ranking, persistence, and natural heat**

```python
# tests/test_virality_gate.py
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
                record("w", "weibo", 1, "事件", nature=ContentNature.COMMERCIAL_PROMOTION),
                record("b", "baidu", 2, "事件", nature=ContentNature.COMMERCIAL_PROMOTION),
                record("z", "zhihu", 3, "事件", nature=ContentNature.COMMERCIAL_PROMOTION),
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
```

- [ ] **Step 3: Run tests and verify both modules are missing**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_candidate_verifier.py tests/test_virality_gate.py -v`

Expected: FAIL because `candidate_verifier` and `virality_gate` do not exist.

- [ ] **Step 4: Implement deterministic candidate verification**

Create `src/avatar_pipeline/candidate_verifier.py`:

```python
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
        evidence.visual_plan.ai_demo_available and bool(evidence.visual_plan.ai_disclosure)
    )
    checks = {
        "within_24_hours": age_hours <= max_age_hours,
        "two_independent_reliable_sources": len(reliable_origins) >= 2,
        "production_visuals": visuals_ok,
        "not_old_news_rehash": not evidence.old_news_rehash,
        "no_major_fact_conflict": not evidence.major_fact_conflict,
        "no_exploitative_harm": not evidence.exploitative_harm,
        "no_unresolved_high_stakes_claim": not evidence.high_stakes_unresolved,
        "cluster_review": not cluster.needs_manual_review or evidence.cluster_review_approved,
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
```

The positive `checks` names remain stable for gate composition, while `reasons` use direct editorial rejection language such as `old_news_rehash` and `major_fact_conflict`.

- [ ] **Step 5: Implement the seven named hard gates**

Create `src/avatar_pipeline/virality_gate.py`:

```python
"""Non-negotiable eligibility gates applied before virality scoring."""

from collections.abc import Sequence

from avatar_pipeline.config import HotspotConfig
from avatar_pipeline.hotspot_models import (
    ContentNature,
    EventCluster,
    EventTrend,
    GateDecision,
    HotspotRecord,
    VerificationDecision,
)


def evaluate_virality_gate(
    cluster: EventCluster,
    trend: EventTrend,
    records: Sequence[HotspotRecord],
    verification: VerificationDecision,
    config: HotspotConfig,
) -> GateDecision:
    members = [item for item in records if item.record_id in set(cluster.record_ids)]
    platforms = {item.platform for item in members if item.content_nature is ContentNature.NATURAL}
    best_rank_by_platform = {
        platform: min(item.rank for item in members if item.platform == platform)
        for platform in platforms
    }
    has_top_five = any(rank <= config.top_rank_single for rank in best_rank_by_platform.values())
    top_ten_count = sum(
        rank <= config.top_rank_multi for rank in best_rank_by_platform.values()
    )
    checks = {
        "three_independent_platforms": len(platforms) >= config.min_platforms,
        "core_rank": has_top_five or top_ten_count >= config.min_top_rank_multi_platforms,
        "within_24_hours": verification.checks.get("within_24_hours", False),
        "two_consecutive_snapshots": (
            trend.consecutive_snapshot_count >= config.min_consecutive_snapshots
        ),
        "natural_heat": bool(members) and all(
            item.content_nature is ContentNature.NATURAL for item in members
        ),
        "two_independent_reliable_sources": verification.checks.get(
            "two_independent_reliable_sources", False
        ),
        "production_visuals": verification.checks.get("production_visuals", False),
    }
    reasons = [name for name, passed in checks.items() if not passed]
    reasons.extend(reason for reason in verification.reasons if reason not in reasons)
    return GateDecision(
        event_id=cluster.event_id,
        passed=not reasons,
        checks=checks,
        reasons=reasons,
    )
```

The gate intentionally carries verifier-only rejection reasons such as `major_fact_conflict` and `cluster_review_required` in `reasons`, while `checks` remains exactly the seven confirmed hard gates. Task 4 normally excludes non-natural records before clusters are built; `natural_heat` deliberately rechecks every member as defense against manually constructed clusters, migrated data, or repository pollution.

- [ ] **Step 6: Run focused tests and lint**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_candidate_verifier.py tests/test_virality_gate.py -v`

Expected: PASS.

Run: `.venv/bin/ruff check src/avatar_pipeline/candidate_verifier.py src/avatar_pipeline/virality_gate.py tests/test_candidate_verifier.py tests/test_virality_gate.py`

Expected: PASS with no diagnostics.

- [ ] **Step 7: Commit verification and gates**

```bash
git add src/avatar_pipeline/candidate_verifier.py src/avatar_pipeline/virality_gate.py tests/test_candidate_verifier.py tests/test_virality_gate.py
git commit -m "feat: enforce viral hotspot eligibility gates"
```

### Task 7: Calculate a versioned and reproducible 100-point virality score

**Files:**
- Create: `src/avatar_pipeline/virality_scorer.py`
- Create: `tests/test_virality_scorer.py`

**Interfaces:**
- Consumes: a passed `GateDecision`, `EventCluster`, `EventTrend`, event member records, `CandidateVerification`, `VerificationDecision`, `EditorialSignals`, and `HotspotConfig`.
- Produces: `score_virality(...) -> ViralityScore`; the output stores `config.rule_version` and every weighted component.

- [ ] **Step 1: Write failing tests for exact weights, deterministic replay, and gate-before-score ordering**

```python
# tests/test_virality_scorer.py
from datetime import datetime

import pytest

from avatar_pipeline.candidate_verifier import verify_candidate
from avatar_pipeline.config import load_config
from avatar_pipeline.virality_gate import evaluate_virality_gate
from avatar_pipeline.virality_scorer import score_virality
from tests.hotspot_factories import cluster, editorial_signals, record, trend, verification

CONFIG = load_config("configs/default.yaml").hotspot
AS_OF = datetime.fromisoformat("2026-08-10T20:00:00+08:00")


def _inputs():
    records = [
        record("w", "weibo", 1, "事件"),
        record("b", "baidu", 4, "事件"),
        record("z", "zhihu", 8, "事件"),
        record("k", "kuaishou", 9, "事件"),
    ]
    event = cluster(records)
    event_trend = trend()
    evidence = verification()
    verified = verify_candidate(event, evidence, as_of=AS_OF, max_age_hours=24)
    gate = evaluate_virality_gate(event, event_trend, records, verified, CONFIG)
    return records, event, event_trend, evidence, verified, gate


def test_score_uses_exact_confirmed_weights_and_is_replayable():
    records, event, event_trend, evidence, verified, gate = _inputs()
    first = score_virality(
        event, event_trend, records, evidence, verified, editorial_signals(), gate, CONFIG
    )
    second = score_virality(
        event, event_trend, records, evidence, verified, editorial_signals(), gate, CONFIG
    )
    assert first == second
    assert first.rule_version == "viral-v1.0"
    assert first.cross_platform_resonance == 25
    assert first.trend_velocity == 14.5
    assert first.conflict_suspense == 13.5
    assert first.public_interest == 9
    assert first.curiosity_gap == 9
    assert first.visual_impact == 8
    assert first.explanatory_depth == 4
    assert first.fact_safety == 5
    assert first.total == 88


def test_audited_subtopic_diffusion_contributes_inside_the_20_point_cap():
    records, event, event_trend, evidence, verified, gate = _inputs()
    baseline = score_virality(
        event, event_trend, records, evidence, verified, editorial_signals(), gate, CONFIG
    )
    expanded = score_virality(
        event,
        event_trend.model_copy(update={"related_subtopic_count": 2}),
        records,
        evidence,
        verified,
        editorial_signals(),
        gate,
        CONFIG,
    )
    assert expanded.trend_velocity == baseline.trend_velocity + 2
    assert expanded.trend_velocity <= 20


def test_score_refuses_an_event_that_failed_a_hard_gate():
    records, event, event_trend, evidence, verified, gate = _inputs()
    rejected = gate.model_copy(update={"passed": False, "reasons": ["forced"]})
    with pytest.raises(ValueError, match="hard gates"):
        score_virality(
            event,
            event_trend,
            records,
            evidence,
            verified,
            editorial_signals(),
            rejected,
            CONFIG,
        )
```

- [ ] **Step 2: Run the test and verify the missing scorer failure**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_virality_scorer.py -v`

Expected: FAIL because `avatar_pipeline.virality_scorer` does not exist.

- [ ] **Step 3: Implement the exact component formulas and rule-version capture**

Create `src/avatar_pipeline/virality_scorer.py`:

```python
"""Versioned virality scoring derived only from saved evidence and editorial inputs."""

from collections.abc import Sequence

from avatar_pipeline.config import HotspotConfig
from avatar_pipeline.hotspot_models import (
    CandidateVerification,
    EditorialSignals,
    EventCluster,
    EventTrend,
    GateDecision,
    HotspotRecord,
    VerificationDecision,
    ViralityScore,
)


def _cross_platform_score(
    cluster: EventCluster,
    records: Sequence[HotspotRecord],
    config: HotspotConfig,
) -> float:
    member_ids = set(cluster.record_ids)
    members = [item for item in records if item.record_id in member_ids]
    best_ranks = {}
    for item in members:
        best_ranks[item.platform] = min(best_ranks.get(item.platform, item.rank), item.rank)
    platform_points = min(13.0, 7.0 + 2.0 * len(best_ranks))
    categories = {
        config.platform_categories.get(platform, f"unknown:{platform}")
        for platform in best_ranks
    }
    diversity_points = min(2.0, max(0.0, float(len(categories) - 1)))
    best_rank = min(best_ranks.values())
    rank_points = 6.0 if best_rank == 1 else 5.0 if best_rank <= 5 else 3.0
    top_ten_points = min(
        4.0,
        2.0 * max(0, sum(rank <= 10 for rank in best_ranks.values()) - 1),
    )
    return min(
        25.0,
        platform_points + diversity_points + rank_points + top_ten_points,
    )


def _trend_score(trend: EventTrend) -> float:
    persistence = min(6.0, 2.0 * trend.consecutive_snapshot_count)
    new_platforms = min(4.0, 2.0 * trend.new_platform_count)
    rank_improvement = min(5.0, max([0, *trend.rank_delta_by_platform.values()]))
    best_same_platform_growth = max([0.0, *trend.heat_growth_by_platform.values()])
    heat_growth = min(5.0, 5.0 * best_same_platform_growth)
    subtopic_diffusion = min(2.0, float(trend.related_subtopic_count))
    return min(
        20.0,
        persistence
        + new_platforms
        + rank_improvement
        + heat_growth
        + subtopic_diffusion,
    )


def _fact_safety_score(
    evidence: CandidateVerification, verification: VerificationDecision
) -> float:
    source_points = 3.0 if verification.independent_reliable_source_count >= 2 else 0.0
    primary_points = 1.0 if evidence.primary_source_ids else 0.0
    resolved_points = 1.0 if not evidence.unresolved_claims else 0.0
    return min(5.0, source_points + primary_points + resolved_points)


def score_virality(
    cluster: EventCluster,
    trend: EventTrend,
    records: Sequence[HotspotRecord],
    evidence: CandidateVerification,
    verification: VerificationDecision,
    editorial: EditorialSignals,
    gate: GateDecision,
    config: HotspotConfig,
) -> ViralityScore:
    ids = {cluster.event_id, trend.event_id, evidence.event_id, verification.event_id,
           editorial.event_id, gate.event_id}
    if len(ids) != 1:
        raise ValueError("all score inputs must describe the same event_id")
    if not gate.passed:
        raise ValueError("virality score requires all hard gates to pass")
    components = {
        "cross_platform_resonance": _cross_platform_score(cluster, records, config),
        "trend_velocity": _trend_score(trend),
        "conflict_suspense": editorial.conflict_suspense * 15,
        "public_interest": editorial.public_interest * 10,
        "curiosity_gap": editorial.curiosity_gap * 10,
        "visual_impact": editorial.visual_impact * 10,
        "explanatory_depth": editorial.explanatory_depth * 5,
        "fact_safety": _fact_safety_score(evidence, verification),
    }
    rounded = {name: round(value, 2) for name, value in components.items()}
    return ViralityScore(
        event_id=cluster.event_id,
        rule_version=config.rule_version,
        **rounded,
        total=round(sum(rounded.values()), 2),
    )
```

This implementation combines ranks and already-normalized component points, never raw heat totals. The 25-point resonance component explicitly includes independent platform count, configured platform-type diversity, best rank, and multi-platform Top 10 depth. Heat contributes only through the best same-platform relative growth observed across snapshots. Audited related-subtopic diffusion contributes at most two points inside the existing 20-point trend component; the component remains capped at 20.

- [ ] **Step 4: Run focused tests and lint**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_virality_scorer.py -v`

Expected: PASS.

Run: `.venv/bin/ruff check src/avatar_pipeline/virality_scorer.py tests/test_virality_scorer.py`

Expected: PASS with no diagnostics.

- [ ] **Step 5: Commit versioned scoring**

```bash
git add src/avatar_pipeline/virality_scorer.py tests/test_virality_scorer.py
git commit -m "feat: score verified hotspot virality"
```

### Task 8: Build the maximum-three report and orchestration service

**Files:**
- Create: `src/avatar_pipeline/hotspot_report.py`
- Create: `src/avatar_pipeline/hotspot_service.py`
- Create: `tests/test_hotspot_report.py`
- Create: `tests/test_hotspot_service.py`
- Modify: `src/avatar_pipeline/hotspot_repository.py`
- Modify: `tests/test_hotspot_repository.py`

**Interfaces:**
- Consumes: stored snapshots, verifications, editorial signals, `HotspotConfig`, and pure Tasks 4–7 functions.
- Produces: `build_hotspot_report(...) -> HotspotReport`, `render_hotspot_markdown(report) -> str`, `HotspotService.build_report(day) -> HotspotReport`, and `HotspotRepository.load_report(day) -> HotspotReport`.

- [ ] **Step 1: Write failing report-selection tests**

```python
# tests/test_hotspot_report.py
from datetime import date

from avatar_pipeline.hotspot_models import (
    EvaluatedHotspot,
    GateDecision,
    ViralityScore,
)
from avatar_pipeline.hotspot_report import build_hotspot_report, render_hotspot_markdown
from tests.hotspot_factories import cluster, editorial_signals, record, trend, verification


def _score(event_id, total):
    capacities = [25, 20, 15, 10, 10, 10, 5, 5]
    remaining = float(total)
    values = []
    for capacity in capacities:
        value = min(remaining, capacity)
        values.append(value)
        remaining -= value
    return ViralityScore(
        event_id=event_id,
        rule_version="viral-v1.0",
        cross_platform_resonance=values[0],
        trend_velocity=values[1],
        conflict_suspense=values[2],
        public_interest=values[3],
        curiosity_gap=values[4],
        visual_impact=values[5],
        explanatory_depth=values[6],
        fact_safety=values[7],
        total=total,
    )


def _evaluated(event_id, total, *, passed=True):
    records = [record(f"{event_id}-w", "weibo", 1, event_id)]
    return EvaluatedHotspot(
        cluster=cluster(records, event_id=event_id),
        trend=trend(event_id=event_id),
        gate=GateDecision(event_id=event_id, passed=passed, checks={}, reasons=[]),
        score=_score(event_id, total) if passed else None,
        verification=verification(event_id=event_id),
        editorial_signals=editorial_signals(event_id=event_id),
    )


def test_report_keeps_only_passing_scores_at_least_75_and_caps_three():
    report = build_hotspot_report(
        day=date(2026, 8, 10),
        rule_version="viral-v1.0",
        snapshot_ids=["t0", "t1", "t2"],
        failures=[],
        evaluations=[
            _evaluated("e1", 86),
            _evaluated("e2", 84),
            _evaluated("e3", 79),
            _evaluated("e4", 78),
            _evaluated("low", 74),
            _evaluated("rejected", 99, passed=False),
        ],
        display_score_min=75,
        strong_score_min=80,
        director_score_min=85,
        max_candidates=3,
    )
    assert [item.event_id for item in report.candidates] == ["e1", "e2", "e3"]
    assert report.director_recommendation_event_id == "e1"
    assert [item.score_band.value for item in report.candidates] == [
        "director_first", "strong_candidate", "backup"
    ]
    assert report.outcome == "qualified_candidates"
    assert "全网最热" not in render_hotspot_markdown(report)
    assert "本轮跨平台综合评分第一" in render_hotspot_markdown(report)


def test_best_84_point_candidate_is_still_recommended_without_director_first_band():
    report = build_hotspot_report(
        day=date(2026, 8, 10),
        rule_version="viral-v1.0",
        snapshot_ids=["t0", "t1", "t2"],
        failures=[],
        evaluations=[_evaluated("best", 84), _evaluated("second", 81)],
        display_score_min=75,
        strong_score_min=80,
        director_score_min=85,
        max_candidates=3,
    )
    assert report.director_recommendation_event_id == "best"
    assert report.candidates[0].score_band.value == "strong_candidate"
    assert report.candidates[0].director_action.value == "watch"


def test_no_qualified_event_returns_explicit_safe_stop_outcome():
    report = build_hotspot_report(
        day=date(2026, 8, 10),
        rule_version="viral-v1.0",
        snapshot_ids=["t0"],
        failures=[],
        evaluations=[_evaluated("low", 74)],
        display_score_min=75,
        strong_score_min=80,
        director_score_min=85,
        max_candidates=3,
    )
    assert report.candidates == []
    assert report.director_recommendation_event_id is None
    assert report.outcome == "no_qualified_hotspot"
```

- [ ] **Step 2: Write a failing service test for transparent failures and missing review inputs**

```python
# tests/test_hotspot_service.py
from datetime import date

from avatar_pipeline.config import load_config
from avatar_pipeline.hotspot_models import CollectionStatus, HotspotFailure
from avatar_pipeline.hotspot_repository import HotspotRepository
from avatar_pipeline.hotspot_service import HotspotService
from tests.hotspot_factories import record, snapshot


def test_service_rejects_unreviewed_event_and_preserves_collection_failure(tmp_path):
    day = date(2026, 8, 10)
    repository = HotspotRepository(tmp_path)
    records = [
        record("w0", "weibo", 1, "同一事件"),
        record("b0", "baidu", 2, "同一事件"),
        record("z0", "zhihu", 3, "同一事件"),
    ]
    failure = HotspotFailure(
        platform="bilibili",
        captured_at=records[0].captured_at,
        reason="api returned -352",
        raw_snapshot_path="tmp/bilibili.json",
        status=CollectionStatus.RESTRICTED,
    )
    repository.save_snapshot(
        day, snapshot("t0", "2026-08-10T19:40:00+08:00", records=records, failures=[failure])
    )
    service = HotspotService(repository, load_config("configs/default.yaml").hotspot)
    report = service.build_report(day)
    assert report.outcome == "no_qualified_hotspot"
    assert report.collection_failures[0].reason == "api returned -352"
    assert any("missing_verification" in item.reasons for item in report.rejected_events)
```

- [ ] **Step 3: Run tests and verify report/service APIs are missing**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_hotspot_report.py tests/test_hotspot_service.py -v`

Expected: FAIL because the report and service modules do not exist.

- [ ] **Step 4: Implement candidate conversion, sorting, recommendation, rejection, and Markdown rendering**

Create `src/avatar_pipeline/hotspot_report.py` with these public functions and helpers:

```python
from collections.abc import Sequence
from datetime import date

from avatar_pipeline.hotspot_models import (
    DirectorAction,
    EvaluatedHotspot,
    HotspotCandidateReport,
    HotspotFailure,
    HotspotRejectedEvent,
    HotspotReport,
    ViralityBand,
)


def _platform_evidence(item: EvaluatedHotspot) -> list[str]:
    evidence = []
    for observation in item.trend.observations:
        for platform, rank in sorted(observation.platform_ranks.items()):
            heat = observation.platform_heat_values.get(platform)
            heat_text = f", heat={heat:g}" if heat is not None else ""
            evidence.append(
                f"{observation.captured_at.isoformat()} {platform} rank={rank}{heat_text}"
            )
    return evidence


def _candidate(
    item: EvaluatedHotspot,
    *,
    strong_score_min: int,
    director_score_min: int,
) -> HotspotCandidateReport:
    assert item.score is not None
    assert item.verification is not None
    assert item.editorial_signals is not None
    editorial = item.editorial_signals
    verification = item.verification
    return HotspotCandidateReport(
        event_id=item.cluster.event_id,
        representative_title=item.cluster.representative_title,
        click_title=editorial.click_title,
        collected_from=item.cluster.first_seen_at,
        collected_to=item.cluster.last_seen_at,
        platform_evidence=_platform_evidence(item),
        trend_label=item.trend.label,
        platform_trend_labels=item.trend.platform_trend_labels,
        related_subtopic_count=item.trend.related_subtopic_count,
        score=item.score,
        score_band=(
            ViralityBand.DIRECTOR_FIRST
            if item.score.total >= director_score_min
            else ViralityBand.STRONG_CANDIDATE
            if item.score.total >= strong_score_min
            else ViralityBand.BACKUP
        ),
        why_click=editorial.why_click,
        opening_hook=editorial.opening_hook,
        audience_relevance=editorial.audience_relevance,
        visual_assets=verification.visual_plan.assets,
        copyright_notes=verification.visual_plan.copyright_notes,
        expected_lifetime=editorial.expected_lifetime,
        risks=[*verification.unresolved_claims, *item.gate.reasons],
        wording_to_avoid=verification.wording_to_avoid,
        director_action=(
            DirectorAction.DO_NOW
            if item.score.total >= director_score_min
            else DirectorAction.WATCH
        ),
        pillar=editorial.pillar,
        source_evidence=verification.sources,
        verification_summary=verification.core_fact,
    )


def build_hotspot_report(
    *,
    day: date,
    rule_version: str,
    snapshot_ids: list[str],
    failures: list[HotspotFailure],
    evaluations: Sequence[EvaluatedHotspot],
    display_score_min: int,
    strong_score_min: int,
    director_score_min: int,
    max_candidates: int,
) -> HotspotReport:
    eligible = [
        item for item in evaluations
        if item.gate.passed
        and item.score is not None
        and item.score.total >= display_score_min
        and item.verification is not None
        and item.editorial_signals is not None
    ]
    eligible.sort(key=lambda item: (-item.score.total, item.cluster.event_id))
    candidates = [
        _candidate(
            item,
            strong_score_min=strong_score_min,
            director_score_min=director_score_min,
        )
        for item in eligible[:max_candidates]
    ]
    recommendation = candidates[0].event_id if candidates else None
    rejected = [
        HotspotRejectedEvent(
            event_id=item.cluster.event_id,
            representative_title=item.cluster.representative_title,
            reasons=(
                item.gate.reasons
                if not item.gate.passed
                else [f"score_below_{display_score_min}"]
                if item.score is None or item.score.total < display_score_min
                else [f"outside_top_{max_candidates}"]
            ),
        )
        for item in evaluations
        if item.cluster.event_id not in {candidate.event_id for candidate in candidates}
    ]
    return HotspotReport(
        day=day.isoformat(),
        rule_version=rule_version,
        snapshot_ids=snapshot_ids,
        collection_failures=failures,
        rejected_events=rejected,
        candidates=candidates,
        director_recommendation_event_id=recommendation,
        outcome="qualified_candidates" if candidates else "no_qualified_hotspot",
    )


def render_hotspot_markdown(report: HotspotReport) -> str:
    lines = [f"# {report.day} 跨平台热点候选", "", f"规则版本：{report.rule_version}", ""]
    if report.outcome == "no_qualified_hotspot":
        lines.extend(["## 结果", "", "今日暂无合格爆点，流程安全停止。", ""])
    for index, item in enumerate(report.candidates, start=1):
        badge = "（本轮跨平台综合评分第一）" if item.event_id == report.director_recommendation_event_id else ""
        lines.extend([
            f"## 候选{index}：{item.click_title}{badge}",
            "",
            f"- 采集区间：{item.collected_from.isoformat()} 至 {item.collected_to.isoformat()}",
            f"- 传播潜力：{item.score.total}/100（{item.score_band.value}）",
            "- 分项："
            f"跨平台{item.score.cross_platform_resonance}/25，"
            f"排名与增速{item.score.trend_velocity}/20，"
            f"冲突悬念{item.score.conflict_suspense}/15，"
            f"普通人利益{item.score.public_interest}/10，"
            f"认知缺口{item.score.curiosity_gap}/10，"
            f"视觉冲击{item.score.visual_impact}/10，"
            f"解释深度{item.score.explanatory_depth}/5，"
            f"事实安全{item.score.fact_safety}/5",
            f"- 趋势：{item.trend_label.value}",
            "- 各平台趋势：" + "；".join(
                f"{platform}={label.value}"
                for platform, label in sorted(item.platform_trend_labels.items())
            ),
            f"- 相关子话题扩散：{item.related_subtopic_count}",
            f"- 点击理由：{item.why_click}",
            f"- 开场钩子：{item.opening_hook}",
            f"- 普通人关联：{item.audience_relevance}",
            f"- 传播寿命：{item.expected_lifetime}",
            f"- 导演建议：{item.director_action.value}",
            f"- 平台证据：{'；'.join(item.platform_evidence)}",
            f"- 视觉素材：{'；'.join(item.visual_assets)}",
            f"- 版权边界：{'；'.join(item.copyright_notes) or '需在生产前确认'}",
            f"- 事实核验：{item.verification_summary}",
            f"- 禁用措辞：{'；'.join(item.wording_to_avoid) or '无新增禁用措辞'}",
            f"- 风险：{'；'.join(item.risks) or '无新增风险'}",
            "",
        ])
    if report.collection_failures:
        lines.extend(["## 采集失败与受限平台", ""])
        lines.extend(
            f"- {item.platform}：{item.reason}（{item.captured_at.isoformat()}）"
            for item in report.collection_failures
        )
    return "\n".join(lines).rstrip() + "\n"
```

- [ ] **Step 5: Add report loading to the repository**

Add `HotspotReport` to the existing `avatar_pipeline.hotspot_models` imports in `tests/test_hotspot_repository.py`, add this exact method to `HotspotRepository`, and extend the repository test with a save/load assertion:

```python
def load_report(self, day: date) -> HotspotReport:
    path = self._day_root(day) / "reports" / "candidate-report.json"
    return HotspotReport.model_validate_json(path.read_text(encoding="utf-8"))
```

```python
def test_repository_loads_the_saved_report(tmp_path):
    repository = HotspotRepository(tmp_path)
    report = HotspotReport(
        day="2026-08-10",
        rule_version="viral-v1.0",
        snapshot_ids=[],
        collection_failures=[],
        candidates=[],
        outcome="no_qualified_hotspot",
    )
    repository.save_report(date(2026, 8, 10), report, "# report\n")
    assert repository.load_report(date(2026, 8, 10)) == report
```

- [ ] **Step 6: Implement orchestration with explicit missing-input rejections**

Create `src/avatar_pipeline/hotspot_service.py`:

```python
"""Application service for deterministic hotspot evaluation and reporting."""

from datetime import date

from avatar_pipeline.candidate_verifier import verify_candidate
from avatar_pipeline.config import HotspotConfig
from avatar_pipeline.event_clusterer import cluster_events
from avatar_pipeline.hotspot_models import EvaluatedHotspot, GateDecision, HotspotReport
from avatar_pipeline.hotspot_report import build_hotspot_report, render_hotspot_markdown
from avatar_pipeline.hotspot_repository import HotspotRepository
from avatar_pipeline.trend_analyzer import analyze_event_trend
from avatar_pipeline.virality_gate import evaluate_virality_gate
from avatar_pipeline.virality_scorer import score_virality


class HotspotService:
    def __init__(self, repository: HotspotRepository, config: HotspotConfig) -> None:
        self.repository = repository
        self.config = config

    def build_report(self, day: date) -> HotspotReport:
        snapshots = self.repository.list_snapshots(day)
        if not snapshots:
            raise ValueError(f"no hotspot snapshots stored for {day.isoformat()}")
        records = [record for snapshot in snapshots for record in snapshot.records]
        failures = [failure for snapshot in snapshots for failure in snapshot.failures]
        verifications = self.repository.load_verifications(day, missing_ok=True)
        editorial_signals = self.repository.load_editorial_signals(day, missing_ok=True)
        evaluations = []
        for event in cluster_events(records, aliases=self.config.event_aliases):
            evidence = verifications.get(event.event_id)
            editorial = editorial_signals.get(event.event_id)
            event_trend = analyze_event_trend(
                event,
                snapshots,
                related_subtopic_ids=(evidence.related_subtopic_ids if evidence else ()),
            )
            missing = [
                name
                for name, value in (
                    ("missing_verification", evidence),
                    ("missing_editorial_signals", editorial),
                )
                if value is None
            ]
            if missing:
                evaluations.append(EvaluatedHotspot(
                    cluster=event,
                    trend=event_trend,
                    gate=GateDecision(
                        event_id=event.event_id,
                        passed=False,
                        checks={},
                        reasons=missing,
                    ),
                ))
                continue
            verified = verify_candidate(
                event,
                evidence,
                as_of=snapshots[-1].captured_at,
                max_age_hours=self.config.max_event_age_hours,
            )
            gate = evaluate_virality_gate(event, event_trend, records, verified, self.config)
            score = (
                score_virality(
                    event,
                    event_trend,
                    records,
                    evidence,
                    verified,
                    editorial,
                    gate,
                    self.config,
                )
                if gate.passed
                else None
            )
            evaluations.append(EvaluatedHotspot(
                cluster=event,
                trend=event_trend,
                gate=gate,
                score=score,
                verification=evidence,
                editorial_signals=editorial,
            ))
        report = build_hotspot_report(
            day=day,
            rule_version=self.config.rule_version,
            snapshot_ids=[item.snapshot_id for item in snapshots],
            failures=failures,
            evaluations=evaluations,
            display_score_min=self.config.display_score_min,
            strong_score_min=self.config.strong_score_min,
            director_score_min=self.config.director_score_min,
            max_candidates=self.config.max_candidates,
        )
        self.repository.save_report(day, report, render_hotspot_markdown(report))
        return report
```

Change repository loading signatures so absent review files return an empty map only when explicitly requested:

```python
def load_verifications(
    self, day: date, *, missing_ok: bool = False
) -> dict[str, CandidateVerification]:
    path = self._day_root(day) / "verification.json"
    if missing_ok and not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = [CandidateVerification.model_validate(item) for item in payload]
    return {item.event_id: item for item in items}


def load_editorial_signals(
    self, day: date, *, missing_ok: bool = False
) -> dict[str, EditorialSignals]:
    path = self._day_root(day) / "editorial-signals.json"
    if missing_ok and not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = [EditorialSignals.model_validate(item) for item in payload]
    return {item.event_id: item for item in items}
```

- [ ] **Step 7: Run report, service, and repository tests**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_hotspot_report.py tests/test_hotspot_service.py tests/test_hotspot_repository.py -v`

Expected: PASS.

Run: `.venv/bin/ruff check src/avatar_pipeline/hotspot_report.py src/avatar_pipeline/hotspot_service.py tests/test_hotspot_report.py tests/test_hotspot_service.py`

Expected: PASS with no diagnostics.

- [ ] **Step 8: Commit reporting and orchestration**

```bash
git add src/avatar_pipeline/hotspot_report.py src/avatar_pipeline/hotspot_service.py src/avatar_pipeline/hotspot_repository.py tests/test_hotspot_report.py tests/test_hotspot_service.py tests/test_hotspot_repository.py
git commit -m "feat: report top viral hotspot candidates"
```

### Task 9: Archive and safely refresh the unapproved production plan

**Files:**
- Create: `src/avatar_pipeline/workflow_refresh.py`
- Create: `tests/test_workflow_refresh.py`
- Modify: `src/avatar_pipeline/models.py:173-225`
- Modify: `src/avatar_pipeline/migration.py`
- Modify: `src/avatar_pipeline/service.py`
- Modify: `tests/test_models.py`
- Modify: `tests/test_service.py`
- Modify: `tests/test_repository.py`

**Interfaces:**
- Consumes: a saved qualified `HotspotReport` or `Sequence[TopicCandidate]`, an existing `DailyTask`, the audited confirmed `HostProfile`, and a nonblank archive reason.
- Produces: `topic_candidates_from_report(report: HotspotReport) -> list[TopicCandidate]`, `refresh_unapproved_task(task, *, candidates, archive_reason, confirmed_host) -> DailyTask`, and `DailyWorkflowService.refresh_unapproved_hotspots(day, candidates, archive_reason, confirmed_host) -> DailyTask`.

- [ ] **Step 1: Write failing model and migration tests for schema V3 archive history**

```python
# additions to tests/test_models.py
from avatar_pipeline.models import ArchivedTopicPlan, DailyTask, TaskStatus


def test_schema_v3_task_accepts_explicit_archived_plan_history():
    task = DailyTask(
        day=date(2026, 8, 10),
        status=TaskStatus.TOPIC_SCRIPT_REVIEW,
        archived_topic_plans=[
            ArchivedTopicPlan(
                reason="旧候选传播性不足",
                previous_status=TaskStatus.TOPIC_SCRIPT_REVIEW,
                candidates=[],
                skipped_candidates=[],
            )
        ],
    )
    assert task.schema_version == 3
    assert task.archived_topic_plans[0].reason == "旧候选传播性不足"
```

```python
# additions to tests/test_repository.py
import json


def test_repository_migrates_v2_to_v3_without_inventing_archive_or_approval(tmp_path):
    day = date(2026, 8, 10)
    path = tmp_path / "days" / day.isoformat() / "task.json"
    path.parent.mkdir(parents=True)
    payload = DailyTask(day=day).model_dump(mode="json")
    payload["schema_version"] = 2
    payload.pop("archived_topic_plans", None)
    path.write_text(json.dumps(payload), encoding="utf-8")
    loaded = DailyTaskRepository(tmp_path).get(day)
    assert loaded.schema_version == 3
    assert loaded.archived_topic_plans == []
    assert loaded.approvals == []
```

- [ ] **Step 2: Run model/repository tests and verify schema/archive failures**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_models.py tests/test_repository.py -v`

Expected: FAIL because `ArchivedTopicPlan` and schema V3 migration do not exist.

- [ ] **Step 3: Add the explicit archive model and schema V3 field**

Add `ArchivedTopicPlan` immediately before `DailyTask` in `src/avatar_pipeline/models.py`, change the schema default to `3`, and add the archive list:

```python
class ArchivedTopicPlan(DomainModel):
    reason: str = Field(min_length=1)
    previous_status: TaskStatus
    candidates: list[TopicCandidate] = Field(default_factory=list)
    skipped_candidates: list[TopicCandidate] = Field(default_factory=list)
    selected_topic_id: str | None = None
    news_script: NewsScript | None = None
    media_plan: MediaPlan | None = None
    archived_at: datetime = Field(default_factory=utc_now)


class DailyTask(DomainModel):
    schema_version: Literal[3] = 3
    # Keep every existing field in its existing order.
    archived_topic_plans: list[ArchivedTopicPlan] = Field(default_factory=list)
```

Place `archived_topic_plans` after `media_plan`. Do not move, rename, or remove any existing production fields.

- [ ] **Step 4: Replace migration with sequential V1→V2→V3 migration**

Refactor `src/avatar_pipeline/migration.py` so existing V1 behavior remains in `_migrate_v1_to_v2`, then add V3 without fabricating evidence:

```python
def _migrate_v1_to_v2(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result["schema_version"] = 2
    result["status"] = _STATUS_MAP.get(result.get("status", "created"), "input_received")
    result.setdefault("mode", "manual")
    result.setdefault("topic_source", "auto_hot")
    result.setdefault("avatar_source", "saved_host")
    result.setdefault("input_text", None)
    result.setdefault("candidates", [])
    result.setdefault("skipped_candidates", [])
    result.setdefault("selected_topic_id", None)
    result.setdefault("host_profile", None)
    result.setdefault("news_script", None)
    result.setdefault("media_plan", None)
    result.setdefault("subtitle_enabled", False)
    result.setdefault("video_structure", "studio_anchor_plus_vertical_news_insert")
    result.setdefault("media_policy", "reliable_original_first_ai_demo_fallback")
    result.setdefault("platforms", ["douyin", "wechat_channels", "xiaohongshu"])
    result.setdefault("approvals", [])
    result.setdefault("artifacts", [])
    result.setdefault("stop_reason", "legacy_task_not_verified")
    return result


def _migrate_v2_to_v3(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result["schema_version"] = 3
    result.setdefault("archived_topic_plans", [])
    return result


def migrate_task_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    version = int(result.get("schema_version", 1))
    if version < 2:
        result = _migrate_v1_to_v2(result)
        version = 2
    if version < 3:
        result = _migrate_v2_to_v3(result)
    return result
```

Migration must not add approvals, verification summaries, source evidence, or archive entries that were absent in the stored payload.

- [ ] **Step 5: Write failing refresh tests for state/approval protection, host preservation, archival, and no generation**

```python
# tests/test_workflow_refresh.py
from datetime import date

import pytest

from avatar_pipeline.hotspot_models import HotspotReport
from avatar_pipeline.models import (
    ApprovalRecord,
    ArtifactRecord,
    DailyTask,
    FactStatus,
    HostProfile,
    MediaKind,
    MediaPlan,
    MediaSegment,
    NewsPillarSlug,
    NewsScript,
    ScriptSegment,
    TaskStatus,
    TopicCandidate,
)
from avatar_pipeline.workflow_refresh import (
    refresh_unapproved_task,
    topic_candidates_from_report,
)


def _topic(topic_id):
    return TopicCandidate(
        id=topic_id,
        title=topic_id,
        pillar=NewsPillarSlug.SOCIAL_PHENOMENA,
        score=90,
        fact_status=FactStatus.VERIFIED,
        publishable=True,
    )


def _confirmed_host() -> HostProfile:
    return HostProfile(
        id="host-c2-pro-candidate-2-final",
        display_name="C2-Pro 新闻主持人",
        reference_image="output/host-v12-c2-pro/GPT-Image-2-Pro-C2-Pro-主持人最终选定.png",
        studio_reference="蓝色演播室、近景胸像、白衬衣、深藏青西装、无桌、避免手臂入镜",
        visual_style="知性亲和、专业克制、低AI感、五官清晰稳定",
        is_new=False,
        version=12,
    )


def test_refresh_archives_old_plan_reconciles_host_and_never_enters_generation():
    host = _confirmed_host()
    old = _topic("old")
    skipped = _topic("old-skipped")
    script = NewsScript(
        title="大学新生电脑涨价",
        spoken_segments=[
            ScriptSegment(
                id="s1",
                kind="fact",
                text="这是已经被否决但必须留档的旧脚本。",
                source_ids=["source-old"],
            )
        ],
        source_ids=["source-old"],
        target_duration_seconds=60,
    )
    media_plan = MediaPlan(
        duration_seconds=60,
        segments=[
            MediaSegment(
                id="m1",
                kind=MediaKind.ORIGINAL_NEWS,
                start_seconds=0,
                end_seconds=8,
                script_segment_id="s1",
                source_id="source-old",
                provenance="旧方案事实画面",
            )
        ],
    )
    approvals = [ApprovalRecord(gate="host", actor="owner")]
    artifacts = [ArtifactRecord(kind="research", path="workspace/research/old.json")]
    task = DailyTask(
        day=date(2026, 8, 10),
        status=TaskStatus.TOPIC_SCRIPT_REVIEW,
        candidates=[old],
        skipped_candidates=[skipped],
        selected_topic_id="old",
        host_profile=None,
        news_script=script,
        media_plan=media_plan,
        approvals=approvals,
        artifacts=artifacts,
    )
    refreshed = refresh_unapproved_task(
        task,
        candidates=[_topic("new")],
        archive_reason="旧候选传播性不足",
        confirmed_host=host,
    )
    assert refreshed.status is TaskStatus.TOPIC_SCRIPT_REVIEW
    assert refreshed.host_profile == host
    assert refreshed.selected_topic_id is None
    assert refreshed.news_script is None
    assert refreshed.media_plan is None
    assert refreshed.candidates[0].id == "new"
    archive = refreshed.archived_topic_plans[-1]
    assert archive.candidates == [old]
    assert archive.skipped_candidates == [skipped]
    assert archive.selected_topic_id == "old"
    assert archive.news_script == script
    assert archive.media_plan == media_plan
    assert archive.reason == "旧候选传播性不足"
    assert refreshed.approvals == approvals
    assert refreshed.artifacts == artifacts


def test_refresh_rejects_a_conflicting_non_null_host():
    task = DailyTask(
        day=date(2026, 8, 10),
        status=TaskStatus.TOPIC_SCRIPT_REVIEW,
        host_profile=_confirmed_host().model_copy(update={"id": "different-host"}),
    )
    with pytest.raises(ValueError, match="conflicts with confirmed host"):
        refresh_unapproved_task(
            task,
            candidates=[_topic("new")],
            archive_reason="replace",
            confirmed_host=_confirmed_host(),
        )


def test_refresh_rejects_topic_approval_and_late_states():
    approved = DailyTask(
        day=date(2026, 8, 10),
        status=TaskStatus.TOPIC_SCRIPT_REVIEW,
        approvals=[ApprovalRecord(gate="topic_script", actor="owner")],
    )
    with pytest.raises(ValueError, match="already approved"):
        refresh_unapproved_task(
            approved,
            candidates=[_topic("new")],
            archive_reason="replace",
            confirmed_host=_confirmed_host(),
        )
    late = DailyTask(day=date(2026, 8, 10), status=TaskStatus.GENERATING_TTS)
    with pytest.raises(ValueError, match="cannot refresh"):
        refresh_unapproved_task(
            late,
            candidates=[_topic("new")],
            archive_reason="replace",
            confirmed_host=_confirmed_host(),
        )


def test_no_qualified_report_cannot_be_converted_to_production_candidates():
    report = HotspotReport(
        day="2026-08-10",
        rule_version="viral-v1.0",
        snapshot_ids=["t0"],
        collection_failures=[],
        candidates=[],
        outcome="no_qualified_hotspot",
    )
    with pytest.raises(ValueError, match="no qualified"):
        topic_candidates_from_report(report)
```

```python
# additions to tests/test_service.py

def test_service_refreshes_only_unapproved_topic_fields_and_preserves_host(tmp_path):
    service = DailyWorkflowService(DailyTaskRepository(tmp_path))
    day = date(2026, 8, 10)
    service.start_day(day, mode=RunMode.MANUAL)
    service.record_research(day, [candidate("old")])
    host = HostProfile(
        id="host-c2-pro-candidate-2-final",
        display_name="C2-Pro 新闻主持人",
        reference_image="output/host-v12-c2-pro/GPT-Image-2-Pro-C2-Pro-主持人最终选定.png",
        studio_reference="蓝色演播室、近景胸像、白衬衣、深藏青西装、无桌、避免手臂入镜",
        visual_style="知性亲和、专业克制、低AI感、五官清晰稳定",
        is_new=False,
        version=12,
    )
    task = service.get(day)
    task.host_profile = host
    service.repository.save(task)
    refreshed = service.refresh_unapproved_hotspots(
        day,
        [_candidate_verified("new")],
        archive_reason="旧候选传播性不足",
        confirmed_host=host,
    )
    assert refreshed.host_profile == host
    assert refreshed.status is TaskStatus.TOPIC_SCRIPT_REVIEW
    assert refreshed.selected_topic_id is None
    assert refreshed.news_script is None
    assert refreshed.media_plan is None
    assert refreshed.approvals == task.approvals
    assert refreshed.artifacts == task.artifacts
```

In `tests/test_service.py`, add this helper beside the existing `candidate()` factory so the call signature is explicit:

```python
def _candidate_verified(topic_id: str) -> TopicCandidate:
    return candidate(topic_id=topic_id).model_copy(
        update={"fact_status": FactStatus.VERIFIED, "publishable": True}
    )
```

- [ ] **Step 6: Run refresh tests and verify missing APIs**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_workflow_refresh.py tests/test_service.py -v`

Expected: FAIL because the refresh module and service method do not exist.

- [ ] **Step 7: Implement report conversion and pure safe refresh**

Create `src/avatar_pipeline/workflow_refresh.py`:

```python
"""Safe bridge from verified hotspot reports to an unapproved production task."""

from collections.abc import Sequence

from avatar_pipeline.hotspot_models import HotspotReport
from avatar_pipeline.models import (
    ArchivedTopicPlan,
    DailyTask,
    FactStatus,
    HostProfile,
    TaskStatus,
    TopicCandidate,
)

_LOCKED_HOST_REFERENCE = (
    "output/host-v12-c2-pro/"
    "GPT-Image-2-Pro-C2-Pro-主持人最终选定.png"
)
_ALLOWED_REFRESH_STATES = {TaskStatus.FACT_SCREENED, TaskStatus.TOPIC_SCRIPT_REVIEW}


def topic_candidates_from_report(report: HotspotReport) -> list[TopicCandidate]:
    if report.outcome != "qualified_candidates" or not report.candidates:
        raise ValueError("report contains no qualified hotspot")
    return [
        TopicCandidate(
            id=item.event_id,
            title=item.click_title,
            pillar=item.pillar,
            score=item.score.total,
            fact_status=FactStatus.VERIFIED,
            target_audience=item.audience_relevance,
            recommendation_reason=item.why_click,
            opening_hook=item.opening_hook,
            trend_evidence=item.platform_evidence,
            risk_flags=item.risks,
            source_evidence=item.source_evidence,
            dedupe_key=item.event_id,
            cluster_id=item.event_id,
            verified_at=report.generated_at,
            verification_summary=item.verification_summary,
            publishable=True,
        )
        for item in report.candidates
    ]


def refresh_unapproved_task(
    task: DailyTask,
    *,
    candidates: Sequence[TopicCandidate],
    archive_reason: str,
    confirmed_host: HostProfile,
) -> DailyTask:
    if confirmed_host.reference_image != _LOCKED_HOST_REFERENCE:
        raise ValueError("confirmed host does not use the locked C2-Pro image")
    if task.host_profile is not None and task.host_profile != confirmed_host:
        raise ValueError("saved host conflicts with confirmed host")
    if task.status not in _ALLOWED_REFRESH_STATES:
        raise ValueError(f"cannot refresh task in {task.status.value}")
    if any(item.gate == "topic_script" for item in task.approvals):
        raise ValueError("topic and script are already approved")
    if not archive_reason.strip():
        raise ValueError("archive_reason must not be blank")
    replacement = list(candidates)
    if not replacement:
        raise ValueError("at least one verified replacement candidate is required")
    if any(not item.publishable or item.fact_status is not FactStatus.VERIFIED for item in replacement):
        raise ValueError("replacement candidates must be verified and publishable")
    archive = ArchivedTopicPlan(
        reason=archive_reason.strip(),
        previous_status=task.status,
        candidates=task.candidates,
        skipped_candidates=task.skipped_candidates,
        selected_topic_id=task.selected_topic_id,
        news_script=task.news_script,
        media_plan=task.media_plan,
    )
    return task.model_copy(update={
        "status": TaskStatus.TOPIC_SCRIPT_REVIEW,
        "candidates": replacement,
        "skipped_candidates": [],
        "selected_topic_id": None,
        "news_script": None,
        "media_plan": None,
        "host_profile": confirmed_host,
        "archived_topic_plans": [*task.archived_topic_plans, archive],
        "stop_reason": None,
    })
```

The helper never changes a valid confirmed `host_profile`; it only fills the actual legacy `null` from the explicitly supplied audited profile and rejects a conflicting non-null host. It never mutates `approvals` or `artifacts`, and it has no dependency on media, TTS, avatar, or compositing modules.

- [ ] **Step 8: Expose the exact refresh method on `DailyWorkflowService`**

Add the workflow import below and add `HostProfile` to the existing model imports in `src/avatar_pipeline/service.py`:

```python
from avatar_pipeline.workflow_refresh import refresh_unapproved_task
```

```python
def refresh_unapproved_hotspots(
    self,
    day: date,
    candidates: Sequence[TopicCandidate],
    archive_reason: str,
    confirmed_host: HostProfile,
) -> DailyTask:
    task = self.repository.get(day)
    refreshed = refresh_unapproved_task(
        task,
        candidates=candidates,
        archive_reason=archive_reason,
        confirmed_host=confirmed_host,
    )
    return self.repository.save(refreshed)
```

Do not call `ensure_transition()` here: this is an audited replacement inside the pre-generation review boundary, not progress into a production stage.

- [ ] **Step 9: Run all model, migration, repository, refresh, and service tests**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_models.py tests/test_repository.py tests/test_workflow_refresh.py tests/test_service.py -v`

Expected: PASS.

Run: `.venv/bin/ruff check src/avatar_pipeline/models.py src/avatar_pipeline/migration.py src/avatar_pipeline/workflow_refresh.py src/avatar_pipeline/service.py tests/test_workflow_refresh.py`

Expected: PASS with no diagnostics.

- [ ] **Step 10: Commit safe workflow refresh**

```bash
git add src/avatar_pipeline/models.py src/avatar_pipeline/migration.py src/avatar_pipeline/workflow_refresh.py src/avatar_pipeline/service.py tests/test_models.py tests/test_repository.py tests/test_workflow_refresh.py tests/test_service.py
git commit -m "feat: safely refresh unapproved hotspot plans"
```

### Task 10: Add manual-mode CLI commands, runbook, and end-to-end safety coverage

**Files:**
- Modify: `src/avatar_pipeline/cli.py`
- Modify: `tests/test_cli.py`
- Create: `tests/test_hotspot_end_to_end.py`
- Create: `docs/runbooks/manual-hotspot-sampling.md`

**Interfaces:**
- Produces CLI commands: `hotspot-import-snapshot`, `hotspot-import-review`, `hotspot-build-report`, `hotspot-status`, and `hotspot-refresh`.
- Safety boundary: all hotspot commands are evidence/report operations except `hotspot-refresh`, which only archives and resets unapproved topic/script/media fields through Task 9; none call generation methods.

- [ ] **Step 1: Write failing CLI tests for import, review status, report creation, and safe refresh**

Append these tests to `tests/test_cli.py`:

```python
from datetime import date

from avatar_pipeline.hotspot_models import (
    DirectorAction,
    HotspotCandidateReport,
    HotspotReport,
    TrendLabel,
    ViralityBand,
    ViralityScore,
)
from avatar_pipeline.hotspot_repository import HotspotRepository
from avatar_pipeline.models import DailyTask, HostProfile, NewsPillarSlug, TaskStatus
from avatar_pipeline.repository import DailyTaskRepository


def test_cli_imports_snapshot_builds_report_and_shows_transparent_status(tmp_path):
    imported = run_cli(
        tmp_path,
        "hotspot-import-snapshot",
        "--date", "2026-08-10",
        "--format", "canonical",
        "--file", "tests/fixtures/hotspots/canonical-t0.json",
    )
    assert imported.returncode == 0
    assert json.loads(imported.stdout)["snapshot_id"] == "t0"

    built = run_cli(tmp_path, "hotspot-build-report", "--date", "2026-08-10")
    assert built.returncode == 0
    assert json.loads(built.stdout)["outcome"] == "no_qualified_hotspot"

    status = run_cli(tmp_path, "hotspot-status", "--date", "2026-08-10")
    payload = json.loads(status.stdout)
    assert payload["snapshot_ids"] == ["t0"]
    assert payload["report_outcome"] == "no_qualified_hotspot"


def test_cli_refresh_preserves_confirmed_host_and_creates_no_assets(tmp_path):
    day = date(2026, 8, 10)
    host = HostProfile(
        id="host-c2-pro-candidate-2-final",
        display_name="C2-Pro 新闻主持人",
        reference_image="output/host-v12-c2-pro/GPT-Image-2-Pro-C2-Pro-主持人最终选定.png",
        studio_reference="蓝色演播室、近景胸像、白衬衣、深藏青西装、无桌、避免手臂入镜",
        visual_style="知性亲和、专业克制、低AI感、五官清晰稳定",
        is_new=False,
        version=12,
    )
    confirmed_host_path = tmp_path / "confirmed-host.json"
    confirmed_host_path.write_text(
        host.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    DailyTaskRepository(tmp_path).create(
        DailyTask(day=day, host_profile=None, status=TaskStatus.TOPIC_SCRIPT_REVIEW)
    )
    score = ViralityScore(
        event_id="event-1",
        rule_version="viral-v1.0",
        cross_platform_resonance=25,
        trend_velocity=20,
        conflict_suspense=15,
        public_interest=10,
        curiosity_gap=10,
        visual_impact=8,
        explanatory_depth=4,
        fact_safety=5,
        total=97,
    )
    candidate = HotspotCandidateReport(
        event_id="event-1",
        representative_title="事件",
        click_title="事件为什么突然引发关注？",
        collected_from="2026-08-10T19:40:00+08:00",
        collected_to="2026-08-10T20:00:00+08:00",
        platform_evidence=["weibo rank=1", "baidu rank=2", "zhihu rank=3"],
        trend_label=TrendLabel.RISING,
        score=score,
        score_band=ViralityBand.DIRECTOR_FIRST,
        why_click="存在明确认知缺口",
        opening_hook="变化发生得比预期更快。",
        audience_relevance="影响普通人的安全与出行",
        visual_assets=["official-map.png"],
        copyright_notes=["引用时标注官方来源"],
        expected_lifetime="12-24小时",
        risks=[],
        wording_to_avoid=[],
        director_action=DirectorAction.DO_NOW,
        pillar=NewsPillarSlug.SOCIAL_PHENOMENA,
        source_evidence=[],
        verification_summary="核心事实已核验",
    )
    report = HotspotReport(
        day=day.isoformat(),
        rule_version="viral-v1.0",
        snapshot_ids=["t0", "t1", "t2"],
        collection_failures=[],
        candidates=[candidate],
        director_recommendation_event_id="event-1",
        outcome="qualified_candidates",
    )
    HotspotRepository(tmp_path).save_report(day, report, "# report\n")

    result = run_cli(
        tmp_path,
        "hotspot-refresh",
        "--date", "2026-08-10",
        "--archive-reason", "旧候选传播性不足",
        "--confirmed-host-profile", str(confirmed_host_path),
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "topic_script_review"
    assert payload["host_profile"] == host.model_dump(mode="json")
    assert payload["selected_topic_id"] is None
    assert payload["news_script"] is None
    assert payload["media_plan"] is None
    assert payload["artifacts"] == []
```

- [ ] **Step 2: Run CLI tests and verify the hotspot commands are unknown**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_cli.py -v`

Expected: FAIL because the five `hotspot-*` commands do not exist.

- [ ] **Step 3: Add exact hotspot command parsers**

Import `datetime`, the hotspot adapters/models/repository/service, and `topic_candidates_from_report` in `src/avatar_pipeline/cli.py`, then append these parsers inside `build_parser()`:

```python
    hotspot_import = subparsers.add_parser("hotspot-import-snapshot")
    _add_date_argument(hotspot_import)
    hotspot_import.add_argument("--file", required=True, type=Path)
    hotspot_import.add_argument("--format", required=True, choices=("canonical", "tophub"))
    hotspot_import.add_argument("--snapshot-id")
    hotspot_import.add_argument("--captured-at")
    hotspot_import.add_argument("--timezone", default="Asia/Shanghai")
    hotspot_import.add_argument("--failures", type=Path)

    hotspot_review = subparsers.add_parser("hotspot-import-review")
    _add_date_argument(hotspot_review)
    hotspot_review.add_argument("--verification", required=True, type=Path)
    hotspot_review.add_argument("--editorial-signals", required=True, type=Path)

    hotspot_build = subparsers.add_parser("hotspot-build-report")
    _add_date_argument(hotspot_build)

    hotspot_status = subparsers.add_parser("hotspot-status")
    _add_date_argument(hotspot_status)

    hotspot_refresh = subparsers.add_parser("hotspot-refresh")
    _add_date_argument(hotspot_refresh)
    hotspot_refresh.add_argument("--archive-reason", required=True)
    hotspot_refresh.add_argument("--confirmed-host-profile", required=True, type=Path)
```

At module scope, replace the existing `datetime` and `typing` imports with the merged forms below. Keep `HostProfile` in the existing grouped `avatar_pipeline.models` import, then add the remaining imports exactly as shown:

```python
from datetime import date, datetime
from typing import Any, TypeVar

from pydantic import BaseModel

from avatar_pipeline.hotspot_collectors import (
    import_canonical_snapshot,
    import_tophub_snapshot,
)
from avatar_pipeline.hotspot_models import CandidateVerification, EditorialSignals
from avatar_pipeline.hotspot_repository import HotspotRepository
from avatar_pipeline.hotspot_service import HotspotService
from avatar_pipeline.workflow_refresh import topic_candidates_from_report
```

- [ ] **Step 4: Implement hotspot dispatch without generation calls**

Add these functions before `_dispatch_production`:

```python
ReviewModelT = TypeVar("ReviewModelT", bound=BaseModel)


def _load_review_items(
    path: Path,
    model_type: type[ReviewModelT],
) -> list[ReviewModelT]:
    payload = _load_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a JSON list")
    return [model_type.model_validate(item) for item in payload]


def _dispatch_hotspot(args: argparse.Namespace) -> dict[str, Any]:
    app_config = load_config(_DEFAULT_CONFIG)
    repository = HotspotRepository(args.workspace)
    service = HotspotService(repository, app_config.hotspot)
    if args.command == "hotspot-import-snapshot":
        if args.format == "canonical":
            snapshot = import_canonical_snapshot(args.file)
        else:
            if not args.snapshot_id or not args.captured_at:
                raise ValueError("tophub import requires --snapshot-id and --captured-at")
            failures_payload = _load_json(args.failures) if args.failures else {}
            failures = {
                platform: (str(value[0]), str(value[1]))
                for platform, value in failures_payload.items()
            }
            snapshot = import_tophub_snapshot(
                path=args.file,
                snapshot_id=args.snapshot_id,
                captured_at=datetime.fromisoformat(args.captured_at),
                timezone=args.timezone,
                platform_aliases=app_config.hotspot.platform_aliases,
                failures=failures,
            )
        repository.save_snapshot(args.date, snapshot)
        return snapshot.model_dump(mode="json")
    if args.command == "hotspot-import-review":
        verifications = _load_review_items(args.verification, CandidateVerification)
        editorial = _load_review_items(args.editorial_signals, EditorialSignals)
        repository.save_verifications(args.date, verifications)
        repository.save_editorial_signals(args.date, editorial)
        return {
            "verification_event_ids": sorted(item.event_id for item in verifications),
            "editorial_event_ids": sorted(item.event_id for item in editorial),
        }
    if args.command == "hotspot-build-report":
        return service.build_report(args.date).model_dump(mode="json")
    if args.command == "hotspot-status":
        snapshots = repository.list_snapshots(args.date)
        try:
            report = repository.load_report(args.date)
        except FileNotFoundError:
            report = None
        return {
            "date": args.date.isoformat(),
            "snapshot_ids": [item.snapshot_id for item in snapshots],
            "successful_platforms": sorted({
                platform for item in snapshots for platform in item.successful_platforms
            }),
            "failures": [
                failure.model_dump(mode="json")
                for item in snapshots
                for failure in item.failures
            ],
            "report_outcome": report.outcome if report else None,
            "candidate_event_ids": [item.event_id for item in report.candidates] if report else [],
        }
    if args.command == "hotspot-refresh":
        report = repository.load_report(args.date)
        production = DailyWorkflowService(DailyTaskRepository(args.workspace))
        confirmed_host = HostProfile.model_validate_json(
            args.confirmed_host_profile.read_text(encoding="utf-8")
        )
        task = production.refresh_unapproved_hotspots(
            args.date,
            topic_candidates_from_report(report),
            archive_reason=args.archive_reason,
            confirmed_host=confirmed_host,
        )
        return _task_payload(task)
    raise ValueError(f"unsupported hotspot command: {args.command}")
```

Route the commands before research/production dispatch:

```python
if args.command.startswith("hotspot-"):
    return _dispatch_hotspot(args)
```

There must be no reference to `mark_tts_ready`, `mark_anchor_ready`, `mark_media_ready`, or `mark_compositing` inside `_dispatch_hotspot`.

- [ ] **Step 5: Run CLI tests and lint**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_cli.py -v`

Expected: PASS.

Run: `.venv/bin/ruff check src/avatar_pipeline/cli.py tests/test_cli.py`

Expected: PASS with no diagnostics.

- [ ] **Step 6: Write the end-to-end tests before implementation integration is considered complete**

Create `tests/test_hotspot_end_to_end.py`:

```python
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
```

- [ ] **Step 7: Run the end-to-end test and fix only integration mismatches**

Run: `PYTHONPATH=src .venv/bin/pytest tests/test_hotspot_end_to_end.py -v`

Expected: PASS with four tests proving Top 3 selection, single-platform rejection, single-snapshot non-trend behavior, safe no-candidate stopping, C2 host preservation, and no generation assets.

- [ ] **Step 8: Write the manual T0/T+10/T+20 runbook**

Create `docs/runbooks/manual-hotspot-sampling.md` with this complete operating procedure:

````markdown
# Manual cross-platform hotspot sampling

This runbook is research-only. It does not generate scripts, speech, avatar video, insert media, or composites.

## Safety checks

1. Use the locked business date `2026-08-10` when rebuilding that day's decision.
2. Confirm `workspace/days/2026-08-10/task.json` is `fact_screened` or `topic_script_review` and has no `topic_script` approval.
3. Do not run `mark-tts`, `mark-anchor`, `mark-media`, or `mark-compositing`.
4. Keep the C2-Pro Candidate 2 host image and `host_profile` unchanged; verify SHA256 `939324593eb718cd2a39be4c171f74178a6a48442f7e0d61afe8a875011e8a47` before refresh.

Run the exact check and stop on mismatch:

```bash
test "$(shasum -a 256 'output/host-v12-c2-pro/GPT-Image-2-Pro-C2-Pro-主持人最终选定.png' | awk '{print $1}')" = \
  "939324593eb718cd2a39be4c171f74178a6a48442f7e0d61afe8a875011e8a47"
```

## Import T0, T+10, and T+20

For canonical snapshots:

```bash
PYTHONPATH=src .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-import-snapshot --date 2026-08-10 --format canonical \
  --file tmp/hotspot-sampling/t0.json
sleep 600
PYTHONPATH=src .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-import-snapshot --date 2026-08-10 --format canonical \
  --file tmp/hotspot-sampling/t1.json
sleep 600
PYTHONPATH=src .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-import-snapshot --date 2026-08-10 --format canonical \
  --file tmp/hotspot-sampling/t2.json
```

For a TopHub structured export, include immutable capture metadata and an optional failure map whose JSON shape is `{"bilibili": ["api returned -352", "tmp/raw/bilibili.json"]}`:

```bash
PYTHONPATH=src .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-import-snapshot --date 2026-08-10 --format tophub \
  --file tmp/tophub_structured.json --snapshot-id t0 \
  --captured-at 2026-08-10T19:47:17+08:00 --timezone Asia/Shanghai \
  --failures tmp/hotspot-failures.json
```

## Discover event IDs and import human review

Build once to expose rejected cluster IDs. Missing review data is an explicit rejection, not an error or zero score:

```bash
PYTHONPATH=src .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-build-report --date 2026-08-10
PYTHONPATH=src .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-status --date 2026-08-10
```

Prepare `verification.json` as a JSON list of `CandidateVerification` objects and `editorial-signals.json` as a JSON list of `EditorialSignals` objects. Rebuild after importing them:

```bash
PYTHONPATH=src .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-import-review --date 2026-08-10 \
  --verification tmp/hotspot-sampling/verification.json \
  --editorial-signals tmp/hotspot-sampling/editorial-signals.json
PYTHONPATH=src .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-build-report --date 2026-08-10
```

Read both:

- `workspace/hotspots/2026-08-10/reports/candidate-report.json`
- `workspace/hotspots/2026-08-10/reports/candidate-report.md`

If `outcome` is `no_qualified_hotspot`, stop. Do not substitute a lower-quality topic.

## Refresh only after reviewing the qualified report

This archives the old candidates, script, and media plan; preserves the host; clears the active selection/script/media plan; and remains at `topic_script_review`:

```bash
PYTHONPATH=src .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-refresh --date 2026-08-10 \
  --archive-reason "旧‘大学新生电脑涨价’方案传播性不足，改用跨平台连续采样候选" \
  --confirmed-host-profile output/manual-run-2026-08-10/planning/host-profile.json
```

After refresh, inspect production state:

```bash
PYTHONPATH=src .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  status --date 2026-08-10
```

The expected state is `topic_script_review`, with the C2-Pro Candidate 2 `host_profile`, no selected topic, no script, no media plan, and no new artifacts. User confirmation is still required before any paid generation.
````

- [ ] **Step 9: Run the complete suite and Ruff**

Run: `PYTHONPATH=src .venv/bin/pytest -v`

Expected: PASS for the entire repository.

Run: `.venv/bin/ruff check src tests`

Expected: PASS with no diagnostics.

- [ ] **Step 10: Perform one local, non-generation smoke run against the saved August 10 evidence**

Use a temporary workspace so this verification cannot alter the real `workspace/days/2026-08-10/task.json`:

```bash
SMOKE_ROOT="$(mktemp -d)"
printf '%s\n' '{"bilibili":["saved API response was restricted","tmp/hotspot-2026-08-10-rebuild/bilibili.json"]}' > "$SMOKE_ROOT/failures.json"
PYTHONPATH=src .venv/bin/python -m avatar_pipeline.cli --workspace "$SMOKE_ROOT" \
  hotspot-import-snapshot --date 2026-08-10 --format tophub \
  --file tmp/tophub_structured.json --snapshot-id saved-t0 \
  --captured-at 2026-08-10T19:47:17+08:00 --timezone Asia/Shanghai \
  --failures "$SMOKE_ROOT/failures.json"
PYTHONPATH=src .venv/bin/python -m avatar_pipeline.cli --workspace "$SMOKE_ROOT" \
  hotspot-build-report --date 2026-08-10
PYTHONPATH=src .venv/bin/python -m avatar_pipeline.cli --workspace "$SMOKE_ROOT" \
  hotspot-status --date 2026-08-10
find "$SMOKE_ROOT" -type f -print | sort
```

Expected:

- the saved local TopHub evidence imports successfully;
- the single saved snapshot is never described as rising;
- missing verification/editorial inputs are transparent rejections;
- only hotspot snapshot/report files exist under the temporary root;
- no `audio`, `anchor`, `insert_media`, `master_video`, TTS, avatar, or compositing artifacts are created;
- this smoke run does **not** preselect typhoon “白海豚” or any other event.

- [ ] **Step 11: Commit CLI, runbook, and end-to-end coverage**

```bash
git add src/avatar_pipeline/cli.py tests/test_cli.py tests/test_hotspot_end_to_end.py docs/runbooks/manual-hotspot-sampling.md
git commit -m "feat: operate manual viral hotspot sampling"
```

## Final implementation verification

After all ten task commits, run:

```bash
PYTHONPATH=src .venv/bin/pytest -v
.venv/bin/ruff check src tests
git status --short
git log --oneline -10
```

Acceptance requires:

- all tests and Ruff pass;
- `workspace/days/2026-08-10/task.json` is unchanged until an operator explicitly runs `hotspot-refresh` after reviewing a qualified report;
- `output/` and `tmp/` remain uncommitted;
- the selected C2-Pro Candidate 2 host remains unchanged;
- no generation service is called and no generated asset is produced;
- a report with no qualifying event says `no_qualified_hotspot` rather than filling the slate with an ordinary topic.
