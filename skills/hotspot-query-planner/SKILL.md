---
name: hotspot-query-planner
description: Use when preparing or revising the daily cross-platform search plan for the three approved life-companion content pillars before any hotspot collection begins.
---

# Hotspot Query Planner

## Inputs

- date, approved pillars, platform targets, and 50%/35%/15% time-window shares for 72 hours/7 days/30 days;
- previous 30 days of queries, scenes, produced topics, empty results, and user directives;
- excluded themes, including eldercare and **父母养老与照护压力**.

## Planning Rules

Create **exactly 9 core query groups**, **three per content pillar**. Each group combines a person/pressure signal, a concrete scene, an emotion or conflict, and platform-aware language. Do not reduce the plan to generic “心灵鸡汤” queries.

Permit at most three evidence-led expansions, each with parent query and reason. Enforce:

- exact-query cooldown: 7 days;
- same-scene non-consecutive window: 3 days;
- terms with two consecutive empty runs: **14-day cooldown**;
- recently produced topics: de-prioritize across the 30-day history.

## Outputs

Return query-group IDs, pillar, intent, expressions per platform, time window, target count, history decision, exclusions, and optional expansion metadata. Do not execute collectors.

## Quality Gate

The plan has nine balanced core groups, no more than three expansions, explicit platform wording, recorded history checks, correct time shares, and no excluded pillar.

## Prohibited Behavior

Do not write scripts, recommend Top 3 topics, copy a viral phrase as a finished query set, bypass cooldowns without recording a user override, or introduce eldercare as a pillar.

## Failure Degradation

If history is missing, mark cooldown confidence low and produce a conservative plan without pretending de-duplication occurred. If one platform lacks a searchable capability, retain the research intent and mark it for an approved adapter or manual import.

## User Actions

Return the plan for approve, revise, redo, return, or hold. Collection starts only after the plan is accepted by the current research run.
