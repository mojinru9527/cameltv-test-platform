# 🗂️ Dev 部门项目看板 — Batch 88（C87-1/2/3）

> **用途**：追踪 Batch 88 进度节点。Dev 部门启动时必须先读本看板。

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | CamelTv 测试平台 v2 — C87-1 蓝湖设计源 / C87-2 SMTP / C87-3 RBAC（完整批次） |
| **关联 PRD** | [batch-88-c87-lanhu-smtp-rbac-prd-summary.md](../batch-88-c87-lanhu-smtp-rbac-prd-summary.md) |
| **关联 PM 计划** | [batch-88-c87-lanhu-smtp-rbac-pm-plan.md](../batch-88-c87-lanhu-smtp-rbac-pm-plan.md) |
| **关联 Design** | [batch-88-c87-lanhu-smtp-rbac-design-spec.md](../batch-88-c87-lanhu-smtp-rbac-design-spec.md) |
| **看板创建** | 2026-08-05 |
| **执行器** | codex（用户确认 2026-08-05） |
| **Worktree** | F:\CamelTv-worktrees\codex-batch-88-c87-lanhu-smtp-rbac（frontend 5214 / backend 8044） |

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 0 | 环境与凭据核验（蓝湖 Cookie/OCR/SMTP 配置/启动） | ✅ | ✅ | ✅ | ✅ | ⏳ | Cookie/OCR/SMTP 就绪 |
| 1 | C87-3 RBAC seed 矩阵修复（TDD） | ✅ | ✅ | ✅ | ✅ | ⏳ | 5/5 测试 + API 200/403 |
| 2 | C87-1 项目级蓝湖链接支持 + 设计图板分支（TDD） | ✅ | ✅ | ✅ | ✅ | ⏳ | 40/40 测试 |
| 3 | C87-1 真实证据包执行（Web/APP → OCR → 导入 RAG/Wiki） | ✅ | ✅ | ✅ | ✅ | ⏳ | 241+102 页闭环，24 页审核豁免，导入完成 |
| 4 | C87-2 SMTP 真实收发验证（plan_done + defect_assigned） | ✅ | ✅ | ✅ | ✅ | ⏳ | IMAP 收件确认 |
| 5 | 全项目 RBAC 核验矩阵 | ✅ | ✅ | ✅ | ✅ | ⏳ | 项目1/2 矩阵 + 行为验证 |
| 6 | QA 硬门禁 + 回归 + 报告 | ✅ | ✅ | ✅ | ✅ | ⏳ | ruff/pytest/vitest/build 全绿；C87-1/2/3 证据齐备 |
| 7 | Leader 判决 + C 条件同步 + 一次总确认 → PR → 合入 | ✅ | ✅ | ✅ | 🔄 ⬅️ | ⏳ | **当前位置**：等一次总确认 |

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

## 📍 当前位置

```
Batch 88 — C87-1/2/3（完整，全部闭环）
├── ✅ C87-1: 241+102 页证据包 → OCR → 需求/RAG/Wiki 导入（清洗后 0 垃圾）
├── ✅ C87-2: SMTP 真实收发（IMAP 收件确认）
├── ✅ C87-3: 全项目 RBAC 核验 + tester 矩阵修复
├── ✅ QA 门禁全绿 + Leader APPROVED
└── 🔄 等一次总确认（推送 + Draft PR + checks 合入）
```

## 📜 批次记录

### Batch 88 — Slice 0 环境与凭据核验 (2026-08-05)
- **产出**: worktree 后端 .env（合并 AI/蓝湖/OCR/SMTP）、.env.example 同步、后端启动
- **审批**: ✅
- **耗时**: 计划 1h / 实际 1h

### Batch 88 — Slice 1/2 编码 (2026-08-05)
- **产出**: seed.py tester 矩阵（51 项）+ test_rbac_project_roles.py 5/5；lanhu_provider 设计图板分支 + job_runner 图片直采 + 测试 40/40
- **审批**: ✅（自测绿）
- **耗时**: 计划 3h / 实际 2.5h

### Batch 88 — Slice 4/5 验证 (2026-08-05)
- **产出**: SMTP 真实收发证据（IMAP 收件）+ 全项目 RBAC 核验矩阵
- **审批**: ✅
- **耗时**: 计划 2h / 实际 1.5h

## 🔗 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD | [batch-88-c87-lanhu-smtp-rbac-prd-summary.md](../batch-88-c87-lanhu-smtp-rbac-prd-summary.md) | ✅ |
| PM 计划 | [batch-88-c87-lanhu-smtp-rbac-pm-plan.md](../batch-88-c87-lanhu-smtp-rbac-pm-plan.md) | ✅ |
| Design 规范 | [batch-88-c87-lanhu-smtp-rbac-design-spec.md](../batch-88-c87-lanhu-smtp-rbac-design-spec.md) | ✅ |
| QA 报告 | [batch-88-c87-lanhu-smtp-rbac-qa-report.md](../batch-88-c87-lanhu-smtp-rbac-qa-report.md) | ⏳ |
