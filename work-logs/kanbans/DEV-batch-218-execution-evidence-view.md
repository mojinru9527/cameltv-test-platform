# 🗂️ Dev 部门项目看板 — Batch 218 版本任务执行与证据 (B8)

> **Executor**: Codex | **Worktree**: codex-batch-218-execution-evidence-view | **Branch**: feature/batch-218-execution-evidence-view

## 📋 项目信息
| 字段 | 值 |
|------|-----|
| **项目名称** | 版本任务执行与证据（B8 前后端） |
| **关联 PM 计划** | [work-logs/batch-218-execution-evidence-view-pm-plan.md](../batch-218-execution-evidence-view-pm-plan.md) |
| **关联 PRD** | [work-logs/batch-218-execution-evidence-view-prd-summary.md](../batch-218-execution-evidence-view-prd-summary.md) |
| **总预估工时** | ~5h |
| **已用批次** | 1 |
| **看板创建** | 2026-09-05 |

## 🎯 交付切片进度
| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | version_task_run 模型+迁移 | ✅ | ✅ | ✅ | ⏳ | ⏳ | |
| 2 | run + 覆盖回写 + 失败分类 + 缺陷草稿 | ✅ | ✅ | ✅ | ⏳ | ⏳ | |
| 3 | API + route_inventory | ✅ | ✅ | ✅ | ⏳ | ⏳ | |
| 4 | 前端详情页 | ✅ | ✅ | ✅ | ⏳ | ⏳ | |
| 5 | 测试 | ✅ | ✅ | ✅ | ⏳ | ⏳ | |

## 📍 当前位置
```
Batch 218 — 执行与证据
├── 已完成: 模型/迁移/run/分类/缺陷草稿/API/前端详情页 编码+自测（后端 11 测试绿；前端 typecheck/lint/build/vitest 608 绿）
├── 🔄 进行中: 后端全量回归
├── ⏳ 待审批: 用户一次总确认（已提前授权 B6-B15 推送+PR+合入）
└── ⏳ 下一步: required checks 全绿后合入 main
```

## 📜 批次记录
### Batch 218 (2026-09-05)
- **产出**: version_task_run 模型/迁移 + run/coverage/失败四分类/缺陷草稿 + 4 API + 前端详情页 + 3 后端测试
- **审批**: 待合入
- **耗时**: ~5h
- **记录**: work-logs/batch-218-*-{prd,pm,design,qa,verdict}

## ⚠️ 阻塞与风险
| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| 无 | — | — | — | — |

## 🔗 相关工件
| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD | work-logs/batch-218-execution-evidence-view-prd-summary.md | ✅ |
| PM 计划 | work-logs/batch-218-execution-evidence-view-pm-plan.md | ✅ |
| 设计规范 | work-logs/batch-218-execution-evidence-view-design-spec.md | ✅ |
| QA 报告 | work-logs/batch-218-execution-evidence-view-qa-report.md | ⏳ |
| Leader 判决 | work-logs/batch-218-execution-evidence-view-leader-verdict.md | ⏳ |
