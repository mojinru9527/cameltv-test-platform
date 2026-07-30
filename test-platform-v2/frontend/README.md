---
title: "CamelTv 测试平台前端"
owner: "frontend-team"
last_reviewed: "2026-06-26"
status: "active"
expires: "2026-12-26"
tags: ["frontend", "react", "ant-design", "vite", "typescript"]
related: ["test-platform-v2/backend/README.md", "test-platform-v2/frontend/CLAUDE.md"]
---

# cameltv-test-frontend

CamelTv 测试平台前端（React 19 + React Router 8 + shadcn/ui + Vite + TypeScript）。

## 技术栈

- React 19 · React Router 8 · shadcn/ui · Vite · TypeScript
- 状态：Zustand（鉴权态/当前项目，持久化到 localStorage）
- 路由：React Router 6（登录守卫 + 动态菜单）
- 请求：axios（JWT 拦截器 + 统一 envelope 拆包）

## 目录结构

```
src/
├── main.tsx           # 入口（ConfigProvider + RouterProvider）
├── api/               # client(axios实例) + auth(接口函数)
├── stores/auth.ts     # Zustand 鉴权状态
├── router/            # 路由表 + 登录守卫
├── layouts/           # MainLayout：侧边菜单 + 项目切换 + 用户菜单
├── pages/             # login / workbench / Placeholder（其余模块占位）
└── types/             # 业务类型（可由 OpenAPI 自动生成替代）
```

## 本地启动

```bash
npm install
npm run dev        # http://localhost:5173 （已配置 /api 代理到 localhost:8000）
```

先启动后端（localhost:8000），再运行 `npm run dev`，使用管理员分配的账号登录。

### API 地址约定

默认情况下，前端以 `/api/v1` 为 API 根路径，Vite 只把该命名空间代理到
`http://127.0.0.1:8000`。`/apitest`、`/api-keys` 等前端路由不会进入代理。

独立 worktree 可在忽略的 `.env.local` 中设置 `VITE_PROXY_TARGET` 覆盖后端地址。
如果需要绕过代理直连后端，则配置完整的 v1 根路径，并确保后端允许该前端来源：

```dotenv
VITE_API_BASE=http://localhost:8000/api/v1
```

## 契约同步（前后端不脱节）

后端跑起来后，一条命令从 OpenAPI 生成 TS 类型：

```bash
npm run gen:api    # 读 http://localhost:8000/openapi.json → src/types/api.d.ts
```

## 构建

```bash
npm run build      # 产物在 dist/，由 Nginx 托管（见 Dockerfile）
```
