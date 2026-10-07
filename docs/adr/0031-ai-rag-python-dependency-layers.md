---
title: "ADR-0031: AI/RAG Python 依赖分层"
owner: "tech-lead"
last_reviewed: "2026-10-07"
status: "superseded"
expires: "2027-09-14"
tags: ["adr", "docker", "dependencies", "fastembed", "onnx", "image-size"]
related: ["0030-image-split-build-cache.md"]
---

# ADR-0031: AI/RAG Python 依赖分层

## 状态

**已被平台简化批次（2026-10-07）取代。** 原决策为「API / AI Gateway / Runner 三层依赖 + 三套 lock」；
简化批次删除了 ai-gateway 独立服务（AI 改平台直连），因此：

1. `requirements.api.lock` **现在包含** FastEmbed / ONNX Runtime / NumPy（本地嵌入随 API 进程交付，
   否则知识库 RAG 向量检索会静默降级为仅关键词）；同时移除了已删除的 Temporal 运行时。
2. `requirements.ai.lock` 与 `builder-ai` / `runtime-ai-base` 阶段**已删除**。
3. `requirements.runner.lock` 由 `-r requirements.api.txt` + Playwright + rapidocr 生成
   （与 `requirements.lock` 版本集合一致）。
4. 三套 lock 收敛为**两套**；平台正确性守卫（Linux dry-run 解析 + `docker build --target api`）
   仍由 required 后端 job 执行，只是锁定对象变为 `requirements.api.lock` 与 `requirements.runner.lock`。
5. 原第 7/8 条关于 split 拓扑与 AI Gateway 健康门禁的决策随服务删除而失效。

以下原文保留为历史记录。

## 状态（历史）

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
9. 三个 Docker target 各自消费自己的 lock，阶段名与角色一一对应（Batch 242）：

   | 阶段 | lock | target |
   |------|------|--------|
   | `builder-api` | `requirements.api.lock` | `api` |
   | `builder-ai` | `requirements.ai.lock` | `ai-gateway` |
   | `builder-runner` | `requirements.runner.lock` | `runner` / `runtime` |

   `requirements.lock` 保留为**约束源**（生成三套锁）与文档基线，不再被任何 Docker
   target 安装；`Dockerfile.local`（本地全量开发镜像）与每日 `pr-check.yml` 继续使用它。
   `requirements.runner.lock` 与 `requirements.lock` 当前版本集合一致（119 pins，
   0 版本差异），因此上述收口在依赖层面零漂移。
10. 三套 lock 的**平台正确性**由 required 后端 job 守卫（Batch 242）：
    对每个 lock 执行 Linux `pip install --dry-run --require-hashes --ignore-installed`
    （不得加 `--no-deps`，否则会跳过正是出问题的依赖解析），
    并额外执行 `docker build --target api` 冒烟。
