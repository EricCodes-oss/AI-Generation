"""Canonical identities for deciding whether evidence references are independent."""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING_QUERY_KEYS = {"from", "share_token", "source", "spm"}


def canonical_source_reference(value: str) -> str:
    """Normalize a URL or opaque reference without inventing source identity."""

    reference = value.strip()
    if not reference:
        return ""
    parts = urlsplit(reference)
    if not parts.scheme or not parts.netloc:
        return reference.casefold().rstrip("/")
    query = [
        (key, item)
        for key, item in parse_qsl(parts.query, keep_blank_values=True)
        if key.casefold() not in _TRACKING_QUERY_KEYS and not key.casefold().startswith("utm_")
    ]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(
        (
            parts.scheme.casefold(),
            parts.netloc.casefold(),
            path,
            urlencode(sorted(query)),
            "",
        )
    ).casefold()


def independent_source_reference_count(references: list[str]) -> int:
    """Count nonblank canonical source identities."""

    canonical = {canonical_source_reference(reference) for reference in references}
    canonical.discard("")
    return len(canonical)
