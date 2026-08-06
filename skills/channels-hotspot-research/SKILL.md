---
name: channels-hotspot-research
description: Use when executing an approved daily query plan across available social platforms, fixtures, or authorized manual imports while preserving platform-specific capability limits.
---

# Channels Hotspot Research

“Channels” means collection channels generally; it does not imply automatic 微信视频号 support.

## Inputs

- approved query plan and platform quotas;
- collector lock and audit reports;
- explicit live-call authorization state;
- available fixtures, exports, manual links, and authenticated capabilities.

## Collection Rules

Aim for valid-source targets: Douyin 8–10, WeChat Channels 6–8, Xiaohongshu 8–10, Zhihu/Weibo/Bilibili and similar sources 4–6, and WeChat Official Accounts 3–5. Apply conservative request caps and preserve raw output.

Use `opinions-crawler` only for commands verified at runtime. Its pinned documentation does not establish Douyin general video search/comments or WeChat Channels support. Use `wechat-article-search` only for Official Account article discovery, never as Video Accounts evidence. Accept approved manual imports when automation is unavailable.

## Outputs

Return per-attempt query, platform, adapter, capability, timestamp, raw-artifact location, result count, latency/error, and whether the result is complete, partial, imported, or unavailable.

## Quality Gate

Every result maps to an approved query and raw artifact. **disclose every platform failure**, quota shortfall, challenge, login requirement, missing operation, and partial page.

## Prohibited Behavior

- **never fabricate platform coverage** or convert another platform's evidence into the missing platform;
- never evade captchas, anti-bot controls, access restrictions, or platform terms;
- never enable a disabled real collector, log in, or install dependencies without explicit authorization;
- never claim **WeChat Channels** data from Official Account search;
- never rank topics or write scripts.

## Failure Degradation

Stop the affected adapter on challenge or repeated failure, retain successful platforms, and emit a structured failure plus a manual-import request. Missing data remains unknown, not zero. Do not hide the failure to satisfy quotas.

## User Actions

Return the collection ledger for approve, revise query, retry an approved capability, attach a manual import, return, or hold. Do not advance the overall workflow yourself.
