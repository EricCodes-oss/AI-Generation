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
