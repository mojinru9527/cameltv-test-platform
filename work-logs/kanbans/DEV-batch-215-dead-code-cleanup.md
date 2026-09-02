# 🗂️ Dev 部门项目看板 — Batch 215 死代码清理 (B5)

> **用途**：追踪多批次开发进度。本批 B5 删除 /testplan、Playground 独立页、无引用前端组件，清理根目录临时物。
> **Executor**: Codex | **Worktree**: codex-batch-215-dead-code-cleanup | **Branch**: feature/batch-215-dead-code-cleanup

## 📋 项目信息
| 字段 | 值 |
|------|-----|
| **项目名称** | 测试平台 M0 死代码清理 |
| **关联 PM 计划** | [work-logs/batch-215-dead-code-cleanup-pm-plan.md](../batch-215-dead-code-cleanup-pm-plan.md) |
| **关联 PRD** | [work-logs/batch-215-dead-code-cleanup-prd-summary.md](../batch-215-dead-code-cleanup-prd-summary.md) |
| **总预估工时** | ~4h |
| **已用批次** | 1（本批） |
| **看板创建** | 2026-09-03 |
| **最后更新** | 2026-09-03 |

## 🎯 交付切片进度
| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 删除 /testplan 独立页 | ✅ | ✅ | ✅ | ⏳ | ⏳ | |
| 2 | 删除 Playground 独立页 | ✅ | ✅ | ✅ | ⏳ | ⏳ | |
| 3 | 删除无引用前端组件/Hook | ✅ | ✅ | ✅ | ⏳ | ⏳ | |
| 4 | special/perftest 冻结 + V1 工具文档 | ✅ | ✅ | ✅ | ⏳ | ⏳ | |
| 5 | 根目录 `_tmp_*`/临时文件清理 | ✅ | ✅ | ✅ | ⏳ | ⏳ | |

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

## 📍 当前位置
```
Batch 215 — 死代码清理
├── 已完成: Task1-5 编码 + 自测（前端 typecheck/lint/build/vitest 全绿；后端 F821/import/menu 测试绿）
├── 🔄 进行中: 收尾（kanban + 工件 → QA → Leader）
├── ⏳ 待审批: 用户一次总确认（推送+PR+合入，已获提前授权）
└── ⏳ 下一步: required checks 通过后合入 main
```

## 📜 批次记录
### Batch 215 — 死代码清理 (2026-09-03)
- **产出**: 
  - 删除 `frontend/src/pages/testplan/`（整页+自测）
  - 删除 `frontend/src/pages/testcase/playground/index.tsx`
  - 删除无引用前端组件/Hook ×18（含 ui primitives 7、SphereTab、ApiDebugPanel、EnvironmentBar、StagePlaceholder、PolicyDecisionDrawer、RetryHistory、ExtractionModal、ListToolbar、VerificationLevelBadge、useA11y、usePaginatedList）
  - 更新 `touchTargetGuard.test.ts`、`batch54-production-governance.test.ts`、`eslint-suppressions.json`
  - `COMMANDS.md` §5 V1 工具已退役标注；`.gitignore` 新增 `_tmp_*` 等；删除 `.pr-body-batch20/22.md`；`repo-boundaries.json` 移除已删除条目
- **审批**: 待用户总确认
- **耗时**: ~4h
- **记录**: work-logs/batch-215-*-{prd,pm,design,qa,verdict}

## ⚠️ 阻塞与风险
| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| 根目录历史文档归档 | P3 | 5 个根历史方案/重复文档需连同 repo-boundaries/CLAUDE/repo-map 引用一并处理，涉及跨文件引用更新，风险大于收益，移交后续文档重构批次 | owner | 2026-09-03 |

## 🔗 相关工件
| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD | work-logs/batch-215-dead-code-cleanup-prd-summary.md | ✅ |
| PM 计划 | work-logs/batch-215-dead-code-cleanup-pm-plan.md | ✅ |
| 设计规范 | work-logs/batch-215-dead-code-cleanup-design-spec.md | ✅ |
| QA 报告 | work-logs/batch-215-dead-code-cleanup-qa-report.md | ⏳ |
| Leader 判决 | work-logs/batch-215-dead-code-cleanup-leader-verdict.md | ⏳ |
