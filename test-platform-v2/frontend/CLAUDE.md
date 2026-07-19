---
title: "test-platform-v2/frontend — React 前端"
owner: "frontend-team"
last_reviewed: "2026-06-26"
status: "active"
expires: "2026-12-26"
tags: ["frontend", "react", "typescript", "shadcn-ui", "zustand"]
related: ["../backend/CLAUDE.md", "../../docs/adr/0005-zustand-over-redux.md", "../../docs/adr/0006-shadcn-ui-over-antd.md"]
---

# test-platform-v2/frontend — React 前端

> React 18 + TypeScript + Vite 5 + shadcn/ui (Radix UI + Tailwind CSS)

## 目录结构

```
frontend/
├── src/
│   ├── main.tsx               入口 (ConfigProvider + RouterProvider)
│   ├── api/                   Axios client + 接口函数
│   │   └── client.ts          Axios 实例 (JWT 拦截器 + envelope 拆包)
│   ├── stores/                Zustand 状态管理
│   │   └── auth.ts            鉴权状态 (localStorage 持久化)
│   ├── router/                React Router 6 路由表 + 登录守卫
│   ├── layouts/               MainLayout (侧边菜单 + 项目切换 + 用户菜单)
│   ├── pages/                 页面组件
│   │   ├── login/             登录页
│   │   ├── workbench/         工作台
│   │   ├── project/           项目管理
│   │   ├── system/            系统管理 (用户/角色/审计)
│   │   ├── testcase/          用例管理
│   │   ├── testplan/          测试计划
│   │   ├── requirement/       需求管理
│   │   ├── report/            报告中心
│   │   ├── schedule/          定时任务
│   │   ├── defect/            缺陷管理
│   │   ├── trace/             质量追溯
│   │   ├── apitest/           API 测试
│   │   ├── uitest/            UI 自动化
│   │   ├── special/           音视频专项
│   │   ├── perftest/          性能监控
│   │   ├── knowledge/         知识中心
│   │   ├── notify/            通知管理
│   │   ├── environment/       环境配置
│   │   ├── dataset/           测试数据集
│   │   ├── integration/       集成配置
│   │   └── agent-workbench/   Agent 工作台
│   ├── components/            shadcn/ui 组件 (34 个)
│   ├── hooks/                 自定义 hooks
│   ├── lib/                   工具函数 (cn, formatters)
│   └── types/                 业务类型 (OpenAPI 自动生成)
├── package.json
├── vite.config.ts             Vite 配置 (proxy /api → localhost:8000)
├── tailwind.config.ts
├── tsconfig.json
└── Dockerfile                 Nginx 静态站点
```

## 技术选型约定

| 功能 | 选择 | 说明 |
|------|------|------|
| UI 组件库 | shadcn/ui (Radix + Tailwind) | 源码可控，无障碍优先 |
| 状态管理 | Zustand | 轻量，支持 localStorage 持久化 |
| 路由 | React Router 6 | 登录守卫 + 动态菜单 |
| HTTP 客户端 | Axios | JWT 拦截器 + 统一 envelope 拆包 |
| 表单 | React Hook Form + Zod | 类型安全校验 |
| 图表 | Recharts | 工作台看板 |
| 表格 | TanStack Table | 用例/计划列表 |
| 通知 | Sonner (toast) | 操作反馈 |
| 图标 | Lucide Icons | 轻量开源 |
| 类型生成 | openapi-typescript | 从后端 /openapi.json 自动生成 |

## API 契约同步

```bash
# 后端启动后，生成 TS 类型（输出到 src/types/api.d.ts）
npm run gen:api
```

- Axios 实例在 `src/api/client.ts`：自动附加 JWT → 解包 `{ code, message, data }` → code≠0 抛异常
- 接口函数在 `src/api/` 下按模块划分，函数名与后端 API 路径对应

## Zustand Store 约定

- 鉴权状态 `authStore`：`token` / `user` / `currentProject`，持久化到 localStorage
- 其他 Store 按页面模块划分，不持久化
- Store 内部不做 API 调用——API 调用在页面组件或 hooks 中完成，Store 只存状态

## 路由约定

```
/login              → 登录页 (公开)
/                   → 重定向到 /workbench
/workbench          → 工作台 (需登录)
/project            → 项目管理
/system/*           → 系统管理 (用户/角色/审计)
/testcase           → 用例管理
/testplan           → 测试计划
/requirement        → 需求管理
/report             → 报告中心
/schedule           → 定时任务
/defect             → 缺陷管理
/trace              → 质量追溯
/apitest            → API 测试
/uitest             → UI 自动化
/special            → 音视频专项
/perftest           → 性能监控
/notify             → 通知管理
/environment        → 环境配置
/dataset            → 测试数据集
/integration        → 集成配置
/knowledge          → 知识中心
/agent-workbench    → Agent 工作台
```

## 本地开发

```bash
npm install
npm run dev          # http://localhost:5173
npm run build        # 生产构建 → dist/
npm run gen:api      # 同步后端 API 类型
npx vitest           # 运行测试
```

## 常见陷阱

- **演示态模块**（special）：数据为前端随机生成，不连接真实后端服务。修改时注意区分
- **真实执行引擎**（apitest/uitest/perftest）：已连接真实后端服务，通过 httpx/Playwright/WebSocket 执行实际测试
- **JWT 过期**：Axios 拦截器处理 401，自动跳转登录。后端 token 过期时间在 `core/config.py` 配置
- **shadcn/ui 组件**：直接用 `npx shadcn-ui@latest add <component>` 添加，组件在 `src/components/ui/`
- **Tailwind**：使用 `cn()` 工具函数（clsx + tailwind-merge）合并类名，不要直接用字符串拼接
