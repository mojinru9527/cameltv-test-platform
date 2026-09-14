# Batch 241 — AI split 默认拓扑与容器级验收
> **Product (🟦)** | Date: 2026-09-14 | Status: Approved

## 0. 批次模式

`mode: full`（完整批次）——本批引入新的默认部署拓扑（新配置/新行为）与发布 profile
的 ai-gateway 制品通道，命中「新配置/新行为」判定。

## 1. 问题陈述

Batch 235–240 已把 AI 控制面、本地运行时、路由兜底与 Python 依赖逐层拆开，但
`origin/main` 上仍有四个未闭合点：

1. **C239-2**：默认 Compose 仍是 combined `runtime`，split 需显式叠加
   `docker-compose.execution.yml`；未在真实 Docker host 跑通 API→AI Gateway→runtime
   全链路 smoke。
2. **C239-3**：发布 profile（release-console）只装载/标记 `backend`、`frontend`、
   `runner` 三个制品，**没有 ai-gateway 制品通道**；`_compose` 的 split 分支只注入
   `API_IMAGE`/`RUNNER_IMAGE`，未注入 `AI_GATEWAY_IMAGE`；`rollback_runtime_override`
   只覆盖 `backend`/`runner`，split 回滚时 ai-gateway 无命令兜底。
3. **C240-1**：合并后从未采集 api / ai-gateway / runner 三镜像的**实测体积与共享层**，
   「API 镜像体积下降」仍无数据支撑。
4. 默认拓扑未切换，瘦身收益在生产路径上未兑现。

## 2. 成功指标

| 指标 | 基线 | 目标 |
|------|------|------|
| 默认 Compose 拓扑 | combined `runtime` | split（api + ai-gateway + runner） |
| 真实 Docker 全链路 smoke | 未执行 | API→AI Gateway→runner 通过 |
| api 镜像体积 | 未测量 | 实测并记录，明显小于 runner/combined |
| 三镜像共享层 | 未测量 | 实测 base 层共享，产出 JSON 证据 |
| 发布 profile split 制品 | backend/frontend/runner | 增加 ai-gateway |
| split 回滚命令兜底 | 仅 backend/runner | 覆盖 backend/runner/ai-gateway |
| 缺 `AI_GATEWAY_TOKEN/IMAGE` | 未验证 | fail-closed（compose 拒绝启动） |

## 3. 非目标

- 不改业务 API 契约、前端页面、数据库 Schema、Alembic 迁移。
- 不引入新运行时依赖（不新增 pip/npm 包）。
- 不改 Temporal/aitde-worker 的既有启动脚本语义。
- 不执行真实腾讯云生产发布（仅本地真实 Docker host 验收 + 发布 profile 单元契约）。
- 不删除 combined `runtime` target（保留为回滚路径）。

## 4. 验收标准

1. `docker-compose.yml` 默认即为 split：`backend` 构建 `api` target，存在
   `ai-gateway` 服务，`backend` 通过 `AI_GATEWAY_URL/TOKEN/ROLE=remote` 走远程网关。
2. 提供 combined 回滚 overlay，可将默认拓扑切回单一 `runtime`。
3. 本地真实 Docker host 跑通：api `/health`、ai-gateway `/internal/ai/v1/health`、
   API→ai-gateway 的 embed/chat 代理、runner 可达。
4. 缺失 `AI_GATEWAY_TOKEN` 或 `AI_GATEWAY_IMAGE` 时 `docker compose config` 或
   `up` 必须 fail-closed，不得静默回落。
5. release-console 的 split 制品集包含 `ai-gateway`，tar/digest 校验通过。
6. 采集三镜像 `size_bytes` 与共享层证据，写入 work-logs。
7. 全部既有部署/镜像契约测试保持绿色（无新增失败）。

## 5. 用户价值

- 生产默认路径即拿到 API 镜像瘦身收益：API 不再携带 FastEmbed/ONNX/NumPy/Playwright。
- split 拓扑可回滚到 combined，降低默认切换的爆炸半径。
- 发布 profile 具备完整三镜像制品与 fail-closed 校验，避免「配置漏注入导致半启动」。
