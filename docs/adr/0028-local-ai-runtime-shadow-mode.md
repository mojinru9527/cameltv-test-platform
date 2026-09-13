---
title: "ADR-0028: 独立本地 AI Runtime 与 Shadow Mode"
owner: "tech-lead"
last_reviewed: "2026-09-13"
status: "active"
expires: "2027-09-13"
tags: ["adr", "ai", "local-runtime", "shadow", "safe-rollout"]
related: ["0027-ai-local-first-gateway.md"]
---

# ADR-0028: 独立本地 AI Runtime 与 Shadow Mode

## 状态

已采纳。Batch 236 实现独立运行时配置、后台 Shadow 对比和失败隔离；local-first 路由属于 Batch 237。

## 决策

1. 本地模型通过外部 OpenAI-compatible runtime 提供，不由 API 进程加载模型。
2. 平台只保存 endpoint、模型名与可选 Key；模型权重、CUDA、Ollama/llama.cpp/vLLM 进程不进入 API 镜像。
3. Shadow Mode 默认关闭，支持 0–1 采样率；主响应不等待本地结果。
4. Shadow 使用独立 DB Session 和后台线程；失败只记录 `failed`，不改变主结果。
5. 只保存输入/输出 hash、JSON 合法性、延迟与 usage，不保存完整 Prompt 或完整输出。
6. 本地与云端共用 `ai_client` 的 OpenAI-compatible transport。

## 后果

- 可以在切换主链前积累真实模型质量和延迟证据。
- 本地 runtime 仍是部署依赖，但与应用发布解耦。
- Shadow 会增加本地推理成本；默认关闭和采样率控制是必要护栏。
- 本地 endpoint 不可达时系统保持主链可用。

## 弃选方案

| 方案 | 否决理由 |
|------|----------|
| API 进程内加载模型 | 镜像膨胀、启动慢、GPU/CUDA 运维复杂 |
| 直接切 local-first | 未验证质量前违反安全回滚原则 |
| 只记录手工评测 | 无法覆盖真实 Prompt、成本和延迟分布 |

## 关联

- 实现：`test-platform-v2/backend/app/services/ai_gateway/runtime.py`
- Shadow：`test-platform-v2/backend/app/services/ai_gateway/shadow.py`
- API：`test-platform-v2/backend/app/api/v1/ai_config.py`
