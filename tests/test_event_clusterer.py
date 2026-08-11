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
