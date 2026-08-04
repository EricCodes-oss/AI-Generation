# Avatar Pipeline

每天生产一条“数字人人生陪伴 IP”视频的可审计工作流。

## 本地安装

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

## 运行测试

```bash
python -m pytest -q
python -m ruff check src tests
```

当前项目已包含：

- Phase 1：本地每日任务编排和 TTS、数字人、Seedance 外部 Skill 契约；
- Phase 2A：用户门控的热点内容检索、来源标准化、评论洞察与研究报告。

两个阶段都不调用真实 TTS、数字人或 Seedance 生成服务。Phase 2A 也不会自动生成 Top 3 或脚本。

## Phase 1 最小工作流

```bash
avatar-pipeline health
avatar-pipeline init-day --date 2026-08-04
avatar-pipeline import-topics --date 2026-08-04 --file tests/fixtures/top_topics.json
avatar-pipeline approve-topic --date 2026-08-04 --topic-id t1 --actor owner
avatar-pipeline status --date 2026-08-04
```

也可以使用 `--workspace /path/to/workspace` 指定任务数据目录。每天的任务会保存到
`<workspace>/days/YYYY-MM-DD/task.json`。

当前 TTS、数字人和 Seedance 三个真实生成能力均在 Skill 契约中明确设置为
`real_generation_enabled: false`。在用户提供并完成对应 Skill 接口核验前，系统不会消耗真实生成额度。

## 运行手册

- [Phase 1 本地任务编排](docs/operations/phase-1-runbook.md)
- [Phase 2A 热点内容检索](docs/operations/phase-2a-hotspot-research-runbook.md)

Phase 2A 离线入口：

```bash
avatar-pipeline research-health
avatar-pipeline research-init --date 2026-08-04
avatar-pipeline research-plan --date 2026-08-04
```

研究报告生成后必须由用户明确批准，批准前不会进入 Top 推荐。
