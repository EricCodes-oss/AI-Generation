# Hotspot News Anchor Pipeline

每天生产一条“固定演播室主持人 + 竖屏新闻画面插播”的热点新闻解读视频。

## 产品边界

- 支持 `managed` 托管模式和 `manual` 手动模式。
- 只允许经过可靠来源核验、低风险的热点进入正式制作。
- V1 固定 9:16、1080×1920 演播室主持人结构，主持人和竖屏新闻画面交替。
- 原始新闻视频优先；没有合适素材时使用明确标识的 Seedance AI 示意画面。
- 默认不添加逐字口播字幕，只保留栏目标题、信息条、来源标识和必要的 AI 示意标识。
- 同一母版视频用于抖音、微信视频号和小红书。

## 两种模式

### 托管模式

用户输入主题、关键词或自动找热点，可选提供主持人形象。Agent 自动采集、核验、去重、写稿、生成 TTS、生成主持人视频、准备插播画面、合成、质检并输出最终视频和发布包装。内部质量闸门仍然生效，遇到不安全或不合格内容会自动跳过、重试或停止。

### 手动模式

只在三个关键节点确认：

1. 展示热点抓取渠道、原始内容、互动数据和热度分析，由用户从 3 个合格热点中选择 1 个；
2. 展示所选热点的完整新闻解读脚本，由用户确认后才开始 TTS、数字人、插播画面和合成；
3. 展示最终视频，由用户确认发布或提出修改。

主持人图片可由用户提供，也可使用已保存的固定主持人，但不单独增加确认节点。TTS 参数、普通分镜、转场、音量和编码参数均不单独确认。

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

## CLI

CLI 为非交互式接口。`init-day` 支持两种内容入口，并默认复用固定坐播主持人“林知遥”（母图：`assets/hosts/fixed-seated-anchor/master-reference.png`）。如果存在最近已确认的主持人资产则优先复用；也可以通过 `--host-image` 提供新形象。只有用户明确要求改版时，才重新生成默认主持人。

```bash
# 手动模式：自动找热点；只在三个关键节点确认
python -m avatar_pipeline.cli --workspace workspace init-day \
  --date 2026-08-06 \
  --mode manual \
  --topic-source auto_hot

# 托管模式：先显式配置真实运行时，再由 init-day 一次执行到最终状态
export AVATAR_PIPELINE_MANAGED_RUNTIME="your_runtime_module:create_runtime"
python -m avatar_pipeline.cli --workspace workspace init-day \
  --date 2026-08-06 \
  --mode managed \
  --topic-source user_topic \
  --input "年轻人如何看待工作和生活的边界"

# 可选：提供新的固定坐播主持人图片
python -m avatar_pipeline.cli --workspace workspace init-day \
  --date 2026-08-07 \
  --mode manual \
  --topic-source auto_hot \
  --host-image assets/host.png

python -m avatar_pipeline.cli --workspace workspace health
python -m avatar_pipeline.cli --workspace workspace status --date 2026-08-06
```

### 手动模式的三个确认命令

```bash
# 1. 从已展示的 Top 3 热点中选择一个
avatar-pipeline approve-hotspot \
  --date 2026-08-06 \
  --topic-id candidate-1 \
  --actor owner

# 2. 确认完整口播脚本；确认后才允许进入媒体生成
avatar-pipeline approve-script --date 2026-08-06 --actor owner

# 3. 确认最终母版视频
avatar-pipeline approve-final-video --date 2026-08-06 --actor owner
```

TTS、主持人、普通分镜、转场、音量、编码和单个插播片段不设置用户确认点。`set-host`、`mark-tts`、`mark-anchor`、`mark-media`、`mark-compositing` 和 `record-qc` 是执行器记录生产状态的接口，不是人工审批命令。

### 托管运行时接口

`managed` 模式不会使用模拟 Provider，也不会在未配置时伪装生成成功。运营环境必须设置 `AVATAR_PIPELINE_MANAGED_RUNTIME=<python_module>:<factory>`。该工厂接收已初始化的 `DailyTask`，返回 `avatar_pipeline.managed_runtime.ManagedRunInput`，其中包含：

- 已采集、去重和核验的候选热点；
- `ManagedProviders` 的脚本、主持人、TTS、数字人、插播媒体、合成和 QC 实现；其中 TTS Provider 签名为 `tts(news_script, voice_id)`；
- 可选的最大候选尝试次数。

`init-day --mode managed` 会调用该运行时并直接推进到 `ready_to_publish` 或安全的 `stopped` 最终状态。单个候选的脚本或生产 Provider 失败时，会清理该候选产生的部分制品、记录失败审计，并在次数上限内尝试下一个已核验候选。未设置运行时环境变量时，命令在创建每日任务前明确报错。当前仓库的 Skill Contracts 仍默认 `real_generation_enabled: false`；启用真实运行时应由部署方显式完成，不会自动消耗生成额度。

`health` 会报告 `managed/manual`、`user_topic/auto_hot`、固定 `seated_studio_anchor` 布局、默认关闭逐字字幕、已配置 Skill 和外部工具状态。

### 发布包装

只有状态为 `ready_to_publish`、具备至少两个不同来源 ID 和两个不同底层来源引用的完整核验记录，并且所有 AI 示意画面都有明确披露时，才能建立发布包装。相同链接即使使用不同 `source_id` 也不能通过。抖音、微信视频号和小红书只生成不同的平台文案，三个平台始终引用同一个 `master_video_path`，不会重复生成三条不同视频。

## Skill Contracts

`skills/contracts/` 记录外部能力的严格输入/输出边界：

- `opinions-crawler`：多平台热点与事实线索采集；
- `news-script-writer`：事实、背景、解读、结论分层的主持人口播稿；
- `news-media-planner`：主持人和竖屏插播时间轴；
- `giggle-generation-speech`：固定主持人 TTS，默认音色 `宣传女生Pro:clone_20260806_114837_980375`，默认情绪 `neutral`、语速 `1.0`；
- `giggle-gpt-image-2`：固定主持人和演播室参考图；
- `giggle-generation-tv-avatar-video`：图片 + 音频驱动主持人视频；
- `news-footage-clipper`：原始新闻素材截取与来源记录；
- `giggle-seedance2-gen`：AI 示意画面；
- `news-compositor`：栏目母版合成；
- `news-quality-control`：事实、版权、标识、音画和画面质量检查。

当前契约默认 `real_generation_enabled: false`，只做本地编排和接口校验，不会未经配置调用真实生成额度。

## 测试与检查

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
git diff --check
```

旧版任务 JSON 读取时会安全迁移到 schema version 3，但不会为旧内容伪造“已核验新闻”状态。

### 端到端验收

`tests/test_end_to_end_news_workflow.py` 使用本地 fake providers 验证完整双模式生产链路，不调用真实生成额度。验收覆盖：仅允许已核验热点进入制作、固定坐播主持人与竖屏插播交替、原始新闻素材优先与 Seedance 披露式回退、默认无逐字字幕、托管模式无人工审批、手动模式严格执行热点、脚本、成片三个确认点、断点恢复不重复生成，以及三平台共用同一通过质检的母版。

## 真实三平台热点采集

Phase 2A 从抖音、微信视频号、小红书读取公开热点证据。Chrome 登录态只由 Agent 使用，采集过程只读；禁止保存 Cookie、Token、密码，也禁止点赞、评论、收藏、关注、私信或发布。默认检索最近 72 小时，不足 3 个合格候选时扩展到最近 7 天；不可见指标保持 `null/unknown`。微信公众号可作核验补充，但公众号不能冒充视频号。

```bash
avatar-pipeline --workspace workspace research-import-browser \
  --date 2026-08-07 --file runs/2026-08-07/browser-collection.json
avatar-pipeline --workspace workspace research-rank-hotspots \
  --date 2026-08-07 --authority-file runs/2026-08-07/authority-evidence.json
avatar-pipeline --workspace workspace research-hotspot-report --date 2026-08-07
avatar-pipeline --workspace workspace research-submit-top3 --date 2026-08-07
```

带水印、Logo、账号标识、二维码或授权不明素材不得进入成片，禁止去水印。没有合规授权画面时，回退为 Seedance 2.0 非复刻式 AI 示意画面。完整规则见 `docs/operations/real-three-platform-collection-runbook.md`。

2026-08-07 的最小只读探测结果：抖音公共热点页为 `ready`；小红书已登录 Explore 页为 `ready`；微信视频号仍为 `login_required`，在登录并验证安全读取入口前按 `manual_assist_required` 处理。该探测不代表第三方采集运行时已经启用，`real_calls_enabled` 仍为 `false`。
