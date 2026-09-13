# Batch 238 — 镜像拆分与包体缓存优化（Phase 4）— Design Spec
> **Design (🎨)** | Date: 2026-09-13 | Status: Ready

## 0. 技术体系确认

无 UI 视觉变更；本批规范发布镜像和浏览器缓存策略。

## 1. 镜像边界

| 组件 | 目标 | 包含 | 不包含 |
|------|------|------|--------|
| API | `api` | Python、FastAPI、Alembic、lanhu provider | Node、DSH、Chromium、ffmpeg |
| Runner | `runner` | Node、DSH、Playwright/Chromium、ffmpeg | 默认 API 角色 |
| Combined | `runtime` | 兼容旧发布与回滚 | 新 split 路径不依赖 |

## 2. 缓存策略

- Backend builder：pip cache mount。
- Backend runner：npm cache mount。
- Frontend builder：npm cache mount。
- Browser 和模型缓存保持持久卷/镜像外挂，不进入源码 layer。
- `index.html`：`no-cache, no-store, must-revalidate`。
- `/assets/*`：`public, immutable` + 30d。

## 3. 前端 chunk

- `vendor-charts`: recharts
- `vendor-graph`: vis-network + vis-data
- `vendor-mindmap`: markmap-lib + markmap-view

目的：重型页面沿用路由懒加载，同时避免依赖升级导致公共 chunk 全量失效。
