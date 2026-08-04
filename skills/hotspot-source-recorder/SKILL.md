---
name: hotspot-source-recorder
description: Use when converting raw hotspot collector results or approved manual imports into normalized, deduplicable, evidence-backed source records for daily research.
---

# Hotspot Source Recorder

## Inputs

- one raw result and its collection attempt;
- query group, platform, collection timestamp, adapter version, and raw-artifact path;
- any available title/text excerpt, author label, publication time, URL/ID, and engagement values.

## Normalization

Create a stable source ID. Record platform, source type, pillar candidates, query provenance, canonical/deep link, published and collected times, sanitized excerpt, engagement metrics, metric meanings, grade evidence, confidence, and raw artifact checksum/path. Preserve the distinction between reported, derived, and unavailable fields.

Deduplicate by platform ID/canonical URL first, then flag probable semantic duplicates without deleting their provenance.

## Outputs

Return one strict source record plus validation warnings, duplicate links, and a compact evidence summary. The record must allow a reviewer to trace every assertion to the original result or manual import.

## Quality Gate

Required provenance is present; timestamps identify their timezone/precision; URLs and IDs are attributable; metric labels are not conflated; **unknown metrics remain null**; and the **raw artifact** reference is immutable.

## Prohibited Behavior

Do not invent metrics, translate missing values to zero, infer cross-platform comparability, overwrite raw evidence, retain unnecessary personal identifiers, copy a full copyrighted post, rank final topics, or write scripts.

## Failure Degradation

Persist an incomplete draft with explicit missing fields and lower confidence. Reject records with no source identity or collection provenance. Keep parse/schema errors attached to the attempt rather than silently dropping them.

## User Actions

Return normalized records for approve, correct metadata, merge/split duplicates, reject a source, return, or hold. Only the research orchestrator may decide whether the daily report advances.
