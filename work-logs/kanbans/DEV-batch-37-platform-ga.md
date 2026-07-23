# 🗂️ Dev 部门项目看板 — batch-37-platform-ga

> **用途**：追踪 batch-37 开发进度。

---

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | 测试平台 GA 补缺 + 工程债务清理 |
| **关联 PM 计划** | [batch-37-platform-ga-pm-plan.md](../batch-37-platform-ga-pm-plan.md) |
| **关联 PRD** | [batch-37-platform-ga-prd-summary.md](../batch-37-platform-ga-prd-summary.md) |
| **关联 Design** | [batch-37-platform-ga-design-spec.md](../batch-37-platform-ga-design-spec.md) |
| **关联 QA** | [batch-37-platform-ga-qa-report.md](../batch-37-platform-ga-qa-report.md) |
| **关联 Leader** | [batch-37-platform-ga-leader-verdict.md](../batch-37-platform-ga-leader-verdict.md) |
| **总预估工时** | 3–4h |
| **看板创建** | 2026-07-23 |
| **最后更新** | 2026-07-23 (✅ 全部完成) |

---

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 批量执行+指派 | ✅ | ✅ | ✅ | ✅ | ⏳ | `d82d765` |
| 2 | 追溯+自动建计划 | ✅ | ✅ | ✅ | ✅ | ⏳ | `0af072b` |
| 3 | 工程债务 | ✅ | ✅ | ✅ | ✅ | ⏳ | `34e3db1` |

---

## 📜 批次记录

### Batch 37 (2026-07-23)
- **产出**:
  - Backend: TestPlan 模型 +2 字段, TestCase +1 字段, Alembic 迁移
  - Backend: execute_all_cases() 批量执行, import_cases 增强 (source_req_id + create_plan)
  - Frontend: PlanDrawer 负责人选择器 + 截止日期, PlanDetail 一键执行按钮
  - Frontend: AiResultModal 自动建计划复选框
  - Eng: Ruff 200→0 违规, npm audit 14→12 漏洞, pyproject.toml ruff 配置
  - 工件: PRD v2.0 / PM Plan / Design Spec / QA Report / Leader Verdict
- **审批**: Leader APPROVED
- **测试**: 522/523 pass (1 预存失败)
- **记录**: [batch-37-platform-ga-prd-summary.md](../batch-37-platform-ga-prd-summary.md)
