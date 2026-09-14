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

已采纳。Batch 240 将 API、AI Gateway、Runner 的 Python 依赖拆成独立 hash lock 与 Docker base；Batch 241 修复锁的平台解析缺陷并把 split 拓扑切为默认。

## 决策

1. API 使用 `requirements.api.lock`，不包含 FastEmbed、ONNX Runtime、NumPy、Playwright。
2. AI Gateway 使用 `requirements.ai.lock`，包含 Embedding 依赖但不包含 Playwright。
3. Runner 使用 `requirements.runner.lock`，包含 AI/RAG、Playwright 和浏览器运行时。
4. 三套 lock 均由现有 `requirements.lock` 作为 version constraint 生成，避免版本漂移。
5. Dockerfile 新增 `builder-api`、`builder-ai`、`runtime-api-base`、`runtime-ai-base`。
6. 三套 lock 必须对**目标平台（linux/amd64）**可解析：由 Windows 解析生成的锁会丢失
   `secretstorage` / `jeepney`（`sys_platform == "linux"`）与 `uvloop`（`sys_platform != "win32"`），
   导致 `pip install --require-hashes` 在镜像构建阶段直接失败（Batch 241 修复）。
7. ~~默认 combined `runtime` 保留；生产 split 切换仍等待真实容器 smoke。~~
   → **已被 Batch 241 取代**：本地真实 Docker host 跑通 API→AI Gateway→runner 全链路后，
   默认拓扑切换为 split；combined `runtime` 改为回滚 overlay（`docker-compose.combined.yml`）。
8. AI Gateway 在 `AI_GATEWAY_TOKEN` 缺失时必须让 `/internal/ai/v1/health` 返回 503，
   使容器级 `--wait` 门禁与 compose `${VAR:?}` 语义一致（Batch 241）。
