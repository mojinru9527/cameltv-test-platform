# camel-ai-agent —— 本地 AI Agent CLI

平台不做 LLM 推理。本 CLI 在你本机（例如 ChatGPT 桌面客户端的会话里）认领平台的
`AiJob`，由**你选择的本地/客户端模型**产出结果，再回传平台。

## 一次性配置

```bash
# 1) 注册 agent（token 仅返回一次，自动写入 ~/.cameltv-ai-agent.json）
python scripts/ai_agent/cli.py register --agent-id my-local-agent --project-id <项目ID>

# 2) 自检
python scripts/ai_agent/cli.py doctor
```

## 一次完整任务

```bash
python scripts/ai_agent/cli.py next --out job.json     # 认领 → 打印任务输入
#   把 job.json 的输入交给本地模型（可随时切换模型），把产物写成 result.json
python scripts/ai_agent/cli.py report --job 12 --file result.json --model chatgpt-5
python scripts/ai_agent/cli.py import --job 12         # generate 结果导入用例库
```

## result.json 约定

`generate` 任务（功能/接口用例）：

```json
{
  "document_id": 20,
  "functional_cases": [{"title": "...", "priority": "P0", "steps": "...", "expected_result": "..."}],
  "api_cases": []
}
```

`extract` 任务（功能拆分）：把模块列表放在 `modules` 字段；当前批次的自动导入仅支持
`generate`，`extract` 结果请在需求页人工确认。

## 常见问题

- 认领不到任务：确认任务 `capability`（extract/generate）在你的 `--capabilities` 范围内；
  平台只会把本项目的任务派给本项目 scope 的 agent。
- 401：token 被吊销或已删除，重新 `register`。
- 任务卡在 running：心跳丢失超过 `AI_JOB_STALE_SECONDS`（默认 300s）后会被自动回收为 pending。
