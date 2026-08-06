# Third-party Skill Audit: `wechat-article-search`

- Audit date: 2026-08-04
- Repository: `https://github.com/wuchubuzai2018/expert-skills-hub.git`
- Pinned commit: `c9307752f2744fecf6f62c243f32df9015c0c416`
- Skill path: `skills/wechat-article-search`
- Reviewed files: `SKILL.md` and the complete `scripts/search_wechat.js`
- Source checksums reviewed:
  - `SKILL.md`: SHA-256 `08967183d1fafe51a6e144281ad28b9607a319d1961c8744938a71d91c83d8d3`
  - `scripts/search_wechat.js`: SHA-256 `d75d427b888b3c7eeee4f6d6e34b5d120a17b371f07b28cf1af5ecb144246ffa`

## Intended project role

Use only as a **supplemental discovery source for WeChat Official Account articles**. It queries Sogou Weixin search and returns article titles, summaries, dates, account names, and intermediate or resolved links.

It does not search WeChat Channels / 视频号, does not supply video engagement metrics, does not collect article comments, and must not be counted as direct Video Accounts coverage.

## Installation and dependencies

The Skill instructs the operator to install `cheerio` globally with `npm install -g cheerio`. The script is CommonJS JavaScript and also uses Node built-ins `https` and `zlib`.

There is no package manifest beside the Skill, no pinned `cheerio` version, and no repository root or Skill-local license file was found during the audit. Consequently:

- do not run the global install instruction automatically;
- do not copy this third-party source into Git history until reuse terms are clarified;
- if approved later, place the pinned source at the lock-file install path and install a reviewed, pinned `cheerio` release in an isolated local package environment.

The project records Node.js 18 as its conservative minimum for probing; the upstream Skill itself does not declare an exact Node version.

## Network, cookies, and output

- Primary destination: `https://weixin.sogou.com`.
- Optional real-link resolution may follow/inspect Sogou intermediate responses and accept links only when they point to `mp.weixin.qq.com`.
- The script first requests Sogou to obtain cookies, parses response `set-cookie` values, and sends those cookies back to Sogou. It does not read Chrome login state.
- The resolver contains fixed non-secret baseline cookie values and may append the response `SNUID` cookie.
- User agents are randomly selected from a hard-coded browser/mobile list.
- No environment variables or API keys are read by the script.
- Standard output is JSON shaped as `{query, total, articles}`. Each article includes title, URL, summary, date fields, and source account. Diagnostics go to standard error.
- With `-o/--output`, the script writes UTF-8 JSON to the caller-supplied path without confining that path to a project directory. Project code must never pass unvalidated output paths.

## Request volume and failure behavior

- Maximum requested results: 50, with approximately ten results per Sogou page.
- Inter-page and per-link pauses are randomized between about 0.5 and 1.5 seconds.
- Request code retries transient failures; real-link resolution additionally retries and often falls back to the original Sogou link.
- Known failures: empty results, changed Sogou markup, decompression/parsing errors, anti-spider pages, blocked IP, unresolved real links, timeout, and partial results after a page failure.
- The upstream instructions explicitly warn against commercial or large-scale crawling and require compliance with website terms.

## Data-quality constraints

- Search rank is not equivalent to platform popularity.
- The output contains no likes, reads, shares, saves, or comments; therefore it cannot independently establish a “hot” grade.
- Relative dates are calculated at collection time and must be normalized while preserving collection timestamp.
- Intermediate Sogou URLs are valid provenance but may expire or fail later.
- HTML selectors and embedded timestamp parsing are brittle and need fixture coverage before use.

## Safety decision

Status: **audited but not installed; live calls disabled**.

A later supervised probe is acceptable only after dependency pinning, reuse-term review, explicit enablement, strict request caps, output-path confinement, raw-response provenance, and stop-on-challenge behavior are implemented. The project verifier performs no HTTP request and does not execute the Skill script.

## 2026-08-04 installation and capability probe record

- Installed only the pinned Skill subtree at `.local/third-party-skills/wechat-article-search` using a temporary sparse Git checkout of commit `c9307752f2744fecf6f62c243f32df9015c0c416`.
- Installed source-tree SHA-256: `a8970aa2bae0e4f1f0b78b3c5b3dcb92cff062db4f0f169a2200a0ac59ccef90`.
- No global npm installation was executed.
- Local observations: Node.js `v23.11.0` ready; npm `10.9.2` ready; the required `cheerio` package is missing from the Skill-local resolution path.
- Non-network capability probe `node --check .local/third-party-skills/wechat-article-search/scripts/search_wechat.js` passed.
- The script's `--help` path was not used because it initializes `cheerio` before argument handling; with the dependency absent it is not a safe independent help probe.
- No Sogou/WeChat HTTP request, cookie exchange, search, or output-file write was performed.
- Current decision: source installed and checksum-verified; local collection readiness is false until a pinned isolated dependency environment is approved; `real_calls_enabled` remains false.

## Supervised local runtime preparation — 2026-08-04

With explicit operator authorization to prepare the collection environment, the project installed `cheerio@1.2.0` under `.local/tools/wechat-article-search` using `npm install --ignore-scripts`. No global npm package was changed. The package reports MIT, its npm integrity is pinned in `skills/third_party.lock.yaml`, the Skill script passed `node --check`, and a local `cheerio.load()` probe passed with `NODE_PATH` pointed at the isolated dependency directory. An npm production dependency audit against `registry.npmjs.org` reported zero known vulnerabilities on 2026-08-04.

No Sogou Weixin or WeChat HTTP request was made during preparation. `real_calls_enabled` remains `false`; a first low-volume live query requires a separate, explicit collection authorization and must be recorded as supplemental WeChat Official Account evidence, never as WeChat Channels evidence.
