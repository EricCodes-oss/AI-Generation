# 抖音、微信视频号、小红书真实热点采集运行手册

## 1. 目标

本手册用于每天从 **抖音、微信视频号、小红书** 读取公开热点证据，形成最多 3 个经过核验的候选热点。手动模式随后只保留 **热点、脚本、最终视频三个确认点**。

默认检索最近 72 小时；合格候选不足 3 个时扩展到最近 7 天。扩展后仍不足 3 个，只输出实际合格数量，禁止虚构补位。

## 2. 浏览器与账号安全边界

- Chrome 登录态只由 Agent 使用；采集器只读取用户当前已登录账号可见的公开页面。
- 禁止保存 Cookie、Token、密码，也禁止导出 Authorization、Session、CSRF 或浏览器登录凭据。
- 全程只读：禁止点赞、评论、收藏、关注、私信、发布、转发或修改账号资料。
- 不绕过登录、验证码、风控、付费墙或平台访问限制。
- 低频、小批量访问；出现挑战页、频控或页面结构异常立即停止当前平台探测。
- 浏览器导出的无凭据研究 JSON 只能写入被 Git 忽略的 `runs/` 或 `workspace/`；不得提交账号数据和原始媒体。

每个平台必须记录一种真实状态：

| 状态 | 含义 | 处理 |
|---|---|---|
| `ready` | 当前登录态和页面结构允许只读采集 | 导出无凭据证据 JSON |
| `login_required` | 需要用户在 Chrome 中登录 | 停止该平台，等待用户登录 |
| `ui_changed` | 页面结构变化，无法可靠读取 | 停止，不猜测字段 |
| `rate_limited` | 遇到频控或挑战页 | 停止并延后重试 |
| `manual_assist_required` | 无稳定自动入口或需用户手工打开内容 | 允许用户辅助提供公开链接或无凭据导出 |

视频号无法稳定自动读取时必须记录 `manual_assist_required`。微信公众号文章只能用于事实核验补充，**公众号不能冒充视频号** 热点证据。

## 3. 证据字段

每条平台证据至少记录：平台、公开链接、内容 ID（可见时）、标题或摘要、作者显示名、发布时间、采集时间、可见互动量、检索关键词、事件键和采集状态。

- 点赞、评论、收藏、分享、播放等不可见指标保持 `null/unknown`，禁止填 0、估算或反推。
- 保存页面中明确可见的数值和单位，并在标准化时保留原始值。
- 同平台先按内容 ID 或规范 URL 去重；跨平台只按明确事件键保守聚类，不把相似观点强行合并为同一事件。

浏览器采集包示例：

```json
{
  "collected_at": "2026-08-07T10:00:00+08:00",
  "platforms": {
    "douyin": {"status": "ready", "records": []},
    "wechat_channels": {"status": "manual_assist_required", "records": []},
    "xiaohongshu": {"status": "ready", "records": []}
  }
}
```

导入器会拒绝包含 cookie、token、password、authorization、session、secret、csrf、access_key 或 refresh_key 的数据。

## 4. 准入、核验和排名

热点满足以下任一条件才可进入正式候选池：

1. 至少在两个目标平台出现；
2. 单平台相对高热度，并有官方或权威来源核验。

以下内容自动跳过并寻找下一个候选：尚未证实、来源冲突、恶意传言、隐私泄露、高风险内容，或只有单一低可信来源的内容。权威来源可以补充事实，但不能伪造成目标平台热度。

综合评分：平台内相对热度 35%、跨平台共振 25%、时效性 15%、评论质量 10%、受众匹配 10%、来源完整度 5%。缺失指标不估算，评分必须展示数据缺口。

## 5. 每日 CLI 流程

```bash
export WORKSPACE=workspace
export DAY=2026-08-07

# 1. Agent 使用 Chrome 只读采集后，导入无凭据 JSON
avatar-pipeline --workspace "$WORKSPACE" research-import-browser \
  --date "$DAY" \
  --file "runs/$DAY/browser-collection.json"

# 2. 导入官方/权威核验文件并进行去重、聚类、过滤和排名
avatar-pipeline --workspace "$WORKSPACE" research-rank-hotspots \
  --date "$DAY" \
  --authority-file "runs/$DAY/authority-evidence.json"

# 3. 生成含渠道、链接、可见互动量、核验和素材方案的 Top 3 报告
avatar-pipeline --workspace "$WORKSPACE" research-hotspot-report --date "$DAY"

# 4. 将最多 3 个合格候选提交到手动热点确认状态
avatar-pipeline --workspace "$WORKSPACE" research-submit-top3 --date "$DAY"
```

报告路径：

```text
workspace/days/YYYY-MM-DD/research/reports/hotspot-top3.md
```

用户在报告中三选一后执行：

```bash
avatar-pipeline --workspace "$WORKSPACE" approve-hotspot \
  --date "$DAY" --topic-id candidate-1 --actor owner
```

此后生成脚本并等待 `approve-script`；脚本确认后才自动生成 TTS、主持人、插播画面和合成；最终只等待 `approve-final-video`。

## 6. 水印和成片素材规则

平台热点视频默认只用于研究、热度证明和脚本参考，不自动进入成片。

- 带水印、平台 Logo、账号昵称、用户 ID、二维码的素材拒绝进入生产。
- 授权不明素材拒绝进入生产。
- 禁止去水印，包括裁剪、遮挡、模糊或 AI 擦除。
- 成片素材优先级：官方授权无水印素材；用户或权利方授权的原创无水印素材；Seedance 2.0 非复刻式 AI 示意画面。
- AI 示意画面不得复刻原视频人物、独特构图、标志性镜头或品牌视觉，并应按项目规则标识为 AI 生成。

最终结构固定为“演播室坐播主持人 + 竖屏新闻画面插播”，默认不加逐字字幕。

## 7. 2026-08-07 Chrome 能力探测结果

本次只读探测未读取或导出任何 Cookie、Token、密码，未执行互动，也未下载平台媒体。

| 平台 | 状态 | 已验证能力 | 限制 |
|---|---|---|---|
| 抖音 | `ready` | 公共热点页可读取话题、热度值、热点视频、可见互动量、作者和日期标签 | 不代表评论、任意视频详情或通用关键词检索均可用 |
| 小红书 | `ready` | 已登录 Explore 页可读取笔记链接、标题、作者和可见互动量 | 推荐流存在账号偏差，部分发布时间不可见 |
| 微信视频号 | `login_required` | 视频号助手入口可访问 | 当前停在登录页，未验证公开热榜或关键词检索；登录并验证前按 `manual_assist_required` 辅助导入处理 |

以上只是 Chrome 页面能力探测，不等于第三方采集 Skill 已端到端启用；`real_calls_enabled` 继续保持 `false`。

## 8. 失败处理

- 单个平台失败不伪造成功，报告明确状态和缺口。
- 72 小时窗口不足 3 个合格热点才扩展至 7 天。
- 7 天后仍不足 3 个时诚实输出 0–2 个。
- 三个平台均无可用证据时停止热点确认，不进入脚本阶段。
- `real_calls_enabled` 只有在部署运行时完成真实能力验证后才能设为 `true`；安装 Skill 或通过静态检查不等于真实采集已启用。
