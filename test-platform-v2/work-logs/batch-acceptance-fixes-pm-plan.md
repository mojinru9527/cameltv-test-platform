# batch-acceptance-fixes — PM Plan

> **PM (🟨)** | Date: 2026-07-19 | Status: 执行中

## 批次概述

修复 2026-07-19 全平台验收发现的 6 个问题 (P1×2, P2×2, P3×2)。

## 任务分解

| # | Slice | 任务 | 估时 | 涉及文件 | 验收标准 |
|---|-------|------|------|---------|---------|
| 1 | P1 | Perftest 路由+菜单注册 | 20min | `seed.py`, `router/index.tsx` | `/perftest` 页面可访问，侧边栏可见「性能监控」 |
| 2 | P1 | X-Project-Id 文档补充 | 5min | `backend/CLAUDE.md` | 文档明确说明 header 要求 |
| 3 | P2 | CLAUDE.md 成熟度标注修正 | 10min | `test-platform-v2/CLAUDE.md`, `frontend/CLAUDE.md` | 三模块标注与实际一致 |
| 4 | P2 | useApi<any> 类型安全修复 | 30min | 7 个页面文件 + `types/index.ts` | 0 个 `useApi<any>` 残留 |
| 5 | P3 | 前端 CLAUDE.md 目录结构补全 | 10min | `frontend/CLAUDE.md` | 包含所有现有模块 |
| 6 | P3 | Workbench 空状态引导 | 15min | `workbench/index.tsx` | 无数据时显示行动指引 |

## 执行顺序

Slice 1-3 可并行（独立文件），Slice 4-6 建议顺序执行。
