"""Application configuration loading and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VideoConfig(StrictModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    min_duration_seconds: int = Field(ge=1)
    max_duration_seconds: int = Field(ge=1)
    target_audio_min_seconds: int = Field(default=40, ge=1)
    target_audio_max_seconds: int = Field(default=46, ge=1)
    avatar_ratio_min: float = Field(default=0.55, ge=0, le=1)
    avatar_ratio_max: float = Field(default=0.65, ge=0, le=1)

    @model_validator(mode="after")
    def validate_v1(self) -> VideoConfig:
        if self.width != 1080 or self.height != 1920:
            raise ValueError("V1 video output must be 1080x1920")
        if self.min_duration_seconds > self.max_duration_seconds:
            raise ValueError("minimum duration must not exceed maximum duration")
        if self.min_duration_seconds < 45 or self.max_duration_seconds > 75:
            raise ValueError("V1 duration range must stay within 45-75 seconds")
        if self.target_audio_min_seconds > self.target_audio_max_seconds:
            raise ValueError("minimum target audio duration must not exceed maximum")
        if self.avatar_ratio_min > self.avatar_ratio_max:
            raise ValueError("minimum avatar ratio must not exceed maximum")
        return self


class ContentPillar(StrictModel):
    slug: str = Field(min_length=1)
    display_name: str = Field(min_length=1)


class ContentConfig(StrictModel):
    pillars: list[ContentPillar] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_pillars(self) -> ContentConfig:
        slugs = [pillar.slug for pillar in self.pillars]
        if len(slugs) != len(set(slugs)):
            raise ValueError("content pillar slugs must be unique")
        return self


class ApprovalPolicy(StrictModel):
    topic_script: Literal["auto", "user_confirm"]
    avatar: Literal["auto", "confirm_if_new_or_changed"]
    final_video: Literal["final_only", "user_confirm"]


class ApprovalConfig(StrictModel):
    managed: ApprovalPolicy
    manual: ApprovalPolicy


class StorageConfig(StrictModel):
    workspace: Path
    contracts_directory: Path


class SourceRangeConfig(StrictModel):
    min_sources: int = Field(ge=0)
    max_sources: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_range(self) -> SourceRangeConfig:
        if self.min_sources > self.max_sources:
            raise ValueError("minimum source target must not exceed maximum")
        return self


class PlatformTargetsConfig(StrictModel):
    douyin: SourceRangeConfig
    wechat_channels: SourceRangeConfig
    xiaohongshu: SourceRangeConfig
    supplementary: SourceRangeConfig
    wechat_official_accounts: SourceRangeConfig


class TimeWindowSharesConfig(StrictModel):
    last_72_hours: float = Field(ge=0, le=1)
    last_7_days: float = Field(ge=0, le=1)
    last_30_days: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_total(self) -> TimeWindowSharesConfig:
        total = self.last_72_hours + self.last_7_days + self.last_30_days
        if abs(total - 1.0) > 1e-9:
            raise ValueError("research time-window shares must sum to 1.0")
        return self


class ResearchQueryConfig(StrictModel):
    core_group_count: int = Field(gt=0)
    groups_per_pillar: int = Field(gt=0)
    expansion_cap: int = Field(ge=0)
    exact_query_cooldown_days: int = Field(gt=0)
    scene_cooldown_days: int = Field(gt=0)
    history_days: int = Field(gt=0)
    empty_result_threshold: int = Field(gt=0)
    empty_result_cooldown_days: int = Field(gt=0)


class CommentTargetsConfig(StrictModel):
    a_grade_sources_min: int = Field(gt=0)
    a_grade_sources_max: int = Field(gt=0)
    per_source_min: int = Field(gt=0)
    per_source_max: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_ranges(self) -> CommentTargetsConfig:
        if self.a_grade_sources_min > self.a_grade_sources_max:
            raise ValueError("minimum A-grade source target must not exceed maximum")
        if self.per_source_min > self.per_source_max:
            raise ValueError("minimum comment target must not exceed maximum")
        return self


class ResearchConfig(StrictModel):
    query: ResearchQueryConfig
    time_window_shares: TimeWindowSharesConfig
    platform_targets: PlatformTargetsConfig
    comments: CommentTargetsConfig
    excluded_topics: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_query_shape(self) -> ResearchConfig:
        if self.query.core_group_count != self.query.groups_per_pillar * 3:
            raise ValueError("core query count must equal groups per pillar times 3")
        if any(not topic.strip() for topic in self.excluded_topics):
            raise ValueError("excluded research topics must not be blank")
        return self


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
    required_short_video_platforms: list[str] = Field(min_length=1)
    min_short_video_sources_per_platform: int = Field(ge=1)
    min_short_video_comment_samples_per_platform: int = Field(ge=1)
    min_short_video_engagement_rate: float = Field(gt=0, le=1)
    min_short_video_observed_interactions: int = Field(ge=1)
    min_short_video_platform_score: float = Field(ge=0, le=1)
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


HotspotSelectionCategory = Literal[
    "social_livelihood",
    "technology",
    "finance",
    "international",
    "policy",
    "consumer",
    "education",
    "influencer",
    "ordinary_people",
    "ordinary_life_moment",
    "culture_entertainment",
    "weather_disaster",
]


class PreferredAuthoritativeMediaConfig(StrictModel):
    name: str = Field(min_length=1)
    platform: str = Field(min_length=1)
    account_name: str | None = None
    roles: list[Literal["fact_source", "hotspot_signal", "footage_candidate"]] = Field(min_length=1)


class OrdinaryLifeMomentGateConfig(StrictModel):
    enabled: Literal[True]
    reject_professional_influencers: Literal[True]
    require_personal_daily_recorder: Literal[True]
    require_ordinary_people_as_primary_subjects: Literal[True]
    reject_creator_initiated_events: Literal[True]
    require_event_preexisted_filming: Literal[True]
    require_daily_life_context: Literal[True]
    require_human_warmth_evidence: Literal[True]
    max_staging_risk: float = Field(ge=0, le=0.35)
    require_original_recorder: Literal[True]
    require_continuous_scene: Literal[True]


def _default_ordinary_life_moment_gate() -> OrdinaryLifeMomentGateConfig:
    return OrdinaryLifeMomentGateConfig(
        enabled=True,
        reject_professional_influencers=True,
        require_personal_daily_recorder=True,
        require_ordinary_people_as_primary_subjects=True,
        reject_creator_initiated_events=True,
        require_event_preexisted_filming=True,
        require_daily_life_context=True,
        require_human_warmth_evidence=True,
        max_staging_risk=0.35,
        require_original_recorder=True,
        require_continuous_scene=True,
    )


class HotspotSelectionConfig(StrictModel):
    target_min_candidates: int | None = Field(default=None, ge=0, le=8)
    min_candidates: int | None = Field(default=None, ge=0, le=8)
    max_candidates: int = Field(ge=1, le=12)
    min_categories: int | None = Field(default=None, ge=0)
    allow_fewer_than_target: bool = False
    pad_weak_candidates: bool = False
    require_user_selection: Literal[True]
    categories: list[HotspotSelectionCategory] = Field(min_length=5)
    preferred_authoritative_media: list[PreferredAuthoritativeMediaConfig] = Field(min_length=1)
    ordinary_life_moment_gate: OrdinaryLifeMomentGateConfig = Field(
        default_factory=_default_ordinary_life_moment_gate
    )

    @model_validator(mode="after")
    def validate_selection_policy(self) -> HotspotSelectionConfig:
        if len(self.categories) != len(set(self.categories)):
            raise ValueError("hotspot selection categories must be unique")
        if self.target_min_candidates is None and self.min_candidates is None:
            raise ValueError("candidate selection requires a target or legacy minimum")
        if (
            self.target_min_candidates is not None
            and self.target_min_candidates > self.max_candidates
        ):
            raise ValueError("target candidate count cannot exceed maximum")
        if self.min_candidates is not None and self.min_candidates > self.max_candidates:
            raise ValueError("legacy minimum candidate count cannot exceed maximum")
        required_names = {"新华网", "人民日报", "中国青年报"}
        configured_names = {item.name for item in self.preferred_authoritative_media}
        if not required_names.issubset(configured_names):
            raise ValueError("preferred media must include 新华网、人民日报和中国青年报")
        return self


class EditorialOpportunityScoreWeights(StrictModel):
    real_heat: Literal[30]
    content_attractiveness: Literal[35]
    fact_reliability: Literal[20]
    video_potential: Literal[15]


EditorialSignalClass = Literal[
    "domestic_boards",
    "authoritative_media",
    "search_demand",
    "social_discussion",
    "video_propagation",
    "vertical_communities",
]


class EditorialOpportunityConfig(StrictModel):
    rule_version: Literal["editorial-opportunity-v2.0"]
    score_weights: EditorialOpportunityScoreWeights
    s_score_min: int = Field(ge=0, le=100)
    a_score_min: int = Field(ge=0, le=100)
    max_user_candidates: Literal[8]
    target_min_candidates: int = Field(default=3, ge=0, le=8)
    allow_fewer_than_target: Literal[True]
    pad_weak_candidates: Literal[False]
    require_user_selection: Literal[True]
    no_s_tier_message: str = Field(min_length=1)
    source_signal_classes: list[EditorialSignalClass] = Field(min_length=6)

    @model_validator(mode="after")
    def validate_editorial_policy(self) -> EditorialOpportunityConfig:
        if self.a_score_min >= self.s_score_min:
            raise ValueError("A threshold must be lower than S threshold")
        if len(self.source_signal_classes) != len(set(self.source_signal_classes)):
            raise ValueError("source signal classes must be unique")
        if self.target_min_candidates > self.max_user_candidates:
            raise ValueError("target candidates cannot exceed user-visible maximum")
        return self


class AppConfig(StrictModel):
    mode: Literal["managed", "manual"]
    topic_source: Literal["user_topic", "auto_hot"]
    avatar_source: Literal["user_provided", "saved_host", "agent_designed"]
    subtitle: Literal[False]
    video_structure: Literal["studio_anchor_plus_vertical_news_insert"]
    media_policy: Literal["reliable_original_first_ai_demo_fallback"]
    platforms: list[Literal["douyin", "wechat_channels", "xiaohongshu"]] = Field(min_length=1)
    video: VideoConfig
    content: ContentConfig
    approval_policy: ApprovalConfig
    storage: StorageConfig
    research: ResearchConfig
    hotspot: HotspotConfig
    hotspot_selection: HotspotSelectionConfig
    editorial_opportunity: EditorialOpportunityConfig | None = None


def load_config(path: Path | str) -> AppConfig:
    """Load and validate application configuration from a YAML file."""

    with Path(path).open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return AppConfig.model_validate(raw)
