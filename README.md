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

Phase 1 只建设本地任务编排与外部 Skill 契约，不调用真实 TTS、数字人或 Seedance 生成服务。

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
