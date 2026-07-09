# 🗂️ Dev 部门项目看板 — 批次九: V2.7 报告增强收尾 (R3+R4)

> **最后更新**: 2026-07-02 | **看板创建**: 2026-07-02
>
> ⚠️ 每次 Dev 部门启动处理本批次时，**先读本看板**确认当前进度。

---

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | 批次九 — V2.7 报告增强收尾 (R3 质量门禁 + R4 报告模板) |
| **关联 PM 计划** | N/A（Backlog 驱动） |
| **关联 PRD** | N/A（Backlog 驱动） |
| **总预估工时** | 14h (R3: 2h + R4: 12h) |
| **已用批次** | 1 批 |
| **看板创建** | 2026-07-02 |
| **最后更新** | 2026-07-02 |

---

## 🎯 交付切片进度

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

### R3 质量门禁规则 (P2, HITL) — 已完成 ✅

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | R3a 门禁配置模型+API | ✅ | ✅ | ✅ | ✅ | ✅ | **已有**: QualityGateConfig 模型 + CRUD API (project.py) |
| 2 | R3b 报告生成门禁判定 | ✅ | ✅ | ✅ | ✅ | ✅ | **已有**: `_compute_gate()` + TestReport.gate_status/details |
| 3 | R3c 前端门禁配置页+展示 | ✅ | ✅ | ✅ | ✅ | ✅ | **已有**: QualityGateCard (project) + Badge 展示 (report) |
| 4 | R3d Alembic 迁移 + SMOKE | ✅ | ✅ | ✅ | ✅ | ✅ | **新增**: migration 0007 + 8 smoke tests PASS |
| 5 | R3e HITL 维度扩展 | — | — | — | — | — | **决策 A**: 保持现有 3 维，后续 backlog 跟进 |

### R4 报告模板配置 (P2, AFK) — 已完成 ✅

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 6 | R4a 模板模型+Schema+Alembic | ✅ | ✅ | ✅ | ✅ | ✅ | ReportTemplate ORM + Pydantic + migrations 0008/0009 |
| 7 | R4b 模板服务层+API | ✅ | ✅ | ✅ | ✅ | ✅ | 模板 CRUD + 预览端点 (6 endpoints) |
| 8 | R4c 报告生成套用模板 | ✅ | ✅ | ✅ | ✅ | ✅ | ReportCreate.template_id + create_report stores template |
| 9 | R4d 前端模板管理页 | ✅ | ✅ | ✅ | ✅ | ✅ | TemplateManager + 创建对话框模板选择器 |

---

## 📍 当前位置

```
批次九 — V2.7 报告增强收尾
├── ✅ R3 质量门禁: 全部完成 (5/5 slices)
├── ✅ R4 报告模板: 全部完成 (4/4 slices)
├── ✅ 烟雾测试: 22/22 PASS (R3: 8 + R4: 14)
└── 🎉 V2.7 批次完成！
```

---

## 📜 批次记录

| 批次 | 日期 | 摘要 |
|------|------|------|
| 1 | 2026-07-02 | R3+R4 全部完成。新增 3 Alembic 迁移 (0007-0009)、ReportTemplate 模型/服务/API、前端模板管理器 + 模板选择器。22 个烟雾测试全部通过。 |

---

## 🔗 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| 改进 Backlog | [改进任务backlog.md](../../test-platform-v2/docs/改进任务backlog.md) | 📋 |
| R3+R4 方案设计 | [R3-R4-方案设计.md](../R3-R4-方案设计.md) | ✅ |
| 烟雾测试 | [test_v27_smoke.py](../../test-platform-v2/backend/tests/test_v27_smoke.py) | ✅ |
| Migration 0007 | [20260702_0007_quality_gate.py](../../test-platform-v2/backend/alembic/versions/20260702_0007_quality_gate.py) | ✅ |
| Migration 0008 | [20260702_0008_report_template.py](../../test-platform-v2/backend/alembic/versions/20260702_0008_report_template.py) | ✅ |
| Migration 0009 | [20260702_0009_test_report_template_id.py](../../test-platform-v2/backend/alembic/versions/20260702_0009_test_report_template_id.py) | ✅ |
