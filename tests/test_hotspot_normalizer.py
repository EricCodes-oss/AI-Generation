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
