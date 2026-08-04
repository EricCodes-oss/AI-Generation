# 数字人人生陪伴 IP 系统实施路线图

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement each phase plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将已确认的设计拆成六个可独立验收的实施阶段，最终形成每天一条、三平台同成片的数字人视频生产系统。

**Architecture:** 系统采用 Python 包实现领域模型、任务状态机、Skill 适配器和命令行编排；媒体处理使用 FFmpeg/ffprobe；外部数字人、TTS 和 Seedance 2.0 通过显式契约接入。每个阶段先提供可测试的本地能力，再接入真实外部服务，避免在接口未验证时消耗生成额度。

**Tech Stack:** Python 3.11+、Pydantic 2、PyYAML、pytest、Ruff、FFmpeg 7+、JSON/YAML 文件存储（V1）。

## Global Constraints

- 每天只生产 1 条 35–50 秒视频，同一成片发布抖音、视频号和小红书。
- 输出规格固定为 9:16、1080×1920、无平台水印。
- 第一阶段内容仅包含职场打拼与现实压力、子女教育与家庭沟通、自我成长与人生感悟。
- “父母养老与照护压力”不进入 V1。
- 选题、脚本、成片必须经过三个人工确认点。
- 独立 TTS 音频是最终主音轨；图片 + TTS 生成数字人视频是主模式。
- A-roll 数字人占 55%–65%，B-roll Seedance 场景占 35%–45%。
- 不搬运热门文案，不自动绕过平台限制，不自动无审核发布。
- 外部生成 Skill 在能力核验前不得批量消耗额度。

---

## 阶段划分

### Phase 1：项目基础与每日任务编排

**交付物：** 可安装的 Python 项目、配置模型、每日任务数据模型、状态机、JSON 仓库、三个人工审批命令、外部 Skill 契约和基础测试。

**详细计划：** `docs/superpowers/plans/2026-08-04-phase-1-foundation.md`

**验收：** 可以创建某日任务、写入 Top 3、选择 Top 1、登记脚本与质检结果，并且非法越级审批会被拒绝。

### Phase 2：平台研究、清洗与 Top 3 排名

**交付物：** 手工导入/浏览器采样适配器、来源归档、内容去重、三大栏目分类、风险初筛、可解释评分和 Top 3 报告。

**计划文件：** 实施 Phase 1 后创建 `2026-08-04-phase-2-topic-research-ranking.md`。

**验收：** 给定一组跨平台样本，系统输出去重后的候选池、评分明细及每日 Top 3；所有来源可追溯。

### Phase 3：原创脚本、安全审核、TTS 与分镜

**交付物：** IP 语言规范、35–50 秒脚本生成器、安全规则、TTS 适配器、音频检查、强制对齐、A-roll/B-roll 分镜和 Seedance 提示词。

**计划文件：** `2026-08-04-phase-3-script-audio-storyboard.md`。

**验收：** 从批准选题生成可审核脚本、40–46 秒目标音频、时间戳字幕和完整分镜 JSON。

### Phase 4：数字人和 Seedance 2.0 Skill 接入

**交付物：** 用户提供 Skill 的能力核验器、适配器、任务提交/轮询/重试、额度保护、输出归档及测试替身。

**计划文件：** 在两个 Skill 到位并读取其 `SKILL.md` 后创建 `2026-08-04-phase-4-generators-integration.md`。

**验收：** 使用一段短测试音频分别生成数字人母版和 Seedance 场景，记录任务 ID、耗时、规格、费用/额度和错误信息。

### Phase 5：自动合成与质量检查

**交付物：** FFmpeg 时间轴合成、字幕和重点词、音乐闪避、转场、1080×1920 编码、ffprobe 检查、黑帧/静音/冻结帧/字幕安全区/语义人工复核报告。

**计划文件：** `2026-08-04-phase-5-compositing-qc.md`。

**验收：** 将测试数字人母版和 3–5 个 B-roll 合成为 35–50 秒统一成片，自动检查通过后才允许人工批准。

### Phase 6：发布包装、数据复盘与 30 天运营

**交付物：** 三平台标题/简介/封面/标签生成、人工发布清单、数据导入、日报周报、评分权重反馈和 30 天运行手册。

**计划文件：** `2026-08-04-phase-6-packaging-analytics-operations.md`。

**验收：** 同一成片生成三份发布包装；导入三平台数据后输出栏目、钩子、完播、收藏、转发和关注转化分析。

## 依赖顺序

```text
Phase 1 基础编排
  ├── Phase 2 选题研究与排名
  └── Phase 3 脚本、TTS 与分镜
          └── Phase 4 外部生成 Skill 接入
                    └── Phase 5 合成与质检
                              └── Phase 6 发布与复盘
```

Phase 2 与 Phase 3 的局部能力可在 Phase 1 后并行开发，但首次端到端样片必须按 Phase 1 → 3 → 4 → 5 顺序完成。
