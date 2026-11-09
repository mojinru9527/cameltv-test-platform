# 🗂️ Dev 看板：Batch 278 决策回写 — baseline 决策入规格

> **用途**：用户确认 D-278-1..3 后，把决策与 4 处口径修正写回 13/14 号与 baseline，解除 M1 的类型歧义。

---

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | AIQE baseline 决策入规格（batch-278 follow-up） |
| **批次号** | batch-278 决策回写（不占 279） |
| **关联文档** | [13 号 v1.3](../../docs/platform-refactor/13-ai-quality-agent-merged-spec.md)、[14 号](../../docs/platform-refactor/14-aiqe-dev-schedule-and-dogfood-plan.md)、[baseline v1.1](../../docs/aiqe/baseline.md) |
| **关联 PR** | 本批新建（feature/batch-278-aiqe-baseline-decisions） |
| **上游 verdict** | [batch-278 Leader verdict](../batch-278-aiqe-ta-001-baseline-audit-leader-verdict.md) §4 |
| **批次模式** | 轻量（PRD-lite + QA + Leader + 看板，docs-only） |
| **Executor** | DeepSeek Harness（agent-team workflow） |
| **分支** | feature/batch-278-aiqe-baseline-decisions |
| **基线与端口** | origin/main `7f205829c`；5208 / 5209 |
| **看板创建** | 2026-11-09 |

---

## 🎯 交付切片进度

| # | 决策 / 修正 | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|------------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | D-278-1 ID 类型（新建 UUID / 旧表 FK BIGINT） | ✅ | ✅ | ✅ | ✅ | 🔄 | §4 规则 + 4 处 `BIGINT FK` |
| 2 | D-278-2 `version_task_run` 候选 B | ✅ | ✅ | ✅ | ✅ | 🔄 | 双写 / 回填 / 只读 / V1.1 删 |
| 3 | D-278-3 前端 `pages/` 目录 | ✅ | ✅ | ✅ | ✅ | 🔄 | 目录树 + 决策段 |
| 4 | 口径修正 ×4（73 表 / 25 表 / 71-123 / 265 paths） | ✅ | ✅ | ✅ | ✅ | 🔄 | 13/14 号同步 |
| 5 | 13 号 v1.3 + baseline 决策已确认 | ✅ | ✅ | ✅ | ✅ | 🔄 | banner + §13 |

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

---

## 📍 当前位置

切片 1-5 全部 ✅；QA 通过、Leader APPROVED；等待 push → PR → checks → merge。

---

## 📝 本批特殊说明

- **不改业务模型**：只把用户已确认的 3 条决策与 4 处口径写成可执行契约；
- **不写 C 条件**：C-278-1/2 由 batch-277 登记（Leader verdict §3）；
- **M0 仍差 2 项**：§0 P0-1..5 + TA-001.5 守卫（batch-277），因此 batch-279（M1）仍不开工。

---

## 📌 下一步

1. push → PR → audit → merge；
2. **batch-277**：§0 P0-1..5 清零 + C-278-1/2 登记 + TA-001.5 守卫（含"新表主键禁 INT"检查）；
3. batch-279：M1 建 8 表 + `environments` 扩字段。
