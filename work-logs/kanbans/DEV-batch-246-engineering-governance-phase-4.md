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
| 1 | 质量 ratchet + 审计 | ✅ | 🔄 ⬅️ | ⏳ | ⏳ | ⏳ | 当前切片 |
| 2 | axe/Lighthouse/前端依赖 | ✅ | 🔄 | ⏳ | ⏳ | ⏳ | |
| 3 | Dashboard GROUP BY | ✅ | ✅ | ✅ | ⏳ | ⏳ | C244-1 |
| 4 | CI 契约与文档 | ✅ | 🔄 | ⏳ | ⏳ | ⏳ | |

---

## 📍 当前位置

```
Batch 246 — Engineering Governance
├── 已完成: 设计/任务拆分、批量统计实现、主要 CI 修改
├── 🔄 进行中: 本地全量与契约门禁复验
├── ⏳ 待审批: QA/Leader
└── ⏳ 下一步: 用户一次总确认 → PR → required checks
```

---

## ⚠️ 阻塞与风险

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| LHCI dev advisories | P3 | required 审计聚焦生产依赖；开发链漏洞持续跟踪上游修复 | 前端维护者 | 2026-09-15 |
| 历史静态债务 | P2 | Ruff/mypy baseline 仅允许下降 | 全团队 | 2026-09-15 |

---

## 🔗 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD | [link](../batch-246-engineering-governance-phase-4-prd-summary.md) | ✅ |
| PM 计划 | [link](../batch-246-engineering-governance-phase-4-pm-plan.md) | ✅ |
| 设计规范 | [link](../batch-246-engineering-governance-phase-4-design-spec.md) | ✅ |
| QA 报告 | [link](../batch-246-engineering-governance-phase-4-qa-report.md) | ⏳ |
| Leader Verdict | [link](../batch-246-engineering-governance-phase-4-leader-verdict.md) | ⏳ |
