---
name: hotspot-ranking-review
description: Use when normalized multi-platform hotspot evidence must be deduplicated, verified, risk-filtered, ranked, and prepared for the manual hotspot confirmation gate.
---

# Hotspot Ranking Review

## Inputs

- normalized evidence from Douyin, WeChat Channels, and Xiaohongshu;
- per-platform collection status and visible metrics;
- explicit event keys for conservative cross-platform clustering;
- official or authoritative verification evidence;
- current time, audience-fit signals, risk flags, and media-clearance metadata.

Default to the latest **72 hours**. Expand to **7 days** only when fewer than three eligible clusters remain.

## Ranking Workflow

1. Deduplicate within a platform by content ID or canonical URL.
2. Cluster across platforms only when records share an explicit event key. Similar emotions or themes are not enough.
3. Admit a cluster only when it appears on **at least two target platforms**, or when one platform shows relatively high heat and the event has **official or authoritative verification**.
4. Reject unverified, conflicting, malicious, privacy-invasive, unsafe, or otherwise high-risk content.
5. Normalize heat within each platform and time window. Score platform-relative heat 35%, cross-platform resonance 25%, recency 15%, comment quality 10%, audience fit 10%, and source completeness 5%.
6. Return at most three review cards. If the 7-day fallback still has fewer than three eligible clusters, return only the real eligible count.

## Outputs

Return zero to three review cards containing:

- rank, title, event key, score, and score breakdown;
- every target-platform source link and visible metric;
- official or authoritative verification summary;
- unavailable fields rendered as `null/unknown`;
- audience insight, risk notes, recommended speaking angle, and source gaps;
- production-media recommendation, defaulting to a Seedance 2.0 non-replicative AI illustration when cleared source media is unavailable.

## Quality Gate

Every admitted card satisfies one of the two evidence thresholds, has no unresolved fact conflict or disqualifying risk, preserves provenance, and never treats unavailable engagement values as zero. All claims must be traceable to platform or authority evidence.

## Prohibited Behavior

- **do not estimate** hidden likes, comments, favorites, shares, views, demographics, or cross-platform equivalence;
- do not invent a third candidate, silently widen beyond 7 days, or promote an unverified rumor because it is popular;
- do not treat WeChat Official Account articles as WeChat Channels evidence;
- do not place media with a watermark, platform logo, account identifier, QR code, or unclear authorization into production;
- do not remove, crop, cover, blur, or erase a watermark;
- do not write the final script or approve a candidate on the user's behalf in manual mode.

## Failure Degradation

Keep eligible clusters and disclose platform failures, missing metrics, time-window expansion, authority gaps, and exclusion reasons. Return zero to two candidates honestly when evidence is insufficient. If no cluster qualifies, stop before script generation.

## User Actions

In manual mode, present the review cards and wait for the user to choose one, revise the search, retry an approved platform capability, attach evidence, return, or hold. The selected candidate may advance only through the existing hotspot approval command.
