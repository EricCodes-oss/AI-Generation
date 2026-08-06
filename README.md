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

1. 选题 + 新闻解读脚本 + 画面规划；
2. 首次创建或变更主持人形象；
3. 最终视频。

已保存且未变更的主持人不重复确认，TTS 参数、普通转场、音量和编码参数不单独确认。

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

## CLI

```bash
# 手动模式：每天一次
avatar-pipeline init-day \
  --date 2026-08-06 \
  --mode manual \
  --topic-source auto_hot

# 托管模式：输入主题后自动推进
avatar-pipeline init-day \
  --date 2026-08-06 \
  --mode managed \
  --topic-source user_topic \
  --input "年轻人如何看待工作和生活的边界"

avatar-pipeline health
avatar-pipeline status --date 2026-08-06
avatar-pipeline import-research --date 2026-08-06 --file research.json
avatar-pipeline record-plan --date 2026-08-06 --file plan.json
avatar-pipeline approve-topic-script --date 2026-08-06 --actor owner
avatar-pipeline set-host --date 2026-08-06 --file host.json
avatar-pipeline approve-host --date 2026-08-06 --actor owner
avatar-pipeline mark-tts --date 2026-08-06 --path audio/main.wav
avatar-pipeline mark-anchor --date 2026-08-06 --path video/anchor.mp4
avatar-pipeline mark-media --date 2026-08-06 --path media/insert.mp4
avatar-pipeline mark-compositing --date 2026-08-06 --path video/master.mp4
avatar-pipeline record-qc --date 2026-08-06 --passed true --report qc/report.json
avatar-pipeline approve-final-video --date 2026-08-06 --actor owner
```

CLI 是非交互式的；手动模式通过显式审批命令推进，不会在小步骤中反复询问。

## Skill Contracts

`skills/contracts/` 记录外部能力的严格输入/输出边界：

- `opinions-crawler`：多平台热点与事实线索采集；
- `news-script-writer`：事实、背景、解读、结论分层的主持人口播稿；
- `news-media-planner`：主持人和竖屏插播时间轴；
- `giggle-generation-speech`：固定主持人 TTS；
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

旧版任务 JSON 读取时会安全迁移到 schema version 2，但不会为旧内容伪造“已核验新闻”状态。
