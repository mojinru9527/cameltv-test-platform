---
title: "ADR-0031: AI/RAG Python 依赖分层"
owner: "tech-lead"
last_reviewed: "2026-09-14"
status: "active"
expires: "2027-09-14"
tags: ["adr", "docker", "dependencies", "fastembed", "onnx", "image-size"]
related: ["0030-image-split-build-cache.md"]
---

# ADR-0031: AI/RAG Python 依赖分层

## 状态

已采纳。Batch 240 将 API、AI Gateway、Runner 的 Python 依赖拆成独立 hash lock 与 Docker base。

## 决策

1. API 使用 `requirements.api.lock`，不包含 FastEmbed、ONNX Runtime、NumPy、Playwright。
2. AI Gateway 使用 `requirements.ai.lock`，包含 Embedding 依赖但不包含 Playwright。
3. Runner 使用 `requirements.runner.lock`，包含 AI/RAG、Playwright 和浏览器运行时。
4. 三套 lock 均由现有 `requirements.lock` 作为 version constraint 生成，避免版本漂移。
5. Dockerfile 新增 `builder-api`、`builder-ai`、`runtime-api-base`、`runtime-ai-base`。
6. 默认 combined `runtime` 保留；生产 split 切换仍等待真实容器 smoke。
