# 本地 AI Agent 接入（平台零推理）

> Batch 248 起，CamelTv 平台默认**不执行任何 LLM 推理**（`AI_PLATFORM_INFERENCE=false`）。
> AI 能力由使用者在本地运行：平台只创建 `AiJob`、接收并展示结果。

## 1. 架构

```text
需求页「AI 拆分 / AI 生成用例」
        │  （平台不调用模型）
        ▼
   AiJob(pending)  ──►  AI 任务页（可见/可导入）
        │
        │  claim（X-AI-Agent-Token）
        ▼
  本地 AI Agent（scripts/ai_agent/cli.py，ChatGPT 桌面客户端会话内执行）
        │  本地/客户端模型推理（模型可自由切换）
        │  report（结果 JSON + model_name）
        ▼
   AiJob(completed) + AiResult ──► 平台展示 ──► 一键导入用例库
```

## 2. 快速开始

见 `scripts/ai_agent/README.md`。最小闭环：

```bash
python scripts/ai_agent/cli.py register --agent-id my-agent --project-id 14
python scripts/ai_agent/cli.py doctor
python scripts/ai_agent/cli.py next --out job.json
python scripts/ai_agent/cli.py report --job <id> --file result.json --model <模型名>
python scripts/ai_agent/cli.py import --job <id>
```

## 3. 平台侧约定

| 能力 | 端点 | 权限 |
|---|---|---|
| 注册 Agent（签发 token） | `POST /api/v1/ai/agents/register` | `apitest:execute` |
| 吊销 token | `POST /api/v1/ai/agents/tokens/revoke` | `apitest:execute` |
| 创建 Job | `POST /api/v1/ai/jobs` | `apitest:execute` |
| Job 列表 / 详情 | `GET /api/v1/ai/jobs`、`GET /api/v1/ai/jobs/{id}` | `apitest:execute` |
| 认领 / 心跳 / 上报 | `POST /api/v1/ai/jobs/claim`、`/jobs/{id}/heartbeat`、`/jobs/{id}/report` | agent token（或登录用户） |
| 导入结果 | `POST /api/v1/ai/jobs/{id}/import` | `requirement:import` |
| Agent 在线状态 | `GET /api/v1/ai/agents/health` | `apitest:execute` |

## 4. 运维开关

| 变量 | 默认 | 说明 |
|---|---|---|
| `AI_PLATFORM_INFERENCE` | `false` | `false`=平台只派发（推荐）；`true`=回退旧的平台内推理链（仅运维/评估） |
| `AI_JOB_STALE_SECONDS` | `300` | 心跳丢失超过该值，running 任务自动回收到 pending |
