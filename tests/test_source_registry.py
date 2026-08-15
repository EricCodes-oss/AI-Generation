import pytest
from pydantic import ValidationError

from avatar_pipeline.source_registry import (
    AcquisitionMode,
    EvidenceRole,
    SourceAdapterSpec,
    build_default_source_registry,
)


def test_default_registry_covers_all_six_discovery_signal_classes():
    registry = build_default_source_registry()
    assert registry.signal_classes == {
        "domestic_boards",
        "authoritative_media",
        "search_demand",
        "social_discussion",
        "video_propagation",
        "vertical_communities",
    }
    assert {"新华网", "人民日报", "央视新闻", "中国青年报"}.issubset(registry.names)
    assert "X官方API" in registry.names
    assert "YouTube Data API" in registry.names


def test_gpl_and_agpl_integrations_are_service_only_with_fallbacks():
    registry = build_default_source_registry()
    for name in ("TrendRadar", "RSSHub"):
        source = registry.by_name(name)
        assert source.acquisition_mode is AcquisitionMode.EXTERNAL_SERVICE
        assert source.fallback
        assert "不复制" in source.license_note


def test_source_adapter_requires_fallback_and_fact_role_requires_reliability():
    with pytest.raises(ValidationError, match="fallback"):
        SourceAdapterSpec(
            adapter_id="bad",
            name="Bad",
            signal_class="social_discussion",
            roles=[EvidenceRole.ATTENTION_SIGNAL],
            acquisition_mode=AcquisitionMode.OFFICIAL_API,
            reliability_tier="orientation",
            fallback="",
        )
    with pytest.raises(ValidationError, match="fact evidence"):
        SourceAdapterSpec(
            adapter_id="bad-fact",
            name="Bad Fact",
            signal_class="authoritative_media",
            roles=[EvidenceRole.FACT_EVIDENCE],
            acquisition_mode=AcquisitionMode.MANUAL_IMPORT,
            reliability_tier="orientation",
            fallback="人工导入",
        )
