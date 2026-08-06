---
name: audience-comment-insight
description: Use when analyzing sampled comments from selected high-value hotspot sources to identify audience situations, emotions, conflicts, questions, needs, and disliked expressions without profiling individuals.
---

# Audience Comment Insight

## Inputs

- 5–8 selected A-grade sources when available;
- 20–40 effective comments per source, sampled approximately as high-like 30%, lived experience 25%, help-seeking 20%, disagreement 15%, and latest 10%;
- comment IDs or hashes, source provenance, visible interaction fields, and collection timestamp.

## Analysis

For each source, synthesize anonymized evidence for: broad role/life-stage clue, concrete scene, emotion, inner conflict, explicit question, **implicit need** (being seen, accepted, comforted, explained, guided, or accompanied), failed attempts, disliked wording, and disagreement. Separate repeated signals from single anecdotes.

Retain only short natural-language fragments when essential for audit; **never copy a complete comment**. Replace usernames and direct identifiers with hashes or source-local references. **never infer exact demographics** such as exact age, income, diagnosis, location, or family status from weak clues.

## Outputs

Return an insight card per source with sample mix, evidence counts, representative paraphrases, tensions/minority views, confidence, privacy notes, and provenance back to comment IDs/hashes.

## Quality Gate

The sample is diverse, claims are traceable, minority disagreement is visible, inference strength is labeled, personal data is minimized, and insights describe needs rather than caricaturing users.

## Prohibited Behavior

Do not reproduce comments verbatim at length, expose usernames, diagnose mental health, infer protected/sensitive attributes, treat high-like comments as universal truth, convert comments directly into finished copy, recommend Top 3, or write scripts.

## Failure Degradation

If comments are unavailable or too sparse, state that explicitly, reduce confidence, and rely only on post-level evidence. Do not fabricate sentiment, fill quota with duplicates, or infer a silent audience's views.

## User Actions

Return cards for approve, revise taxonomy, remove sensitive evidence, resample, reject, return, or hold. Do not unlock ranking or script work.
