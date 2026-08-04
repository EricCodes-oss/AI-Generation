# Phase 2A 热点内容检索运行手册

## 1. 阶段目标与边界

Phase 2A 只实现每日内容生产的第一个环节：**热点内容检索与用户审核**。

```text
加载热点检索 Skill
→ 生成每日查询计划
→ 导入并标准化跨平台来源
→ 导入 A 级来源评论洞察
→ 生成可审阅研究报告
→ 等待用户明确决定
```

用户只有明确执行 `research-approve` 后，该研究修订才会被冻结为批准版本。本阶段不会：

- 生成或排序 Top 3；
- 生成脚本、TTS、数字人或 Seedance 画面；
- 修改 Phase 1 每日任务的 `created` 状态；
- 自动登录抖音、小红书、视频号或其他平台；
- 启用无人值守采集或真实生成。

永久排除主题：`父母养老与照护压力`、`养老`、`照护老人`。

## 2. 前置环境

要求：

- Python 3.11 或更高；
- 项目开发依赖已安装；
- fixture/manual import 流程无需平台登录；
- 第三方采集 Skill 的源码安装状态与真实调用能力必须分开判断。

安装项目：

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

检查研究能力：

```bash
avatar-pipeline research-health
python scripts/verify_research_skills.py --project-root .
```

截至 2026 年 8 月 4 日，本地状态为：

- `opinions-crawler`：固定提交源码已安装并校验；OpenCLI 缺失；浏览器扩展和平台登录仍需人工确认；真实调用关闭。
- `wechat-article-search`：固定提交源码已安装并校验；JavaScript 静态语法检查通过；`cheerio` 尚未在隔离环境安装；真实调用关闭。
- 视频号不能由微信公众号文章搜索替代；当前应使用人工授权导入或用户后续提供的专用能力。

源码位于 `.local/third-party-skills/`，该目录不进入 Git；仓库只保存固定提交、源码树摘要和审计记录。不得运行第三方 `setup.sh`，也不得擅自进行全局 npm/Python 安装。

## 3. 工作区结构

研究数据保存在：

```text
<workspace>/days/YYYY-MM-DD/research/
├── run.json
├── raw/
├── reports/
│   └── daily-research-revision-N.md
└── revisions/
    └── revision-N.json
```

- `run.json`：当前可继续修改的状态；
- `reports/`：每次供用户审阅的 Markdown 报告；
- `revisions/`：批准后生成的不可覆盖 JSON 快照；
- `raw/`：真实接入后保存原始采集产物；fixture/manual import 仍会记录原始文件路径和 SHA-256。

## 4. 完整离线演练

下面的流程使用确定性 fixture，只证明编排、标准化、报告和审批门控可工作，**不证明任何真实平台已可采集**。

```bash
export WORKSPACE=/tmp/avatar-research-smoke
export DAY=2026-08-04

avatar-pipeline --workspace "$WORKSPACE" research-init --date "$DAY"
avatar-pipeline --workspace "$WORKSPACE" research-plan --date "$DAY"
avatar-pipeline --workspace "$WORKSPACE" research-import \
  --date "$DAY" \
  --collector fixture \
  --file tests/fixtures/research/manual_sources.json
avatar-pipeline --workspace "$WORKSPACE" research-import-insights \
  --date "$DAY" \
  --file tests/fixtures/research/comment_insights.json
avatar-pipeline --workspace "$WORKSPACE" research-report --date "$DAY"
avatar-pipeline --workspace "$WORKSPACE" research-status --date "$DAY"
```

fixture 包含 30 条来源、5 条 A 级来源、5 张评论洞察卡、三个内容支柱、三个时间窗口和一个明确的数据缺口。报告生成后状态仍是 `ready_for_review`，必须停下来给用户审阅。

## 5. 查询计划规则

`research-plan` 加载项目的热点查询规划逻辑：

- 每天生成 9 个核心查询组；
- 三个内容支柱各 3 组；
- 时间目标为最近 72 小时 50%、7 天 35%、30 天 15%；
- 7 天内避免完全相同关键词；
- 3 天内避免相同生活场景；
- 最近 30 天已生产主题降权；
- 连续两次无结果的查询冷却 14 天；
- 最多允许 3 个动态扩展查询组；
- 不纳入养老与照护老人相关内容。

可附加用户方向：

```bash
avatar-pipeline research-plan \
  --date 2026-08-04 \
  --directive "重点关注中年职场转型和亲子沟通"
```

## 6. 来源导入格式

`research-import` 支持 `fixture` 和 `manual_import`。输入可以是 JSON 数组，也可以是含 `items` 数组和可选 `failures` 数组的对象。

每条 item 的结构：

```json
{
  "platform": "xiaohongshu",
  "query_group_id": "core-07-growth-emotional-boundary",
  "payload": {
    "title": "来源标题",
    "excerpt": "只保留结构化摘要，不复制长文案",
    "url": "https://example.com/item",
    "content_id": "platform-id",
    "grade": "A",
    "published_at": "2026-08-04T08:00:00+08:00",
    "likes": 1200,
    "comments": 80
  }
}
```

关键约束：

- 来源必须关联当天已知查询组；
- 标题不能为空；
- URL 和平台内容 ID 至少有一个；
- 未知互动字段保持 `null`，不能编造；
- 原始互动量不跨平台直接比较；
- 采集失败应作为 `failures` 保留，不能用虚构来源补齐数量；
- 不复制热门视频完整台词、文章正文或大段评论。

视频号无法自动获取时，可把人工审核后导出的结构化数据以 `manual_import` 导入：

```bash
avatar-pipeline research-import \
  --date 2026-08-04 \
  --collector manual_import \
  --file /path/to/authorized-channels-export.json
```

## 7. 评论洞察导入

评论洞察文件可以是卡片数组，也可以是含 `cards` 数组的对象。每日目标：

- 5–8 个 A 级来源；
- 每个来源 20–40 条有效评论；
- 覆盖高赞、亲历、求助、不同意见、最新五类样本；
- 保存匿名化评论引用编号，不保存不必要的可识别信息；
- 提炼场景、情绪、内在冲突、显性问题、隐性需要、失败尝试和反感表达；
- 不诊断心理疾病，不推断未知身份；
- 自伤、家暴或违法信号必须标记给人工安全复核。

导入：

```bash
avatar-pipeline research-import-insights \
  --date 2026-08-04 \
  --file /path/to/comment-insights.json
```

## 8. 用户决策与修订

### 批准

```bash
avatar-pipeline research-approve \
  --date 2026-08-04 \
  --actor owner
```

批准前必须已经生成报告。若未达到 30–40 条来源或 5–8 张有效洞察卡，必须显式记录接受的缺口：

```bash
avatar-pipeline research-approve \
  --date 2026-08-04 \
  --actor owner \
  --accept-gap "视频号只完成 4 条人工授权来源" \
  --accept-gap "今天仅完成 4 张评论洞察卡"
```

批准会写入 `revisions/revision-N.json`。该文件不能被后续修改覆盖。

### 补充平台

```bash
avatar-pipeline research-revise \
  --date 2026-08-04 \
  --action supplement_platform \
  --feedback "补充视频号来源"
```

### 补充话题

```bash
avatar-pipeline research-revise \
  --date 2026-08-04 \
  --action supplement_topic \
  --feedback "补充职场被否定的具体场景"
```

### 重采评论

```bash
avatar-pipeline research-revise \
  --date 2026-08-04 \
  --action recollect_comments \
  --feedback "重新检查 A 级来源的不同意见样本"
```

### 其他动作

- `hold`：暂存为 `held`；
- `return`：退回并保持已有材料；
- `revise`：一般性修改；
- `redo`：本环节全部重做，清空计划、来源、洞察和失败记录。

从已批准版本发起修订时，新工作版本的 revision 自动加一，并用 `parent_revision` 指向旧批准版本。

## 9. 故障恢复

- 平台采集失败：保留失败记录，继续处理其他平台；需要用户决定补采、人工导入或接受缺口。
- JSON 格式错误：CLI 返回退出码 2 和明确错误，不修改已有 run。
- 来源无法追溯：拒绝该条，不补造 URL、内容 ID 或互动数据。
- 报告需要修改：执行对应 `research-revise`，补充后重新导入洞察并再次 `research-report`。
- 已批准快照冲突：不要删除旧 revision；检查是否错误重复批准或 revision 未递增。
- 第三方平台出现登录失效、验证码、反爬或页面结构变化：立即停止，不绕过限制；记录失败并转人工流程。

## 10. 隐私、版权与平台合规

- 只提取主题、情绪、生活场景、需求、表达结构和互动证据；
- 不保存或输出完整爆款脚本、大段文章、批量原评论；
- 评论必须匿名化，避免用户名、手机号、住址、学校、公司等可识别信息；
- 不绕过登录、验证码、访问控制、反爬或平台限制；
- 不把搜索排名等同于热度，不把不同平台的原始互动量直接横向排名；
- 实际使用第三方源码和依赖前继续核验许可证、站点条款和商业使用条件。

## 11. 与下一环节的边界

批准研究报告仅表示“热点资料可以进入下一环节”。当前 Phase 2A 不会创建 `TopicCandidate`，也不会调用选题推荐或脚本 Skill。

后续建设应单独实现：

```text
已批准研究报告
→ 加载选题推荐 Skill
→ 返回 Top 推荐供用户审核
→ 用户明确批准
→ 才加载脚本 Skill
```

在下一阶段代码完成并经用户确认前，不得用 `import-topics` 假装研究环节已经自动产出 Top 3。
