# Batch 239 — 独立 AI Gateway 服务边界（Phase 5A）— PM Plan
> **PM (🟨)** | Date: 2026-09-14

## 开发任务
### [ ] Task 1: 配置与服务角色
- `AI_GATEWAY_URL`、`AI_GATEWAY_TOKEN`、`AI_GATEWAY_ROLE`
- API 默认 embedded；Gateway 进程 role=gateway

### [ ] Task 2: 内部 HTTP 服务
- `POST /internal/ai/v1/chat`
- `POST /internal/ai/v1/embed`
- `GET /internal/ai/v1/health`
- Token fail-closed

### [ ] Task 3: AI Client 远程委派
- sync/async chat 远程分支
- Gateway 角色禁止递归
- 错误保持现有 AI 异常分类

### [ ] Task 4: Embedding 远程委派
- `EmbeddingService.embed` 远程分支
- 返回 NumPy 数组，维持现有接口

### [ ] Task 5: Docker/Compose
- Dockerfile `ai-gateway` target
- execution overlay 增加 ai-gateway service 与健康检查
- 不修改默认 combined 服务

### [ ] Task 6: 测试与证据
- 服务端 auth/chat/embed/health 测试
- API remote delegation 测试
- image contract 扩展
