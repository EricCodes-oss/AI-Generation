# 热点新闻数字人主持人双模式视频系统设计

- 文档版本：V2.1
- 日期：2026-08-06
- 状态：核心方案与主持人形象规格已确认，待制定实施计划

## 1. 产品定位

打造一个固定主持人数字人新闻解读栏目，每天围绕经过可靠来源确认的热点新闻生产一条竖屏短视频，统一发布到抖音、微信视频号和小红书。

栏目不是新闻机构，不冒充记者、律师、医生、金融顾问或其他专业权威。主持人负责把热点事实讲清楚、解释争议和影响；视频插播负责提供可靠新闻素材或明确标识的 AI 示意画面。

核心表达：

> 热点新闻是内容主体，主持人负责解释和串联，画面负责提供事实感与理解辅助。

## 2. V1 固定视频形态

V1 统一采用：

- 固定演播室坐播主持人；
- 9:16 竖屏，1080×1920 输出；
- 主持人与竖屏新闻画面交替；
- 主持人开场、解释、总结；
- 原始新闻视频优先，AI 示意画面作为补充；
- 固定栏目包装，热点标题和信息条随选题变化；
- 默认不添加逐字口播字幕；
- 不加入站播、户外主持、访谈主持、多主持人或多演播室切换。

建议单条时长为 45–75 秒，按事实复杂度和实际 TTS 时长动态确定，不强制套用固定秒数。

### 2.1 参考结构

```text
主持人坐播：热点钩子与事件概述
→ 新闻画面：原始片段或 AI 示意画面
→ 主持人坐播：争议点、背景和影响解释
→ 新闻画面：关键细节或辅助说明
→ 主持人坐播：理性总结
```

主持人不是全程占满画面，而是作为稳定的叙事入口和栏目识别。新闻画面不是装饰，应服务于事实证明或理解辅助。

## 3. 内容范围与安全底线

### 3.1 默认内容方向

- 社会现象；
- 职场生活；
- 教育话题；
- 消费生活；
- 科技生活；
- 家庭关系；
- 年轻人情绪与生活方式。

### 3.2 默认排除

- 娱乐八卦和未经证实的个人爆料；
- 敏感政治内容；
- 高风险医疗、法律和金融判断或建议；
- 恶意攻击、隐私曝光、人格定性；
- 未成年人隐私；
- 血腥暴力、灾难细节和可能引发现实伤害的内容；
- 依靠聊天截图、匿名消息、单一账号或可疑剪辑才能成立的内容。

### 3.3 热点准入规则

热度只决定是否值得核查，不能决定是否可以发布。

只有核心事实经过可靠来源确认的内容，才可进入正式候选池。对于“有热度但尚未完全证实”的内容，Agent 必须自动跳过并继续寻找下一个合格热点，不进入脚本、数字人生成或视频合成。

内部状态：

```text
verified       核心事实已确认，可进入正式候选池
pending        有热度但待核实，不进入正式候选池
unverified     无法确认，不进入正式候选池
high_risk      高风险，直接排除
malicious      疑似恶意内容，直接排除
```

如果当天没有达到可信度和安全标准的热点，不为满足日更而强行制作。

## 4. 两种运行模式

### 4.1 托管模式（managed）

用户输入想法、主题、关键词或“自动寻找热点”，可选提供数字人形象。Agent 自动完成从热点采集到最终视频质检的完整流程，中间不要求用户确认，只返回最终结果和必要说明。

```text
用户输入
→ 热点采集
→ 去重、聚类和多源核查
→ 风险筛选
→ 自动选择合格选题
→ 新闻解读脚本
→ 复用或设计固定坐播主持人
→ TTS
→ 坐播主持人数字人视频
→ 原始新闻片段截取或 AI 示意画面生成
→ 栏目化合成
→ 自动质检
→ 输出最终视频与发布包装
```

托管模式不取消内部质量闸门。出现事实不足、风险过高、版权或素材不可用、口型/音画/画面质量不合格时，Agent 应自动换题、重试或停止，不把问题交给用户兜底。

最终输出包括：成片、标题、简介、标签、来源说明、AI 画面说明和必要风险提示。

### 4.2 手动模式（manual）

用户输入想法、主题或自动找热点，可选提供数字人形象。过程只保留关键确认点，不确认每个小步骤。

默认确认策略：

1. **确认一：选题 + 脚本 + 画面规划**
   - 热点候选、来源、时间和推荐理由；
   - 事实摘要和解读角度；
   - 完整主持人口播稿；
   - 主持人/B-roll 时间结构；
   - 原始素材或 AI 示意画面计划。
2. **确认二：主持人形象（仅在需要时）**
   - 首次创建主持人；
   - 用户提供新参考图；
   - 修改人物、演播室或栏目视觉风格。
   - 已确认的固定坐播主持人后续自动复用，不重复确认。
3. **确认三：最终视频**
   - 用户审核内容准确性、主持人口播、插播画面、节奏和栏目包装。

不单独确认：TTS 参数、每个 B-roll 候选、普通转场、编码参数、音量、文件命名和过程日志。

## 5. 固定主持人形象规格

### 5.1 角色定位

> 成熟专业的女性热点新闻主持人，兼具调查记者的冷静判断力和陪伴型表达的亲和感。

数字人不是内容主体，只负责稳定播报、解释和串联内容。V1 只制作并复用一套固定的演播室坐播形象，以降低生产复杂度，把资源集中到热点质量、事实核验、脚本表达和插播画面上。

### 5.2 固定人物设定

外貌：

- 成年东亚女性，30–36 岁视觉年龄；
- 黑色中长直发，自然落在肩部；
- 五官清晰、知性自然，不使用明显明星脸；
- 自然清晰的眉形，有神但克制的眼睛；
- 精致但不过度浓艳的职业妆容；
- 自然红棕或豆沙色口红；
- 平和、专注、可信的表情。

服装：

- 深蓝色西装外套；
- 米白色内搭；
- 简洁的虚构栏目胸针；
- 不使用真实媒体 Logo、警徽、肩章或政府标志；
- 不使用明显性感化、暴露或夸张装饰。

姿态与构图：

- 坐在现代新闻演播室桌后；
- 腰部以上中景；
- 正面或轻微三分之一角度；
- 双肩自然放松；
- 双手位于桌面下方或自然放在桌面；
- 面部和嘴部无遮挡；
- 目光朝向镜头；
- 适合数字人口型同步；
- 画面比例 9:16，人物居中。

场景：

- 现代虚构新闻演播室；
- 深海军蓝、炭灰色和少量冷白色；
- 抽象世界地图、柔和 LED 屏和简洁新闻桌；
- 不出现可读新闻标题、真实媒体台标或现实机构标志；
- 背景保持安静，不能抢过人物和插播画面。

### 5.3 参考图片使用边界

用户提供的参考图片：

```text
/Users/liuweidong/Downloads/1785598397341-z5ilw311-1785598399474-1.jpg
```

只作为以下视觉参考：黑色长发、东亚女性面部气质、自信镇定的镜头感、写实摄影风格、灰蓝色调和专业灯光。

不复制以下元素：警察制服、警徽和肩章、警察局/审讯室、铁栅栏、WANTED/MISSING PERSON 海报、挑逗表情、性感化摆拍、短裙和高跟鞋造型。

### 5.4 GPT Image 2 正式主图提示词

```text
Create a realistic professional seated female news presenter for a fictional digital news channel.

She is an adult East Asian woman with a visual age of approximately 30 to 36 years old. She has long straight black hair falling naturally over her shoulders, refined but natural facial features, clear expressive eyes, naturally defined eyebrows, subtle professional makeup, and muted rose-red lipstick.

Her expression is calm, intelligent, trustworthy, and composed, with a gentle restrained smile. She looks directly toward the camera like an experienced television journalist explaining important information to the audience. She should appear professional and approachable, not seductive, glamorous, or like a fashion model.

She is seated behind a modern news desk in a fictional broadcast studio. She wears a tailored deep navy-blue blazer over an ivory blouse, with a small simple fictional newsroom pin on the lapel. The outfit is modest, elegant, and suitable for a daily news program.

Composition: vertical 9:16 portrait, medium shot from the waist up, centered presenter, relaxed shoulders, stable seated posture, unobstructed face and mouth area, hands resting naturally below the frame or lightly on the desk, suitable for talking-head digital avatar lip synchronization.

Background: a clean modern fictional news studio with dark navy and charcoal gray tones, subtle abstract world map graphics, soft LED panels, and a minimal news desk. The background should remain visually quiet and should not compete with the presenter.

No police uniform, no police badge, no military uniform, no government emblem, no real media logo, no real public figure resemblance, no revealing clothing, no exaggerated jewelry, no seductive pose, no readable text, no distorted hands, no extra people.

Soft professional broadcast lighting, realistic skin texture, natural proportions, sharp facial details, high-quality realistic photographic style, credible television news atmosphere.
```

### 5.5 资产策略

- 只生成一张固定坐播主图作为 V1 主持人资产；
- 首次在手动模式中需要用户确认，托管模式内部自动生成并检查；
- 用户提供主持人图片时，优先使用用户资产，并执行清晰度、构图、版权和内容安全检查；
- 后续每日生产直接复用已确认主图，不重复设计人物；
- 如需更换人物或演播室，视为一次新的主持人资产变更，需要重新确认。

## 6. 内容生产流程与 Skill 分工

1. **热点采集**：`opinions-crawler`、`wechat-article-search`
2. **清洗、去重和聚类**：`material-organizer`
3. **事实与风险筛选**：`hotspot-fact-safety-reviewer`
4. **选题推荐**：`viral-topic-forge`、`wechat-viral-topic`
5. **新闻解读脚本**：`kidd-script-writing` 作为结构参考，配合 `news-anchor-script-writer`
6. **分镜与媒体计划**：`scene-planner` + `news-media-planner`
7. **TTS**：`giggle-generation-speech`
8. **主持人视频**：`giggle-generation-tv-avatar-video`
9. **原始视频素材**：`news-footage-clipper`
10. **AI 示意画面**：`giggle-seedance2-gen`
11. **视频合成**：`news-anchor-video-compositor`
12. **质量检查**：`news-video-quality-control`
13. **发布包装**：抖音、微信视频号和小红书共用同一母版，分别生成平台文案。

## 7. 配置与状态

```yaml
mode: managed | manual
topic_source: user_topic | auto_hot
avatar_source: user_provided | saved_host | agent_designed
avatar_layout: seated_studio_anchor
subtitle: false
video_structure: studio_anchor_plus_vertical_news_insert
media_policy: reliable_original_first_ai_demo_fallback
platforms:
  - douyin
  - wechat_channels
  - xiaohongshu
approval_policy:
  managed:
    topic_script: auto
    avatar: auto
    final_video: final_only
  manual:
    topic_script: user_confirm
    avatar: confirm_if_new_or_changed
    final_video: user_confirm
```

建议状态：

```text
input_received
→ researching
→ fact_screened
→ topic_script_review (manual only)
→ host_review (only if new/changed)
→ media_planning
→ generating_tts
→ generating_anchor
→ acquiring_or_generating_media
→ compositing
→ quality_check
→ final_review (manual only)
→ ready_to_publish
```

任何未达到 `verified` 的热点不得进入 `topic_script_review` 之后的状态。托管模式在内部完成等价检查，但不向用户发起确认。

## 8. 验收标准

- 两种模式行为清晰且不可混淆；
- 托管模式不在中间要求人工确认，手动模式只有约定的关键确认点；
- 未经证实或恶意内容无法进入正式制作；
- V1 输出固定坐播演播室主持人与竖屏新闻画面插播结构；
- 主持人仅保留一套固定坐播形象，不实现站播、户外、访谈和专题多形象；
- 原始新闻视频优先，AI 画面明确为示意而非事实证据；
- 默认不添加逐字字幕；
- 用户提供主持人时可复用，未提供时 Agent 可设计并在手动模式首次确认；
- 三个平台使用同一母版视频；
- 生成前、生成后和发布前均保留来源、素材、脚本和审核记录；
- 质量不达标时托管模式自动重试/换题/停止，手动模式在关键问题处暂停。
