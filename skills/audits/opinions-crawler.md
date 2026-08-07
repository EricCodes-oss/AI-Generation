# Third-party Skill Audit: `opinions-crawler`

- Audit date: 2026-08-04
- Repository: `https://github.com/infometa/workbuddyskills.git`
- Pinned commit: `2bd6db6fe5678650e8272adafabbdceba61c3544`
- Skill path: `experts/databrain-opinion-expert/skills/opinions-crawler`
- Reviewed files: `SKILL.md`, all three files under `references/`, and `scripts/setup.sh`
- Source checksums reviewed:
  - `SKILL.md`: SHA-256 `66a9489d61433b578c248d1b50210b8b6d5e0b46cac86812d7cd4e1ac0a4ac4a`
  - `scripts/setup.sh`: SHA-256 `07a56749fd419f8bbf2228e37fa624db402a301014602d3770f396fa85d13167`

## Intended project role

Use as a **capability-dependent collector**, never as proof that every named platform supports every operation. It may provide discovery, metadata, and comments for platforms whose current OpenCLI adapter exposes those commands. Project-owned normalization and provenance recording remain mandatory.

It is not a scoring, rewriting, topic-ranking, or script-writing Skill.

## Installation and side effects

The supplied setup script:

1. checks Node.js major version and requires Node.js 20 or newer;
2. runs `npm install -g @jackwener/opencli` if `opencli` is absent;
3. runs `opencli doctor`, which can start a local daemon;
4. instructs the operator to download and load the OpenCLI Browser Bridge Chrome extension;
5. attempts a global `pip install appstore-review-cli` or `pip3 install ...` even though app-store collection is unrelated to this project.

These operations modify global npm/Python environments and Chrome configuration. The project therefore **must not execute `scripts/setup.sh`**. If approved later, install only the pinned Skill source into the declared local install path and provision OpenCLI separately with an explicit version and operator review.

No root or Skill-local license covering this Skill was found at the pinned repository path during the audit. Third-party contents must not be copied into this repository until reuse terms are clarified. The lock file records source coordinates instead.

## Runtime, login, and network behavior

- Runtime: Node.js >= 20, npm, OpenCLI, Chrome/Chromium, OpenCLI Browser Bridge.
- Local service: documentation identifies `OPENCLI_DAEMON_PORT`, default `19825`; `opencli doctor` may start the daemon.
- Environment variables documented by the source include OpenCLI daemon configuration; no project secrets should be placed in the lock or reports.
- Authentication: OpenCLI reuses the active Chrome login state. The operator must log into each target site in Chrome. Platform cookies remain browser-managed, but collection commands act with that session.
- Network destinations: the selected platform websites and OpenCLI release/npm infrastructure during setup. Exact live destinations depend on the adapter invoked and must be recorded per run.
- Filesystem writes: global npm installation, optional global Python installation, downloaded/unpacked browser extension, OpenCLI local configuration/cache/daemon state, and any shell redirection selected by the caller.

## Output and rate control

- The Skill recommends `-f json` for structured output; OpenCLI also advertises table, CSV, YAML, and Markdown formats.
- Output schemas differ by platform and command. Treat raw JSON as untrusted adapter output and preserve it before normalization.
- The examples recommend sleeping roughly 3 seconds during repeated comment collection; the operational notes recommend 2–5 second request spacing and small batches. Project adapters must enforce their own conservative throttling and stop on challenge/rate-limit responses.

## Confirmed useful coverage at the pinned Skill revision

The documentation explicitly shows useful commands for Bilibili, Weibo, Xiaohongshu, Zhihu, Toutiao, Jike, YouTube, Reddit, and other sources. Search, detail, metrics, and comment support vary by platform.

### Important exclusions and non-assumptions

- **Douyin:** documented commands are creator profile, the authenticated creator's videos, hashtag search, hashtag hot, and creator video stats. The documented flow requires login to `creator.douyin.com`. Do **not** assume general Douyin video keyword search, arbitrary-video detail, or comment collection.
- **WeChat Channels / 视频号:** no documented adapter or command was found. Coverage is **not available by assumption** and requires a separate user-provided capability or manual/authorized source.
- A platform named in the Skill description does not guarantee all operations.
- `weibo hot` is documented as returning 404 at that revision.
- `zhihu hot` may return empty data.
- `reddit hot` may return parsing errors.
- DOM/API changes, expired login state, captchas, anti-bot challenges, permission failures, empty responses, and schema drift are expected failure modes.

## Safety decision

Status: **audited but not installed; live calls disabled**.

Safe for a later, supervised local capability probe only after:

- licensing/reuse terms and the exact OpenCLI version are reviewed;
- global installer side effects are replaced by an isolated install procedure;
- Chrome extension and platform-login use receive explicit operator approval;
- each adapter command is allowlisted;
- raw-output redaction, throttling, and run-level provenance are active.

The verifier in this project performs only static/local prerequisite checks. It never invokes `opencli`, starts a daemon, opens Chrome, logs in, or accesses a platform.

## 2026-08-04 installation and capability probe record

- Installed only the pinned Skill subtree at `.local/third-party-skills/opinions-crawler` using a temporary sparse Git checkout of commit `2bd6db6fe5678650e8272adafabbdceba61c3544`.
- Installed source-tree SHA-256: `a6c85c151688dfa1045e707330b7818dd25d62a5b52673c366ea27740ff7bb95`.
- The upstream `scripts/setup.sh` was **not executed**.
- Local observations: Node.js `v23.11.0` ready; npm `10.9.2` ready; Google Chrome present; `opencli` missing.
- OpenCLI Browser Bridge and authenticated platform sessions remain `manual_action_required`; they were not inspected or changed.
- Capability probe status: `missing`. The proposed safe command is `opencli --version`, but it could not run because the executable is absent.
- No OpenCLI daemon, Chrome automation, login, search, comment collection, or platform request was started.
- Current decision: source installed and checksum-verified; local collection readiness is false; `real_calls_enabled` remains false.

## Supervised local runtime preparation — 2026-08-04

With explicit operator authorization to prepare the collection environment, the project installed `@jackwener/opencli@1.8.6` under `.local/tools/opencli` using `npm install --ignore-scripts`. No global npm package, shell completion, OpenCLI daemon, browser session, login, or platform command was started. The package reports Apache-2.0, its npm integrity is pinned in `skills/third_party.lock.yaml`, and an npm production dependency audit against `registry.npmjs.org` reported zero known vulnerabilities on 2026-08-04.

The matching official GitHub release `v1.8.6` supplied `opencli-extension-v1.0.22.zip`. The archive was downloaded to `.local/tools/opencli-extension`, verified against the release digest `9d2e3d053948beab5d97124aa79b1532d2122e33e461eca56cac113afd33207a`, and extracted locally. The manifest requests `debugger`, `tabs`, `cookies`, `activeTab`, `alarms`, `storage`, `tabGroups`, `downloads`, and `<all_urls>` access. Because this is broad browser/account access, loading or enabling the extension remains an explicit manual operator action. Platform login state also remains unverified, and `real_calls_enabled` remains `false`.

## 2026-08-07 Chrome read-only platform capability probe

With the operator's existing authorization, a minimal read-only Chrome probe was performed without exporting or reading browser credentials and without liking, commenting, collecting, following, messaging, publishing, or modifying any account.

Observed platform states:

- **Douyin:** `ready` for the public `https://www.douyin.com/hot` page. The rendered page exposed a current hot list, topic links, visible heat values, hot videos, visible engagement values, author display names, and relative/date labels. This proves a viable read-only public-page collection surface; it does not prove general keyword search, comments, or arbitrary private creator data.
- **Xiaohongshu:** `ready` for the authenticated public Explore feed at `https://www.xiaohongshu.com/explore`. The rendered page exposed note links, note titles, author display names, and visible engagement values. This proves a viable read-only feed surface; recommendation bias and missing publication times must remain explicit limitations.
- **WeChat Channels / 视频号:** `login_required` for `https://channels.weixin.qq.com/platform`, which redirected to the Video Accounts Assistant login page and displayed a login control. No stable public hot-list or keyword-search surface was verified. Until the user signs in and a safe read-only search surface is proven, production collection must use `manual_assist_required` for Video Accounts evidence rather than substituting Official Account articles.

No CAPTCHA, challenge, rate-limit page, interaction, platform-media download, Cookie/Token/password access, or credential export occurred. The probe created no repository data. Because the pinned `opinions-crawler` runtime/OpenCLI adapter itself was not verified end-to-end and Video Accounts remains unavailable, `real_calls_enabled` stays `false`.

## Current repository-state correction — 2026-08-07

A filesystem recheck of the active worktree and repository root found no `.local/third-party-skills/opinions-crawler`, `.local/bin/opencli`, OpenCLI runtime package, or unpacked Browser Bridge files. The 2026-08-04 installation notes above are retained as historical records, but they do not describe the current checkout. `skills/third_party.lock.yaml` therefore marks this Skill `installed: false`, its package capability probe `missing`, and `real_calls_enabled: false`.

The separate Chrome page probe remains useful as an Agent-controlled browser capability, not as proof that this pinned third-party Skill or its OpenCLI adapter is installed or enabled.
