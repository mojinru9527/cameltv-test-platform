# Batch 239 — 独立 AI Gateway 服务边界（Phase 5A）
> **Product (🟦)** | Date: 2026-09-14 | Status: Approved

## 1. 问题陈述

AI Gateway、路由、缓存、Shadow 和本地 embedding 当前仍运行在后端 API 进程。API 的普通读写请求与 AI 重能力共享进程、GIL、内存和故障域，无法独立扩缩、回滚或做依赖瘦身。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 独立 AI Gateway 进程 | 无 | `app.ai_gateway_app:app` 可独立启动 | 本批测试 |
| 内部 HTTP 契约 | 无 | chat/embed/health 三接口 | 契约测试 |
| API 远程委派 | 无 | `AI_GATEWAY_URL` 配置后 API 不再本地执行 AI | 单元测试 |
| 安全门禁 | 无 | 内部 Token + fail-closed | 单元测试 |
| 默认行为 | combined | 默认关闭远程委派，split overlay opt-in | 回归 |

## 3. 非目标

- 本批不切默认 Compose 拓扑。
- 本批不拆 `requirements.lock`；FastEmbed/ONNX 依赖分层留后续批次。
- 不把本地 LLM 权重放入 `ai-gateway` 镜像。
- 不改变前端 API。

## 4. 验收标准

- `ai-gateway` Docker target 不含 Node/Chromium/DSH。
- 内部 chat/embed 请求必须有 Token；Token 未配置时 fail-closed。
- API 配置 `AI_GATEWAY_URL` 后 chat/embed 经 HTTP 转发。
- Gateway 角色自身不递归转发。
- combined 部署和现有测试保持通过。
