# 🗂️ Dev 部门项目看板

> **用途**：追踪多批次开发的进度节点，防止上下文丢失。

---

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | Batch 246 — Engineering Governance & Required Checks |
| **关联 PM 计划** | [work-logs/batch-246-engineering-governance-phase-4-pm-plan.md](../batch-246-engineering-governance-phase-4-pm-plan.md) |
| **关联 PRD** | [work-logs/batch-246-engineering-governance-phase-4-prd-summary.md](../batch-246-engineering-governance-phase-4-prd-summary.md) |
| **总预估工时** | 8h |
| **已用批次** | 1 批 |
| **看板创建** | 2026-09-15 |
| **最后更新** | 2026-09-15 |

---

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 质量 ratchet + 审计 | ✅ | ✅ | ✅ | ⏳ | ⏳ | Ruff/mypy 768/193 no-new |
| 2 | axe/Lighthouse/前端依赖 | ✅ | ✅ | ✅ | ⏳ | ⏳ | axe 28/28，Lighthouse 通过，production audit=0 |
| 3 | Dashboard GROUP BY | ✅ | ✅ | ✅ | ⏳ | ⏳ | C244-1；批统计固定 5 查询 |
| 4 | CI 契约与文档 | ✅ | ✅ | ✅ | ⏳ | ⏳ | contract 10/10，YAML 通过 |

---

## 📍 当前位置

```
Batch 246 — QA 与 Leader 本地评审完成
├── 已完成: 实现、双端全量、axe/Lighthouse、ratchet、依赖审计
├── 🔄 进行中: 等待用户一次总确认
├── ⏳ 待审批: 用户总确认 + PR required checks
└── ⏳ 下一步: push → Draft PR → required checks → final audit → squash merge
```

---

## 📜 批次记录

### Batch 246 — Engineering Governance (2026-09-15)
- **产出**:
  - `481e0dc4` 规划工件
  - `05c18a4c` Ruff/mypy ratchet
  - `8eec1861` Lighthouse/依赖审计
  - `06d3d668` Dashboard 批量聚合
  - `914bf4e0` required CI fail-closed
  - `c35fb73f` 文档回写
  - `dae41a25` axe suite 拆分
  - `6b2a7787` 完整 npm audit ratchet
  - `e76c0660` 完整审计文档
- **审批**: QA PASS（本地）；Leader APPROVED（条件为用户总确认 + CI checks）
- **耗时**: 约 7h
- **记录**: [QA 报告](../batch-246-engineering-governance-phase-4-qa-report.md) / [Leader Verdict](../batch-246-engineering-governance-phase-4-leader-verdict.md)

---

## ⚠️ 阻塞与风险

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| LHCI dev advisories | P2 | 7 high / 1 moderate / 2 low；生产依赖为 0；full audit no-new ratchet | 前端维护者 | 2026-09-15 |
| 历史静态 WARN | P3 | dev-gate WARN=330，HARD=0；不新增 | 全团队 | 2026-09-15 |

---

## 🔗 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD | [link](../batch-246-engineering-governance-phase-4-prd-summary.md) | ✅ |
| PM 计划 | [link](../batch-246-engineering-governance-phase-4-pm-plan.md) | ✅ |
| 设计规范 | [link](../batch-246-engineering-governance-phase-4-design-spec.md) | ✅ |
| QA 报告 | [link](../batch-246-engineering-governance-phase-4-qa-report.md) | ✅ |
| Leader Verdict | [link](../batch-246-engineering-governance-phase-4-leader-verdict.md) | ✅ |
