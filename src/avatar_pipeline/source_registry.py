"""Source-adapter registry for the six editorial-opportunity discovery classes."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from avatar_pipeline.models import DomainModel
from avatar_pipeline.news_intelligence_models import AttentionSourceKind, EvidenceRole


class AcquisitionMode(StrEnum):
    EXISTING_COLLECTOR = "existing_collector"
    RSS = "rss"
    OFFICIAL_API = "official_api"
    EXTERNAL_SERVICE = "external_service"
    MANUAL_IMPORT = "manual_import"


class SourceAdapterSpec(DomainModel):
    adapter_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    signal_class: AttentionSourceKind
    roles: list[EvidenceRole] = Field(min_length=1)
    acquisition_mode: AcquisitionMode
    reliability_tier: str = Field(min_length=1)
    requires_credentials: bool = False
    experimental: bool = False
    license_note: str = ""
    fallback: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_adapter_policy(self) -> SourceAdapterSpec:
        if not self.fallback.strip():
            raise ValueError("source adapter fallback must not be blank")
        if (
            EvidenceRole.FACT_EVIDENCE in self.roles
            and self.reliability_tier not in {"authoritative", "trusted", "first_party"}
        ):
            raise ValueError("fact evidence adapters require authoritative reliability")
        return self


class SourceRegistry(DomainModel):
    adapters: list[SourceAdapterSpec] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_adapters(self) -> SourceRegistry:
        ids = [item.adapter_id for item in self.adapters]
        names = [item.name for item in self.adapters]
        if len(ids) != len(set(ids)) or len(names) != len(set(names)):
            raise ValueError("source adapter IDs and names must be unique")
        return self

    @property
    def signal_classes(self) -> set[str]:
        return {item.signal_class.value for item in self.adapters}

    @property
    def names(self) -> set[str]:
        return {item.name for item in self.adapters}

    def by_name(self, name: str) -> SourceAdapterSpec:
        try:
            return next(item for item in self.adapters if item.name == name)
        except StopIteration as error:
            raise KeyError(name) from error


def _adapter(
    adapter_id: str,
    name: str,
    signal_class: AttentionSourceKind,
    roles: list[EvidenceRole],
    acquisition_mode: AcquisitionMode,
    reliability_tier: str,
    fallback: str,
    *,
    requires_credentials: bool = False,
    experimental: bool = False,
    license_note: str = "",
) -> SourceAdapterSpec:
    return SourceAdapterSpec(
        adapter_id=adapter_id,
        name=name,
        signal_class=signal_class,
        roles=roles,
        acquisition_mode=acquisition_mode,
        reliability_tier=reliability_tier,
        requires_credentials=requires_credentials,
        experimental=experimental,
        license_note=license_note,
        fallback=fallback,
    )


def build_default_source_registry() -> SourceRegistry:
    attention = EvidenceRole.ATTENTION_SIGNAL
    fact = EvidenceRole.FACT_EVIDENCE
    footage = EvidenceRole.FOOTAGE_CANDIDATE
    adapters = [
        _adapter(
            "domestic-hot-boards",
            "国内热点榜单",
            AttentionSourceKind.DOMESTIC_BOARD,
            [attention],
            AcquisitionMode.EXISTING_COLLECTOR,
            "orientation",
            "人工导入榜单快照",
        ),
        _adapter(
            "xinhuanet",
            "新华网",
            AttentionSourceKind.AUTHORITATIVE_MEDIA,
            [attention, fact, footage],
            AcquisitionMode.RSS,
            "authoritative",
            "网页或人工导入官方原文",
        ),
        _adapter(
            "people-daily",
            "人民日报",
            AttentionSourceKind.AUTHORITATIVE_MEDIA,
            [attention, fact, footage],
            AcquisitionMode.RSS,
            "authoritative",
            "官方网页或账号人工导入",
        ),
        _adapter(
            "cctv-news",
            "央视新闻",
            AttentionSourceKind.AUTHORITATIVE_MEDIA,
            [attention, fact, footage],
            AcquisitionMode.RSS,
            "authoritative",
            "央视官方网页或账号人工导入",
        ),
        _adapter(
            "china-youth-daily",
            "中国青年报",
            AttentionSourceKind.AUTHORITATIVE_MEDIA,
            [attention, fact, footage],
            AcquisitionMode.RSS,
            "authoritative",
            "官方网页或账号人工导入",
        ),
        _adapter(
            "trendradar",
            "TrendRadar",
            AttentionSourceKind.DOMESTIC_BOARD,
            [attention],
            AcquisitionMode.EXTERNAL_SERVICE,
            "orientation",
            "现有榜单采集器或人工快照",
            license_note="GPL-3.0，仅服务/API接入，不复制源代码",
        ),
        _adapter(
            "rsshub",
            "RSSHub",
            AttentionSourceKind.AUTHORITATIVE_MEDIA,
            [attention],
            AcquisitionMode.EXTERNAL_SERVICE,
            "orientation",
            "来源官网或人工导入",
            license_note="AGPL-3.0，仅服务/API接入，不复制源代码",
        ),
        _adapter(
            "google-trends",
            "Google Trends",
            AttentionSourceKind.SEARCH_DEMAND,
            [attention],
            AcquisitionMode.OFFICIAL_API,
            "orientation",
            "百度相关搜索与人工趋势记录",
            requires_credentials=True,
            experimental=True,
            license_note="官方接口受限时不得作为唯一生产信号",
        ),
        _adapter(
            "x-official-api",
            "X官方API",
            AttentionSourceKind.SOCIAL_DISCUSSION,
            [attention, footage],
            AcquisitionMode.OFFICIAL_API,
            "orientation",
            "第一方账号网页快照或人工导入",
            requires_credentials=True,
        ),
        _adapter(
            "xquik",
            "Xquik",
            AttentionSourceKind.SOCIAL_DISCUSSION,
            [attention],
            AcquisitionMode.EXTERNAL_SERVICE,
            "orientation",
            "X官方API或人工导入",
            requires_credentials=True,
            experimental=True,
            license_note="MIT 可选适配器，官方 X API 优先",
        ),
        _adapter(
            "youtube-data-api",
            "YouTube Data API",
            AttentionSourceKind.VIDEO_PROPAGATION,
            [attention, footage],
            AcquisitionMode.OFFICIAL_API,
            "orientation",
            "官方频道页面或人工导入视频资料",
            requires_credentials=True,
        ),
        _adapter(
            "scrapecreators",
            "ScrapeCreators社交研究",
            AttentionSourceKind.VIDEO_PROPAGATION,
            [attention],
            AcquisitionMode.EXTERNAL_SERVICE,
            "orientation",
            "平台原始页面、字幕和评论人工抽样",
            requires_credentials=True,
            experimental=True,
            license_note="可选付费增强，不作为唯一依赖",
        ),
        _adapter(
            "the-news",
            "The News",
            AttentionSourceKind.AUTHORITATIVE_MEDIA,
            [attention],
            AcquisitionMode.EXTERNAL_SERVICE,
            "orientation",
            "GDELT 或权威媒体首页人工核对",
            license_note="MIT，用于国际新闻方向发现而非最终核验",
        ),
        _adapter(
            "gdelt-doc",
            "GDELT DOC 2.0",
            AttentionSourceKind.AUTHORITATIVE_MEDIA,
            [attention],
            AcquisitionMode.OFFICIAL_API,
            "orientation",
            "国际权威媒体人工检索",
        ),
        _adapter(
            "github-hacker-news",
            "GitHub与Hacker News",
            AttentionSourceKind.VERTICAL_COMMUNITY,
            [attention],
            AcquisitionMode.OFFICIAL_API,
            "orientation",
            "项目官方仓库与发布说明人工核验",
        ),
        _adapter(
            "vertical-communities",
            "垂直社区人工观察",
            AttentionSourceKind.VERTICAL_COMMUNITY,
            [attention],
            AcquisitionMode.MANUAL_IMPORT,
            "orientation",
            "权威媒体和第一方来源复核",
        ),
    ]
    return SourceRegistry(adapters=adapters)
