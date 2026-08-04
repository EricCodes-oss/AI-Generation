---
name: daily-hotspot-research
description: Use when starting or revising the daily research step for the life-companion digital-human project, before content cleaning, ranking, topic planning, or script writing.
---

# Daily Hotspot Research

## Purpose

Produce one reviewable **《每日热点内容检索报告》** about current audience concerns. This is a research gate, not a content-generation step.

## Allowed Skills

- `hotspot-query-planner`
- `channels-hotspot-research`
- `hotspot-source-recorder`
- `audience-comment-insight`
- pinned collector `opinions-crawler`
- pinned collector `wechat-article-search`

Only invoke the six Skills listed above. Read `skills/third_party.lock.yaml`; never enable live calls, install software, open a login session, or exceed an approved capability without explicit operator authorization.

## Inputs

- research date and optional user emphasis/exclusions;
- three pillars: workplace/real-life pressure, child education/family communication, self-growth/life insight;
- 30-day query/topic history and prior failures;
- approved fixtures, imports, or collector capabilities;
- permanent V1 exclusion: **父母养老与照护压力**.

## Workflow

1. Build exactly one daily query plan with `hotspot-query-planner`.
2. Collect platform results with `channels-hotspot-research`; preserve partial success.
3. Normalize every accepted item with `hotspot-source-recorder`.
4. Select 5–8 A-grade sources and analyze 20–40 effective comments per source with `audience-comment-insight` when comments are available.
5. Compile the report, disclose gaps, and stop at the research gate.

## Outputs

Return a versioned report containing:

- query plan, time-window coverage, and cooldown decisions;
- 30–40 valid sources when available, grouped by platform and pillar;
- source evidence, engagement fields, confidence, and raw-artifact provenance;
- 5–8 A-grade sources with comment insight cards when approvable;
- platform success/failure table, missing metrics, limitations, and collection failures;
- observed audience situations, emotions, conflicts, questions, implicit needs, disliked expressions, and disagreement signals;
- a clear statement that this report contains research evidence only.

## Quality Gate

Approve only when provenance is complete, duplicates are flagged, time windows are visible, the eldercare exclusion holds, platform failures are disclosed, and evidence is sufficient for later cleaning. Target 30–40 valid sources, but never fabricate data to meet a quota.

## Prohibited Behavior

- **do not produce Top 3** recommendations or rank final topics;
- **do not write scripts**, hooks, finished copy, storyboards, or production prompts;
- do not copy platform posts or complete comments into downstream content;
- do not claim direct Douyin general-search/comment or WeChat Channels coverage unless the run proves that capability;
- do not silently continue to the next workflow step.

## Failure Degradation

Keep successful platforms, record each failure and attempted query, lower confidence, and request an approved manual import or later retry. A missing platform is a visible gap, not zero interest. If evidence is insufficient, return a draft report marked not approvable.

## User Actions

Present the report and wait for the user to **approve, revise, redo, return, or hold**. Apply feedback as a new revision. **wait for explicit user approval** before unlocking content cleaning and clustering.
