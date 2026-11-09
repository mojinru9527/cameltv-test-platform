# 🗂️ Dev 看板：Batch 278 — AIQE TA-001 代码基线审计

> **用途**：M1 开工前把 13 号目标模型与仓库真实代码逐项对账，产出 `docs/aiqe/baseline.md`，并暴露 10 条冲突 + 3 条待用户决策。

---

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | AIQE TA-001 代码基线审计 |
| **批次号** | batch-278 |
| **关联文档** | [docs/aiqe/baseline.md](../../docs/aiqe/baseline.md) |
| **关联 PR** | 本批新建（feature/batch-278-aiqe-ta-001-baseline-audit） |
| **关联排期** | [14 号 §4.1](../../docs/platform-refactor/14-aiqe-dev-schedule-and-dogfood-plan.md) |
| **批次模式** | 完整批次（docs-only）：PRD + PM + Design + Dev + QA + Leader + 看板 |
| **Executor** | DeepSeek Harness（agent-team workflow） |
| **分支** | feature/batch-278-aiqe-ta-001-baseline-audit |
| **基线与端口** | origin/main `0af75a821`；5206 / 5207 |
| **总预估工时** | 5 人日（14 号 W1~W2） |
| **看板创建** | 2026-11-09 |

---

## 🎯 交付切片进度

| # | 任务 | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|------|:----:|:----:|:----:|:----:|:----:|------|
| T278-1 | 43 文件 / 73 表 AST 盘点 | ✅ | ✅ | ✅ | ✅ | 🔄 | 主键 INT×72 / str×1 |
| T278-2 | 25 表逐表对账（315 字段 / ≈2090 行） | ✅ | ✅ | ✅ | ✅ | 🔄 | 22 新建 + 2 兼容 + 3 扩展 |
| T278-3 | 8 接入点 + 附加服务对账 | ✅ | ✅ | ✅ | ✅ | 🔄 | 9 路径全存在 |
| T278-4 | 30 规格端点 vs 265 paths / 323 ops | ✅ | ✅ | ✅ | ✅ | 🔄 | 29 个净新增 |
| T278-5 | 前端 + Driver/Node 能力 | ✅ | ✅ | ✅ | ✅ | 🔄 | 19 域 / 153 组件 / 30 路由 |
| T278-6 | 执行链时序 + 迁移批次 + 冲突登记 | ✅ | ✅ | ✅ | ✅ | 🔄 | 3 条链 / 10 冲突 |

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

---

## 📍 当前位置

T278-1..6 全部 ✅；QA 通过、Leader 🟡 APPROVED（附"用户阅读确认"条件）；等待 push → Draft PR → checks → merge。

---

## 📝 本批特殊说明

- **docs-only**：只新增 `docs/aiqe/baseline.md` + work-logs，不改代码/迁移/CI；
- **统计口径修正**：43 文件 / 73 表（非 43 表）、25 目标表（22 净新建）、71 顶层服务 / 123 递归、265 paths；
- **不替用户决策**：D-278-1（ID 类型）/ D-278-2（version_task_run）/ D-278-3（前端目录）显式留给用户；
- **M1 前置**：batch-274 verdict 规定"baseline 未产出前，TA-005+ 代码 PR 必须打回"——本批合入后解除。

---

## 📌 下一步

1. push 分支 → Draft PR → `audit-ai-pr` → squash merge；
2. 用户阅读 baseline §0/§3/§13 并对 D-278-1..3 表态；
3. batch-277（§0 P0 清零）与 batch-279（M1 建表）按排期推进；D-278-1 确认前不合并 test_runs 迁移脚本。
