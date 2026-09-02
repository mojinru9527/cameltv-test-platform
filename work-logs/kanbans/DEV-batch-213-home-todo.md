# 🗂️ Dev 部门项目看板 — Batch 213 首页我的待办（B3 / home-todo）

## 📋 项目信息
| 字段 | 值 |
|------|-----|
| **项目名称** | 平台重构 B3：工作台改「我的待办」（待审/在跑/失败/待放行聚合）+ dashboard API |
| **关联 PRD** | [batch-213-home-todo-prd-summary.md](../batch-213-home-todo-prd-summary.md) |
| **总预估工时** | 约 4h（实际约 4h） |
| **已用批次** | 1 批（完整：前后端） |
| **看板创建** | 2026-09-02 |
| **最后更新** | 2026-09-02 |

## 🎯 交付切片进度
| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 后端 dashboard/todo 聚合接口（schema/service/route + pytest） | ✅ | ✅ | ✅ | ⏳ | ⏳ | pytest 2 绿 |
| 2 | 前端 API + 类型（fetchDashboardTodo / DashboardTodo） | ✅ | ✅ | ✅ | ⏳ | ⏳ | typecheck 绿 |
| 3 | 前端「我的待办」页面重写（四区 + 直达链接 + 四态） | ✅ | ✅ | ✅ | ⏳ | ⏳ | vitest 612 绿 |
| 4 | 首页落地到「我的待办」（PlatformHomeEntry → /workbench） | ✅ | ✅ | ✅ | ⏳ | ⏳ | vitest 612 绿 |
| 5 | 路线图 §5 交接区 + C-CONDITIONS + 合规工件 | ✅ | ✅ | ✅ | ⏳ | ⏳ | — |
| 6 | QA：硬门禁 + 小白走查（tester 真实登录） | ✅ | ✅ | ✅ | ⏳ | ⏳ | 走查证据 work-logs/evidence/batch-213/ |

## 📍 当前位置
```
Batch 213（B3）— 开发与 QA 证据就绪
├── ✅ 后端 GET /api/v1/dashboard/todo（待审/在跑/失败/待放行 四桶 + count + items）
├── ✅ 前端 /workbench = 「我的待办」页面（四区可点直达 + 空态 + 四态）
├── ✅ 登录首页 / → /workbench（我的待办）；/missions 仍可经「版本验收」菜单直达
├── ✅ 硬门禁：frontend typecheck/build/lint/vitest 612 + backend ruff F821 + 相关 pytest
├── ✅ 小白走查（tester 真实登录）证据 work-logs/evidence/batch-213/
└── ⏳ 待 Leader APPROVED → push → Draft PR → checks 绿 → squash 合入 main
```

## ⚠️ 阻塞与风险
| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| 无 | — | — | — | — |

## 🔗 相关工件
| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD | work-logs/batch-213-home-todo-prd-summary.md | ✅ |
| PM 计划 | work-logs/batch-213-home-todo-pm-plan.md | ✅ |
| Design 规范 | work-logs/batch-213-home-todo-design-spec.md | ✅ |
| QA 报告 | work-logs/batch-213-home-todo-qa-report.md | ✅ |
| Leader 判决 | work-logs/batch-213-home-todo-leader-verdict.md | ✅ |
| 走查证据 | work-logs/evidence/batch-213/ | ✅ |
| C 条件 | C-CONDITIONS.md（batch-213 处理记录） | ✅ |
