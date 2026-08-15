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
- 素材可保留用户明确接受的来源水印、平台角标或账号标识，但必须如实记录；
- 来源水印可用不等同于已经获得版权授权；
- 自动 QC 通过后仍须完成两遍导演审核。

完整操作流程见 [`docs/runbooks/manual-news-v5-production.md`](docs/runbooks/manual-news-v5-production.md)。

## 两种 Legacy 模式

### 托管模式

用户输入主题、关键词或自动找热点，可选提供主持人形象。Agent 自动采集、核验、去重、写稿、生成 TTS、生成主持人视频、准备插播画面、合成、质检并输出最终视频和发布包装。内部质量闸门仍然生效，遇到不安全或不合格内容会自动跳过、重试或停止。

### 手动模式

Legacy 手动流程在选题脚本、主持人和最终视频节点显式确认。已保存且未变更的主持人不重复确认，普通转场、音量和编码参数不单独确认。

V5 只有热点选题门需要用户确认：系统先用双漏斗从 20—40 个原始话题中筛选注意力与内容价值，只展示真正合格的 3—8 个候选，也允许少于 3 个；没有 S 级选题时明确报告，不用弱题凑数。用户与导演确认后，事实核验、稿件、TTS、数字人、素材、剪辑和 QC 均按非交互式 SOP 连续执行；只有事实冲突、权利风险或硬质量门失败才停止。 普通过程汇报只用于同步进度，不构成暂停点；执行者不得在阶段结束后等待用户再次发送“继续”，而应自动进入下一安全步骤，直至成片和全部交付物通过验收。硬质量门失败时，优先自动诊断、返工和复验，只有无法自行消除的真实阻塞才请求用户介入。

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

## V5 手动新闻制作

```bash
# 1. 对内部评审后的 v2 选题证据打分，生成动态候选池和导演报告
avatar-pipeline --workspace workspace editorial-build-report \
  --date 2026-08-13 \
  --file tmp/editorial-opportunities/2026-08-13/opportunities.json

avatar-pipeline --workspace workspace hotspot-pool-status --date 2026-08-13

# 2. 用户与导演共同评估后，只确认一次选题
avatar-pipeline --workspace workspace hotspot-select \
  --date 2026-08-13 \
  --candidate-id candidate-2 \
  --actor owner \
  --reason "共同评估后确认"

# 3. 用批准记录初始化不可覆盖的新版本目录
avatar-pipeline news-v5-init \
  --output-root output \
  --date 2026-08-13 \
  --slug 已确认选题 \
  --topic "候选池中已确认的完整标题" \
  --version 1 \
  --topic-selection workspace/hotspot-selections/2026-08-13/topic-selection.json

RUN_DIR="output/manual-news-2026-08-13-已确认选题-v01"

# 4. 获取宽松的插播参考范围；最终段数、时长、占比由导演动态决定
avatar-pipeline news-v5-guidance --duration 52.128

# 5. 依次通过生产质量门
avatar-pipeline news-v5-preflight \
  --run-dir "$RUN_DIR" --stage generation --project-root "$PWD"
avatar-pipeline news-v5-preflight --run-dir "$RUN_DIR" --stage timeline
avatar-pipeline news-v5-preflight --run-dir "$RUN_DIR" --stage render

# 6. 渲染后进入自动QC和导演审核
avatar-pipeline news-v5-mark-rendered --run-dir "$RUN_DIR"
avatar-pipeline news-v5-build-qc --run-dir "$RUN_DIR"
avatar-pipeline news-v5-apply-director-review --run-dir "$RUN_DIR"
avatar-pipeline news-v5-status --run-dir "$RUN_DIR"
```

热点发现覆盖国内榜单、权威媒体、搜索需求、社交讨论、视频传播和垂直社区六类信号，不得只由百度或任何单一平台主导。候选可覆盖社会民生、科技、财经、国际、政策、消费、教育、网红热点、普通人热议、文娱文化和天气灾害。平台热度只证明关注变化，事实必须回到第一方、官方或独立可靠来源；素材还须核验画面相关性、清晰度、年代、口罩或疫情时期错配、水印/文字、哈希以及版权或使用依据。

插播采用 `director_dynamic`：不固定三段，也不按视频时长机械分配次数。题材、稿件结构、素材质量、动作完整性和最终观看效果共同决定插播数量、单段时长及占比；优先少而长、语义连贯的叙事块，避免频繁短切。1—5 段、4.5—12 秒、20%—45% 仅为宽松参考范围，不是达标配额。

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
PYTHONPATH="$(pwd):$(pwd)/src" .venv/bin/python -m pytest -q
git ls-files '*.py' -z | xargs -0 .venv/bin/ruff check
git diff --check
```

旧版任务 JSON 读取时会安全迁移到 schema version 2，但不会为旧内容伪造“已核验新闻”状态。
