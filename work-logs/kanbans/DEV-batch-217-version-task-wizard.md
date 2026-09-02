# 🗂️ Dev 部门项目看板 — Batch 217 版本验收建任务向导 (B7)

> **Executor**: Codex | **Worktree**: codex-batch-217-version-task-wizard | **Branch**: feature/batch-217-version-task-wizard

## 📋 项目信息
| 字段 | 值 |
|------|-----|
| **项目名称** | 版本验收建任务向导（B7 前后端） |
| **关联 PM 计划** | [work-logs/batch-217-version-task-wizard-pm-plan.md](../batch-217-version-task-wizard-pm-plan.md) |
| **关联 PRD** | [work-logs/batch-217-version-task-wizard-prd-summary.md](../batch-217-version-task-wizard-prd-summary.md) |
| **总预估工时** | ~5h |
| **已用批次** | 1 |
| **看板创建** | 2026-09-05 |

## 🎯 交付切片进度
| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 后端方案条目模型+迁移 | ✅ | ✅ | ✅ | ⏳ | ⏳ | |
| 2 | 生成+审核 service | ✅ | ✅ | ✅ | ⏳ | ⏳ | |
| 3 | API + route_inventory | ✅ | ✅ | ✅ | ⏳ | ⏳ | |
| 4 | 前端 API client + 向导页 | ✅ | ✅ | ✅ | ⏳ | ⏳ | |
| 5 | 测试 | ✅ | ✅ | ✅ | ⏳ | ⏳ | |

## 📍 当前位置
```
Batch 217 — 版本验收向导
├── 已完成: 模型/迁移/生成+审核/API/前端向导 编码+自测（后端 version_task 8 测试绿；前端 typecheck/lint/build/vitest 608 绿；batch54 守卫绿）
├── 🔄 进行中: 后端全量回归
├── ⏳ 待审批: 用户一次总确认（已提前授权 B6-B15 推送+PR+合入）
└── ⏳ 下一步: required checks 全绿后合入 main
```

## 📜 批次记录
### Batch 217 (2026-09-05)
- **产出**: version_task_plan_item 模型/迁移 + 生成/审核 service + 3 API + 前端向导页 + 8 后端测试
- **审批**: 待合入
- **耗时**: ~5h
- **记录**: work-logs/batch-217-*-{prd,pm,design,qa,verdict}

## ⚠️ 阻塞与风险
| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| 无 | — | — | — | — |

## 🔗 相关工件
| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD | work-logs/batch-217-version-task-wizard-prd-summary.md | ✅ |
| PM 计划 | work-logs/batch-217-version-task-wizard-pm-plan.md | ✅ |
| 设计规范 | work-logs/batch-217-version-task-wizard-design-spec.md | ✅ |
| QA 报告 | work-logs/batch-217-version-task-wizard-qa-report.md | ⏳ |
| Leader 判决 | work-logs/batch-217-version-task-wizard-leader-verdict.md | ⏳ |
