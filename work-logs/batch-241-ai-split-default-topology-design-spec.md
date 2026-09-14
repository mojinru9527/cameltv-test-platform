# Batch 241 — Design 技术规范
> **Design (🎨)** | Date: 2026-09-14 | Status: Approved

## 1. 拓扑目标态

```
                         ┌──────────────────────┐
   :80  frontend ──────▶ │  backend (api)       │  构建 target: api
                         │  uvicorn app.main    │  WORKER_EXECUTION_ENABLED=false
                         └───┬──────────┬───────┘
                             │          │
              AI_GATEWAY_URL │          │ RUNNER_HTTP_URL
                             ▼          ▼
                  ┌────────────────┐  ┌──────────────────┐
                  │ ai-gateway     │  │ runner           │
                  │ app.ai_gateway │  │ app.main         │
                  │ :8100 internal │  │ WORKER_EXECUTION │
                  │ target:ai-     │  │ _ENABLED=true    │
                  │ gateway        │  │ target: runner   │
                  └────────────────┘  └──────────────────┘
```

- 三者共享同一 OCI base（`python:3.12-slim@sha256:57cd7c3a…`），镜像层部分复用。
- `backend` 不再携带 FastEmbed/ONNX/NumPy/Playwright（api lock）。
- `ai-gateway` 携带 AI/RAG 依赖，不携带浏览器。
- `runner` 携带完整运行时（AI + Playwright + Chromium + Node）。

## 2. 默认切换策略（C239-2）

| 层 | 变更 |
|----|------|
| `docker-compose.yml` | `backend.build.target: api`；新增 `ai-gateway` 服务；`volume-permissions.build.target: api`；`backend.depends_on` 增加 ai-gateway health |
| `docker-compose.combined.yml`（新） | 回滚 overlay：`backend`/`aitde-worker`/`volume-permissions` 回到 `runtime` target；`ai-gateway` 通过 `profiles: ["split-only"]` 排除 |

**关键约束**：`docker-compose.yml` 单独使用时必须是可用拓扑；combined 回滚必须
`-f docker-compose.yml -f docker-compose.combined.yml` 两条一起给。

## 3. Fail-closed 契约（C239-3）

| 场景 | 期望行为 |
|------|---------|
| 缺 `AI_GATEWAY_TOKEN` | `docker compose config` 报错退出（`${VAR:?}` 语义） |
| 缺 `AI_GATEWAY_IMAGE`（split 发布路径） | 同上 |
| `AI_GATEWAY_ROLE=remote` 但 URL 不可达 | 启动期 healthcheck 失败 → `--wait` 返回非零，不进入 running |
| combined 回滚缺 ai-gateway | 不依赖 ai-gateway，`backend` 本地执行 AI |

现有 `docker-compose.execution.yml` 已用 `${AI_GATEWAY_TOKEN:?AI_GATEWAY_TOKEN is required}`
实现前两条；本批把该语义固化进契约测试，并补齐发布 profile 侧的注入与制品校验。

## 4. 发布 profile 制品通道（C239-3）

统一「part」抽象：`parts = ('backend', 'frontend', 'runner')` 在 split 下扩展为
`('backend', 'frontend', 'runner', 'ai-gateway')`。

| part | 仓库名 | tar | 目标 service |
|------|--------|-----|--------------|
| backend | `cameltv-tp-backend` | `{tag}-backend.tar` | backend |
| frontend | `cameltv-tp-frontend` | `{tag}-frontend.tar` | frontend |
| runner | `cameltv-tp-runner` | `{tag}-runner.tar` | runner / aitde-worker |
| ai-gateway（新） | `cameltv-tp-ai-gateway` | `{tag}-ai-gateway.tar` | ai-gateway |

- `release_artifacts.verify()` 对 split 校验四件 tar 的单一镜像导出与 config digest。
- `runtime_mode()` 对 split 增加 `ai_gateway` 制品结构校验。
- `TencentSshExecutor._compose(mode='split')` 注入
  `AI_GATEWAY_IMAGE=<config.image_ai_gateway>`。
- `rollback_runtime_override('split')` 的 owner 列表扩展到
  `('backend', 'runner', 'ai-gateway')`，ai-gateway 用 `app.ai_gateway_app:app` 启动。

## 5. 证据契约

`scripts/ops/smoke_ai_split_topology.py` 输出单行 JSON：

```json
{"result":"passed","images":[{"name":"...","size_bytes":N}],
 "chain":{"api_health":true,"gateway_health":true,"api_to_gateway_embed":true,
          "runner_reachable":true},
 "fail_closed":{"missing_token":true,"missing_image":true},
 "shared_base":"sha256:57cd7c3a..."}
```

失败时打印脱敏后的容器日志并返回非零，禁止「跳过即通过」。

## 6. 兼容性

- 业务 API 契约不变；前端无改动。
- `runtime`（combined）target 保留，供回滚与单机部署。
- 迁移：无数据库迁移；回滚 = 叠加 combined overlay 后 `compose up -d`。
