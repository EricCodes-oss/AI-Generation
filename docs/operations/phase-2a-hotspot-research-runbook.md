# Phase 2A 热点检索、核验与 Top 3 运行手册

## 阶段目标

Phase 2A 从 **抖音、微信视频号、小红书** 获取公开热点证据，进行去重、跨平台聚类、权威核验、风险过滤和热度排名，然后把最多 3 个合格热点提交给用户确认。

```text
加载检索 Skill
→ 最近 72 小时只读采集
→ 不足时扩展到最近 7 天
→ 去重与保守聚类
→ 权威核验与风险过滤
→ Top 3 报告
→ 等待热点确认
```

永久排除主题：`父母养老与照护压力`、`养老`、`照护老人`。

## 与生产流程的边界

手动模式只有 **热点、脚本、最终视频三个确认点**：

1. Phase 2A 展示渠道、原始链接、可见互动量、热度分析和核验结果，让用户最多三选一；
2. 用户确认完整脚本；
3. 用户确认最终视频。

主持人、TTS、普通分镜、转场和单个插播片段不增加审批点。没有用户热点确认时，不得生成正式脚本；没有脚本确认时，不得消耗 TTS、数字人或 Seedance 额度。

## 真实采集安全规则

- Chrome 登录态只由 Agent 使用。
- 禁止保存 Cookie、Token、密码。
- 只读访问，禁止点赞、评论、收藏、关注、私信、发布或修改账号。
- 不绕过验证码、登录、风控或付费墙。
- 平台状态必须如实记录为 `ready`、`login_required`、`ui_changed`、`rate_limited` 或 `manual_assist_required`。
- 不可见互动指标保持 `null/unknown`，禁止估算。
- 微信公众号文章可用于事实核验，但公众号不能冒充视频号。

详细浏览器操作、数据格式和失败降级见：

```text
docs/operations/real-three-platform-collection-runbook.md
```

## 准入规则

候选热点必须满足：

- 至少两个目标平台出现；或
- 单平台相对高热，并有官方或权威来源核验。

尚未完全证实、来源冲突、恶意传言、隐私泄露和高风险内容直接跳过。默认最近 72 小时，合格候选不足 3 个才扩展至最近 7 天；仍不足时只输出实际数量。

评分权重：平台内相对热度 35%、跨平台共振 25%、时效性 15%、评论质量 10%、受众匹配 10%、来源完整度 5%。

## 真实数据命令

```bash
export WORKSPACE=workspace
export DAY=2026-08-07

avatar-pipeline --workspace "$WORKSPACE" research-import-browser \
  --date "$DAY" --file "runs/$DAY/browser-collection.json"

avatar-pipeline --workspace "$WORKSPACE" research-rank-hotspots \
  --date "$DAY" --authority-file "runs/$DAY/authority-evidence.json"

avatar-pipeline --workspace "$WORKSPACE" research-hotspot-report --date "$DAY"
avatar-pipeline --workspace "$WORKSPACE" research-submit-top3 --date "$DAY"
```

`research-submit-top3` 只把任务停在热点确认状态，不会自动选择候选。用户通过 `approve-hotspot` 选择后才进入脚本阶段。

## 水印与授权门禁

平台视频只作为研究证据，除非它是官方授权或权利方授权的无水印素材。带水印、Logo、账号标识、二维码或授权不明素材一律拒绝。禁止去水印，也禁止用裁剪、遮挡、模糊或 AI 擦除绕过门禁。

无法获得合规原始画面时，使用 **Seedance 2.0 非复刻式 AI 示意画面**，不得复刻原视频人物、独特构图或标志性镜头。

## 离线测试与能力声明

fixture/manual import 可以验证标准化、报告和审批门控，但不证明真实平台已可采集。第三方 Skill 的“已安装”“静态检查通过”“真实调用可用”必须分开记录；未完成真实能力探测前，`real_calls_enabled` 保持 `false`。

检查本地依赖：

```bash
avatar-pipeline research-health
python scripts/verify_research_skills.py --project-root .
```

真实运行产物、账号状态和原始媒体只保存在被 Git 忽略的 `runs/` 或 `workspace/`。
