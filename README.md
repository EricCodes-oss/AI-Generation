# Hotspot News Anchor Pipeline

每天生产一条“固定演播室主持人 + 真实竖屏新闻画面插播”的热点新闻解读视频。

## 产品边界

项目包含两套边界不同的流程：

### Legacy V1 工作流

- 支持 `managed` 托管模式和 `manual` 手动模式；
- 使用旧版每日任务状态机和显式审批命令；
- 原始新闻视频优先，缺少素材时可使用带必要说明的 AI 示意画面；
- 旧版栏目母版可以包含标题、信息条、来源标识或 AI 示意标识。

### V5 手动新闻无字净版

V5 是当前固定质量基线，仅覆盖：

- 45—90 秒；
- 数字人主持人主讲；
- 9:16、1080×1920、25fps；
- H.264 视频、AAC 48kHz 单声道；
- 无字幕、标题、来源条、Logo、音乐和素材原声的无字净版；
- 固定短发主持人 `host-c2-pro-candidate-2-final`；
- 主持人参考图 SHA-256：`939324593eb718cd2a39be4c171f74178a6a48442f7e0d61afe8a875011e8a47`；
- 固定音色 `未来科技解说`，音色 ID：`cobra_design_20250717_162347_664524`；
- 真实现场素材必须保留来源 URL、下载时间和文件哈希旁路记录；
- 无水印准入不等同于已经获得版权授权；
- 自动 QC 通过后仍须完成两遍导演审核。

完整操作流程见 [`docs/runbooks/manual-news-v5-production.md`](docs/runbooks/manual-news-v5-production.md)。

## 两种 Legacy 模式

### 托管模式

用户输入主题、关键词或自动找热点，可选提供主持人形象。Agent 自动采集、核验、去重、写稿、生成 TTS、生成主持人视频、准备插播画面、合成、质检并输出最终视频和发布包装。内部质量闸门仍然生效，遇到不安全或不合格内容会自动跳过、重试或停止。

### 手动模式

Legacy 手动流程在选题脚本、主持人和最终视频节点显式确认。已保存且未变更的主持人不重复确认，普通转场、音量和编码参数不单独确认。

V5 流程为非交互式 SOP：准备阶段记录后直接运行质量门，不会在每个小步骤反复询问；只有需求冲突或硬质量门失败才停止。

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

## V5 手动新闻制作

```bash
# 1. 初始化不可覆盖的新版本目录
avatar-pipeline news-v5-init \
  --output-root output \
  --date 2026-08-12 \
  --slug 台风强降雨 \
  --topic "台风影响减弱但北方强降雨风险仍在持续" \
  --version 1

RUN_DIR="output/manual-news-2026-08-12-台风强降雨-v01"

# 2. 根据实际音频时长获取插播节奏建议
avatar-pipeline news-v5-guidance --duration 52.128

# 3. 依次通过生产质量门
avatar-pipeline news-v5-preflight \
  --run-dir "$RUN_DIR" --stage generation --project-root "$PWD"
avatar-pipeline news-v5-preflight --run-dir "$RUN_DIR" --stage timeline
avatar-pipeline news-v5-preflight --run-dir "$RUN_DIR" --stage render

# 4. 渲染后进入自动QC和导演审核
avatar-pipeline news-v5-mark-rendered --run-dir "$RUN_DIR"
avatar-pipeline news-v5-build-qc --run-dir "$RUN_DIR"
avatar-pipeline news-v5-apply-director-review --run-dir "$RUN_DIR"
avatar-pipeline news-v5-status --run-dir "$RUN_DIR"
```

日期、主题、来源事实、素材 URL 和剪辑区间必须来自当次运行。详细 JSON 格式、FFmpeg 规则、QC 证据和返工方式以 Runbook 为准。

## Legacy CLI

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

CLI 是非交互式的；Legacy 手动模式通过显式审批命令推进。

## Skill Contracts

`skills/contracts/` 记录外部能力的严格输入/输出边界：

- `opinions-crawler`：多平台热点与事实线索采集；
- `news-script-writer`：权威来源约束、短句和完整结尾的主持人口播稿；
- `news-media-planner`：主持人、语义映射和插播时间线；
- `tts`：固定“未来科技解说”音色；
- `giggle-gpt-image-2`：主持人和演播室参考图；
- `giggle-generation-tv-avatar-video`：图片 + 音频驱动主持人视频；
- `news-footage-clipper`：连续正向新闻素材截取与来源旁路记录；
- `giggle-seedance2-gen`：Legacy AI 示意画面能力；
- `news-compositor`：V5 无字净版母版合成；
- `news-quality-control`：技术、身份、时间线、结尾和导演审核。

当前契约保持 `contract_version: "1.0"` 和 `real_generation_enabled: false`，只做本地编排和接口校验，不会未经配置调用真实生成额度。

## 测试与检查

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
git diff --check
```

旧版任务 JSON 读取时会安全迁移到 schema version 2，但不会为旧内容伪造“已核验新闻”状态。
