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
    shared_alias = bool(_matched_aliases(left, aliases) & _matched_aliases(right, aliases))
    return min(1.0, jaccard + (0.50 if shared_alias else 0.0))


def _event_key(members: Sequence[HotspotRecord], aliases: dict[str, list[str]]) -> str:
    shared_aliases = set.intersection(*(_matched_aliases(item.title, aliases) for item in members))
    if shared_aliases:
        return "alias:" + "|".join(sorted(shared_aliases))
    anchor = min(members, key=lambda item: (item.captured_at, item.record_id))
    return "anchor:" + _canonical_text(anchor.title, aliases)


def cluster_events(
    records: Sequence[HotspotRecord], *, aliases: dict[str, list[str]]
) -> list[EventCluster]:
    natural = [item for item in records if item.content_nature is ContentNature.NATURAL]
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
            similarity = _similarity(natural[left].title, natural[right].title, aliases)
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
