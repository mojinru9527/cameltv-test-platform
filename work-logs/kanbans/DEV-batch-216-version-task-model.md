# 🗂️ Dev 部门项目看板 — Batch 216 版本任务统一事实源 (B6)

> **Executor**: Codex | **Worktree**: codex-batch-216-version-task-model | **Branch**: feature/batch-216-version-task-model

## 📋 项目信息
| 字段 | 值 |
|------|-----|
| **项目名称** | 版本验收任务（B6 后端+DB） |
| **关联 PM 计划** | [work-logs/batch-216-version-task-model-pm-plan.md](../batch-216-version-task-model-pm-plan.md) |
| **关联 PRD** | [work-logs/batch-216-version-task-model-prd-summary.md](../batch-216-version-task-model-prd-summary.md) |
| **总预估工时** | ~4h |
| **已用批次** | 1 |
| **看板创建** | 2026-09-03 |
| **最后更新** | 2026-09-03 |

## 🎯 交付切片进度
| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | VersionTask 模型 | ✅ | ✅ | ✅ | ⏳ | ⏳ | |
| 2 | Alembic 单头迁移 + drill | ✅ | ✅ | ✅ | ⏳ | ⏳ | |
| 3 | Schema + Service（状态机/兼容映射） | ✅ | ✅ | ✅ | ⏳ | ⏳ | |
| 4 | API + route_inventory | ✅ | ✅ | ✅ | ⏳ | ⏳ | |
| 5 | tests | ✅ | ✅ | ✅ | ⏳ | ⏳ | |

## 📍 当前位置
```
Batch 216 — VersionTask 统一事实源
├── 已完成: 模型/迁移/Schema/Service/API/测试 编码+自测（version_task 6 测试绿；ruff 新文件绿；route_inventory 绿；alembic 单头 drill 通过）
├── 🔄 进行中: 后端全量回归
├── ⏳ 待审批: 用户一次总确认（已提前授权 B6-B15 推送+PR+合入）
└── ⏳ 下一步: required checks 全绿后合入 main
```

## 📜 批次记录
### Batch 216 (2026-09-03)
- **产出**: version_task 模型/迁移/Schema/Service/API + 6 测试 + route_inventory 617 条
- **审批**: 待合入
- **耗时**: ~4h
- **记录**: work-logs/batch-216-*-{prd,pm,design,qa,verdict}

## ⚠️ 阻塞与风险
| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| 无 | — | — | — | — |

## 🔗 相关工件
| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD | work-logs/batch-216-version-task-model-prd-summary.md | ✅ |
| PM 计划 | work-logs/batch-216-version-task-model-pm-plan.md | ✅ |
| 设计规范 | work-logs/batch-216-version-task-model-design-spec.md | ✅ |
| QA 报告 | work-logs/batch-216-version-task-model-qa-report.md | ⏳ |
| Leader 判决 | work-logs/batch-216-version-task-model-leader-verdict.md | ⏳ |
