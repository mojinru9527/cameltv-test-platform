# Batch 238 — 镜像拆分与包体缓存优化（Phase 4）
> **Product (🟦)** | Date: 2026-09-13 | Status: Approved

## 1. 问题陈述

API、AI/UI 重运行时此前已具备 `api` / `runner` Docker target，但缺少 Phase 4 的基线采集、BuildKit 缓存契约和前端重型 chunk 缓存治理。直接宣称“已优化”没有可复用测量口径，也无法防止后续把 Node/DSH/Chromium 重新塞回 API 镜像。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| API/runner 分离契约 | 文件存在 | 自动验证 target 不混用 | 本批测试 |
| 镜像基线 | 历史手工记录 | 可重复采集脚本 + 历史真实测量引用 | 本批证据 |
| BuildKit cache mount | 0/未约束 | backend pip/npm、frontend npm | 契约测试 |
| 前端重型 chunk | 单 chunk 风险 | charts/graph/mindmap 独立 vendor chunk | build 输出 |
| SPA shell 缓存 | 未显式 | `index.html` no-store；assets immutable | nginx 契约 |

## 3. 非目标

- 不把默认 Compose 从 combined 切换为 split；仍走 opt-in overlay。
- 不引入模型权重或 CUDA 到 API 镜像。
- 不重做已存在的基础 API/runner target。
- 本轮 Docker daemon 不可用时，不伪造实时镜像大小。

## 4. 验收标准

- `docker-compose.execution.yml` 验证 backend→api、runner/aitde-worker→runner。
- API target 段不含 nodejs/playwright install；runner target 含重运行时。
- Backend/Frontend Dockerfile 含 BuildKit cache mount。
- `vite.config.ts` 拆分 charts/graph/mindmap；Nginx 对 index.html 不缓存、对 assets 长缓存。
- `collect-image-baseline.ps1` 可输出 JSON，并在 Docker 不可用时明确记录。

## 5. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| Phase 4 | 发布/运维 | 契约测试通过；split overlay 可独立使用 |
| 后续发布 | 发布火车 | 在 Docker host 上复采 API/runner 实际大小 |
