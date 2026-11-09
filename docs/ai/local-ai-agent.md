---
title: "本地 AI Agent 接入（已退役）"
owner: "qa-team"
last_reviewed: "2026-11-09"
status: "superseded"
expires: "2027-11-09"
tags: ["ai", "local-agent", "superseded", "execution-node"]
related: ["../adr/0027-ai-local-first-gateway.md", "../adr/0028-local-ai-runtime-shadow-mode.md", "../aiqe/baseline.md"]
---

# 本地 AI Agent 接入（已退役）

> **status: superseded（batch-277 P0-5，2026-11-09）**：`scripts/ai_agent/`、`/ai/jobs/*` 端点、
> ai-gateway / Shadow / 本地优先路由已全部删除。"平台零推理 + 本地 Agent 认领 AiJob" 的旧模式不再存在。

## 1. 现行架构（三句话）

| 能力 | 现在的做法 | 代码 |
|------|-----------|------|
| 文本类 AI（需求拆分 / 用例生成 / 分诊建议） | 控制面**直连项目级 provider**（OpenAI 协议，DeepSeek / Qwen / Claude 均可） | `app/services/ai_client.py` + `app/services/ai_config_service.py` |
| AI 配额 / 熔断 / 成本台账 | `ai_guard` + `model_usage_ledger`；每次调用必记账 | `app/services/ai_guard.py`、`app/models/model_usage.py` |
| 浏览器 / 接口**执行** | `cameltv-node` 本地执行节点认领 `ExecutionJob`（与 LLM 无关） | `scripts/node/cameltv_node/`、`app/services/execution_job_service.py` |

**没有**本地 LLM 推理、**没有** ai-gateway、**没有** Shadow 副本、**没有**本地优先路由兜底。

## 2. 旧文档迁移说明

- `scripts/ai_agent/cli.py` / `README.md`：**已删除**（它调用的 `/ai/jobs/claim|report|import` 端点早已不存在）；
- `ai_agents` 表：仍保留，但语义是**执行节点注册表**；模型文件由 `app/models/ai_job.py` 更名为
  `app/models/execution_node.py`，类名 `ExecutionNode`（表名不变，避免生产数据迁移风险）；
- 相关 ADR：ADR-0027 / 0028 / 0029 均已标 `superseded`；
- `ai_response_cache` / `ai_shadow_run` 两张表：由 migration
  `20261109_b277_drop_retired_tables` 删除（可 downgrade 重建）。

## 3. 节点接入（现行）

执行节点接入见 `scripts/node/README.md`：

```bash
cameltv-node login --username <平台账号> --project-id <项目ID>
cameltv-node up --node-id my-pc --capabilities api web
```

节点只做「执行 + 证据上传」，不做 LLM 推理；`X-AI-Agent-Token` 仍是节点鉴权头（历史命名，保留兼容）。

