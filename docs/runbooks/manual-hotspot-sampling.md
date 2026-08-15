# Manual cross-platform hotspot sampling

This runbook is research-only. It does not generate scripts, speech, avatar video, insert media, or composites.

## Safety checks

1. Use the current sampling date for a new run (for example `2026-08-11`). Never reuse an earlier business date to imitate fresh evidence.
2. Confirm the matching `workspace/days/<date>/task.json`, if it exists, is `fact_screened` or `topic_script_review` and has no `topic_script` approval.
3. Do not run `mark-tts`, `mark-anchor`, `mark-media`, or `mark-compositing`.
4. Keep the C2-Pro Candidate 2 host image and `host_profile` unchanged; verify SHA256 `939324593eb718cd2a39be4c171f74178a6a48442f7e0d61afe8a875011e8a47` before refresh.

Run the exact check and stop on mismatch:

```bash
test "$(shasum -a 256 'output/host-v12-c2-pro/GPT-Image-2-Pro-C2-Pro-主持人最终选定.png' | awk '{print $1}')" = \
  "939324593eb718cd2a39be4c171f74178a6a48442f7e0d61afe8a875011e8a47"
```

## Import T0, T+10, and T+20

For canonical snapshots:

```bash
PYTHONPATH=src:. .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-import-snapshot --date 2026-08-10 --format canonical \
  --file tmp/hotspot-sampling/t0.json
sleep 600
PYTHONPATH=src:. .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-import-snapshot --date 2026-08-10 --format canonical \
  --file tmp/hotspot-sampling/t1.json
sleep 600
PYTHONPATH=src:. .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-import-snapshot --date 2026-08-10 --format canonical \
  --file tmp/hotspot-sampling/t2.json
```

For a TopHub structured export, include immutable capture metadata and an optional failure map whose JSON shape is `{"bilibili": ["api returned -352", "tmp/raw/bilibili.json"]}`:

```bash
PYTHONPATH=src:. .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-import-snapshot --date 2026-08-10 --format tophub \
  --file tmp/hotspot-sampling/tophub_structured.json --snapshot-id t0 \
  --captured-at 2026-08-10T19:47:17+08:00 --timezone Asia/Shanghai \
  --failures tmp/hotspot-failures.json
```

The CLI only imports saved local evidence. It does not perform network collection. Snapshot files are immutable: importing an existing snapshot ID fails rather than overwriting evidence.

## Discover event IDs and import human review

Build once to expose rejected cluster IDs. Missing review data is an explicit rejection, not an error or zero score:

```bash
PYTHONPATH=src:. .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-build-report --date 2026-08-10
PYTHONPATH=src:. .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-status --date 2026-08-10
```

Prepare three auditable review files:

- `verification.json`: `CandidateVerification` objects for fact safety;
- `editorial-signals.json`: `EditorialSignals` objects for click, conflict, relevance, visuals, and explanation;
- `short-video-evidence.json`: `EventShortVideoEvidence` objects with separate Douyin and Xiaohongshu evidence. Preserve source counts, observed views/likes/comments/shares/saves, comment samples, emotion/conflict signals, hook patterns, visual materials, suitability score, and raw evidence paths. A restricted or failed platform must retain `collection_status` and `failure_reason`; never convert missing data to zero heat.

Rebuild after importing them:

```bash
PYTHONPATH=src:. .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-import-review --date 2026-08-10 \
  --verification tmp/hotspot-sampling/verification.json \
  --editorial-signals tmp/hotspot-sampling/editorial-signals.json \
  --short-video-evidence tmp/hotspot-sampling/short-video-evidence.json
PYTHONPATH=src:. .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-build-report --date 2026-08-10
```

Read both:

- `workspace/hotspots/2026-08-10/reports/candidate-report.json`
- `workspace/hotspots/2026-08-10/reports/candidate-report.md`

The report is limited to three candidates and uses the versioned `viral-v1.1` rules. Rank-board virality and short-video fit are separate layers. A candidate may remain visible with `director_action=watch`, but it can become the director recommendation and enter `hotspot-refresh` only when both Douyin and Xiaohongshu evidence pass their source, comment, engagement/observed-interaction, and suitability thresholds. If evidence is missing or restricted, the platform score stays unknown rather than zero. If `outcome` is `no_qualified_hotspot`, stop. Do not substitute a lower-quality topic or describe an ordinary topic as the hottest topic on the internet.

## Refresh only after reviewing the qualified report

Only run this command after a human has reviewed a report whose outcome is `qualified_candidates` **and** whose `director_recommendation_event_id` is non-null. A watch-only report cannot refresh production:

```bash
PYTHONPATH=src:. .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-refresh --date 2026-08-10 \
  --archive-reason "旧‘大学新生电脑涨价’方案传播性不足，改用跨平台连续采样候选" \
  --confirmed-host-profile output/manual-run-2026-08-10/planning/host-profile.json
```

This archives the old candidates, script, and media plan; preserves the host; clears the active selection/script/media plan; and remains at `topic_script_review`:

```bash
PYTHONPATH=src:. .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  status --date 2026-08-10
```

The expected state is `topic_script_review`, with the C2-Pro Candidate 2 `host_profile`, no selected topic, no script, no media plan, and no new artifacts. User confirmation is still required before any paid generation.

## 新流程：Editorial Opportunity v2 双漏斗选题门

原有 `viral-v1.1` 继续负责 T0、T+10、T+20 连续采样、事件聚类和短视频平台适配判断，作为第一漏斗的一部分。V5 的最终选题入口改为 `editorial-opportunity-v2.0`：先发现注意力，再判断这个话题是否真的值得做。

### 漏斗一：发现注意力

每轮目标流程：

```text
20—40 个原始话题
→ 12—20 个聚类事件
→ 8—12 个内部评审事件
→ 0—8 个真正合格的用户候选
```

六类信号必须尽量交叉：

1. 国内榜单：百度、头条、微博、抖音、小红书、快手、知乎、B站；
2. 权威媒体与官方账号：新华网、人民日报、央视新闻、中国青年报、政府和第一方；
3. 搜索需求：解释型、问题型和“为什么现在”查询；
4. 社交讨论：X、Reddit、评论区中的重复问题、争议和情绪变化；
5. 视频传播：上传速度、相对账号基线的异常播放、字幕与评论问题；
6. 垂直社区：GitHub、Hacker News、影视、消费、教育和普通人社区。

百度、头条或任何平台都不能单独证明“这是今日最热”。注意力信号不能充当事实证据。

### 漏斗二：判断内容价值

内部评审必须写清：

- 为什么是今天；
- 最强反差、悬念、冲突或知识缺口；
- 普通人为什么关心；
- 观众看完能获得什么；
- 一句有事实含量的前三秒开场；
- 核心事实来源和未解决冲突；
- 真实素材、连续时长、清晰度、年代和获取风险；
- 预计热度寿命与是否已经错过制作窗口。

评分固定为：真实热度 30、内容吸引力 35、事实可靠性 20、视频潜力 15。单平台伪热点、无可靠核心事实、旧闻回流、空洞标题、纯情绪无解释、无相关素材、核心事实冲突、高风险断言证据不足、营销账号独占传播或必须靠失真标题才能点击的题目必须淘汰。

### 构建导演候选报告

准备 `EditorialOpportunity` JSON 列表后执行：

```bash
PYTHONPATH=src:. .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  editorial-build-report --date 2026-08-13 \
  --file tmp/editorial-opportunities/2026-08-13/opportunities.json

PYTHONPATH=src:. .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-pool-status --date 2026-08-13
```

系统输出：

```text
workspace/hotspot-selections/2026-08-13/editorial-opportunity-pool.json
workspace/hotspot-selections/2026-08-13/candidate-pool.json
workspace/hotspot-selections/2026-08-13/candidate-pool.md
```

`candidate-pool.md` 是导演选题卡，必须包含最新进展、为什么是今天、跨平台热度证据、反差或悬念、普通人关联、观看回报、前三秒开场、可靠事实来源、素材与年代风险、热度寿命和导演评级。

用户可见候选最多 8 条，目标为 3—8 条，但允许少于 3 条。禁止为了数量或类别覆盖补入弱候选。没有 S 级时报告必须显示“暂无 S 级选题”。

### 用户只确认一次选题

用户与导演共同评估后执行：

```bash
PYTHONPATH=src:. .venv/bin/python -m avatar_pipeline.cli --workspace workspace \
  hotspot-select --date 2026-08-13 --candidate-id odyssey \
  --actor owner --reason "共同评估后确认"
```

`topic-selection.json` 生成前禁止初始化新的 V5 生产任务。确认后，稿件、TTS、数字人、素材、剪辑和 QC 按既定流程继续，不再逐步询问，除非出现事实冲突、素材权利风险或硬质量门失败。

### 外部工具与许可边界

- TrendRadar、RSSHub 以外部服务/API 方式接入，不直接复制 GPL/AGPL 源码；
- X 官方 API 优先，Xquik 只作为可选适配器；
- YouTube Data API 用于官方视频发现和上传速度信号；
- Google Trends 官方能力不可用时只启用实验性适配器，不能作为唯一生产依据；
- The News、GDELT 用于国际新闻方向发现，不替代最终事实核验；
- ScrapeCreators 可用于异常帖子、评论问题和字幕研究，但不能成为唯一依赖；
- 所有外部来源失败时必须回退到本地快照或人工导入。

所有候选和素材不得虚构链接、发布时间、排名、播放量或互动数据。可下载、无水印或允许保留水印，均不自动等于已获得转载授权。

## 下游插播采用导演动态决策

热点确认后，素材规划不得套用固定“三段插播”模板。插播数量、单段时长和总占比由题材、稿件信息段、素材连续性、视觉质量和最终观看效果决定。默认优先少而长、语义连贯的素材块，避免频繁短切；`news-v5-guidance` 输出的 1—5 段、4.5—12 秒、20%—45% 只是复审参考，不是生产配额。硬门只约束事实与语义映射、素材哈希和批准状态、正向连续播放、无倒放循环、时间线连续以及完整主持人结尾。

## 普通人自然瞬间：强制准入门（2026-08-15 起）

当候选属于 `ordinary_life_moment` 时，必须先完成 `ordinary_moment_assessment`，再进入用户候选池。判断原则不是“内容看起来温暖”，而是：

> 事情先在普通人的生活中自然发生，镜头只是恰好记录下来；不能为了拍摄内容而设计事情。

### 必须同时满足

1. 拍摄者、主人公不是职业博主、网红或 MCN 策划账号；
2. 事件不是拍摄者主动发起，且在拍摄意图之外本来就会发生；
3. 能追溯原始记录者或原始发布者；
4. 有连续现场画面，不能只靠媒体拼接后的几秒片段；
5. 能指出自然反应证据，例如未看镜头、真实环境声、连续动作或即时对话；
6. `staging_risk <= 0.35`；
7. 热度、真实性和素材可用性分别核验，不能用媒体转发量代替原视频热度。

### 优先记录形态

- 家庭手机随手拍；
- 路人偶遇；
- 行车记录仪；
- 公共场所或店铺监控；
- 学校、医院、车站、婚礼、街头等日常现场。

### 一票否决

- 职业博主、网红或团队账号主导；
- 送礼、挑战、帮助陌生人、请人吃饭等创作者主动策划事件；
- 固定栏目、预设台词、多人配合表演、剧情短剧；
- 镜头提前等待表演动作，或当事人持续面向镜头输出；
- 无法追溯原始记录者、只有二次剪辑；
- 摆拍风险高于 0.35；
- 内容自然但没有足够传播热度，或热度高但真实性无法核验。

允许本轮输出 0 条。宁可明确写“未发现同时达标内容”，也不得用网红策划内容或弱热度内容补足数量。
#### 本项目所说的“普通人自然瞬间”不是泛正能量

筛选顺序必须是“普通人真实日常”在前，“温暖感”在后，“热度”最后核验：

1. **账号先过门：** 原始发布者应是个人生活记录账号。职业博主、网红、MCN、机构栏目、固定街访或固定暖心栏目，即使事件真实也不进入该类别。
2. **人物先过门：** 画面主体必须是正在生活的普通人，而不是由创作者带领、采访、挑战、送礼或制造情境的参与者。
3. **场景先过门：** 事件发生于原本就存在的家庭、邻里、通勤、店铺、车站、医院、校园、婚礼或街头日常。拿掉相机之后，事情仍会自然发生。
4. **情感必须在动作中自然流露：** 至少记录一条可观察证据，例如下意识搀扶、默默等待、自然拥抱、临时回头帮忙、家人间未经提示的关心。标题或配乐宣称“感动”不能作为证据。
5. **镜头只是记录者：** 当事人不持续看镜头、不按口令行动、没有固定开场或结尾话术；优先采用连续家庭随手拍、监控、行车记录仪或路人偶遇。
6. **最后才看热度：** 通过上述真实性门槛后，再核验原视频点赞、评论、收藏、分享和跨平台自然传播。不得因为热度高而降低普通人、自然性和可回溯要求。

导演复核时必须能明确回答：这是“一个普通人的生活被恰好记录”，还是“一个内容创作者拍了一条普通人题材的视频”？只有前者可以进入候选池。
