---
name: daily-hotspot-research
description: Use when starting or revising daily real-hotspot research before the manual hotspot confirmation gate or managed-mode automatic topic selection.
---

# Daily Hotspot Research

## Purpose

Produce one traceable daily Top 3 hotspot review from real platform evidence. This Skill owns research orchestration through ranking, but it must stop before script writing in manual mode.

## Allowed Skills

- `hotspot-query-planner`
- `channels-hotspot-research`
- `hotspot-source-recorder`
- `audience-comment-insight`
- `hotspot-ranking-review`
- pinned collector `opinions-crawler`
- pinned collector `wechat-article-search`

Only invoke the seven Skills listed above. Read `skills/third_party.lock.yaml`; never enable live calls, install software, expose browser credentials, or exceed an approved capability.

## Inputs

- research date, optional user topic, emphasis, and exclusions;
- target platforms: Douyin, WeChat Channels, and Xiaohongshu;
- three pillars: workplace/real-life pressure, child education/family communication, self-growth/life insight;
- 30-day query/topic history and prior failures;
- approved browser envelopes, fixtures, imports, authority evidence, or verified collector capabilities;
- permanent V1 exclusion: **父母养老与照护压力**.

## Workflow

1. Build the daily query plan with `hotspot-query-planner`.
2. Collect only visible, public evidence with `channels-hotspot-research`; preserve partial success and per-platform states.
3. Normalize every accepted item with `hotspot-source-recorder`.
4. Analyze comments with `audience-comment-insight` only when comments are visibly available and approved for collection.
5. Deduplicate, verify, risk-filter, rank, and prepare at most three cards with `hotspot-ranking-review`.
6. Persist the report and submit the manual task to `HOTSPOT_REVIEW` without choosing a candidate.

## Outputs

Return a versioned hotspot report containing:

- query plan and 72-hour/7-day window decision;
- platform status, source links, timestamps, visible engagement fields, and `null/unknown` gaps;
- conservative duplicate and event-cluster decisions;
- authority verification, conflict/risk exclusions, audience insight, and ranking breakdown;
- zero to three eligible Top 3 review cards;
- watermark/authorization-safe production-media recommendation;
- a clear statement that manual mode is waiting at `HOTSPOT_REVIEW`.

## Quality Gate

Approve the research result only when provenance is complete, unavailable values remain unknown, target-platform failures are disclosed, the eldercare exclusion holds, every ranked candidate passes evidence and safety rules, and the report contains no fabricated candidate or metric.

## Prohibited Behavior

- **do not write scripts**, hooks, final narration, storyboards, TTS, avatar video, or Seedance prompts;
- do not auto-select or approve a Top 3 candidate in manual mode;
- do not claim direct platform capability unless the current run proves it;
- do not use Official Account articles as WeChat Channels evidence;
- do not copy full posts, videos, transcripts, or comments into downstream content;
- do not silently continue beyond `HOTSPOT_REVIEW`.

## Failure Degradation

Keep successful platforms, record each failure and exclusion, lower confidence, and request an approved manual import or later retry when needed. Expand from 72 hours to 7 days only for candidate shortage. If evidence remains insufficient, return the actual eligible count and stop before scripts.

## User Actions

Present the Top 3 report and wait for the user to **approve, revise, redo, return, or hold**. Apply feedback as a new revision. **wait for explicit user approval** of one hotspot before unlocking script generation.
