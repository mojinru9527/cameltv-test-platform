# Batch 239 — 独立 AI Gateway 服务边界（Phase 5A）— Design Spec
> **Design (🎨)** | Date: 2026-09-14 | Status: Ready

## 内部 API

```text
GET  /internal/ai/v1/health
POST /internal/ai/v1/chat
POST /internal/ai/v1/embed
```

鉴权：`X-AI-Gateway-Token`。未配置 token 或 token 不匹配时返回 401/503。

## 服务拓扑

```text
API  --HTTP--> AI Gateway --HTTP--> Cloud / Local LLM Runtime
                   |
                   +--> FastEmbed / Cache / Shadow
```

API 角色默认 `embedded`，配置 `AI_GATEWAY_URL` 后切换为 `remote`。
AI Gateway 角色固定 `gateway`，禁止再次远程委派。

## 镜像边界

- `ai-gateway` target：Python + AI/RAG 依赖，不含 Node/Chromium/DSH。
- 默认 combined 镜像保持不变。
- `docker-compose.execution.yml` 才启用独立服务。
