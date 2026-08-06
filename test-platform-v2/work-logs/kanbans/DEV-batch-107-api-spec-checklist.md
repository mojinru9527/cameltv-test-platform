# 🗂️ Dev 部门项目看板 — Batch 107（接口用例生成「测试考虑点」全量固化）

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | 接口用例生成规范补全（XMind 测试考虑点固化 + 响应结构断言 + 稳定性/兼容性/监控） |
| **关联 PRD** | [batch-107-api-spec-checklist-prd-summary.md](../batch-107-api-spec-checklist-prd-summary.md) |
| **关联 PM 计划** | [batch-107-api-spec-checklist-pm-plan.md](../batch-107-api-spec-checklist-pm-plan.md) |
| **关联 Design** | [batch-107-api-spec-checklist-design-spec.md](../batch-107-api-spec-checklist-design-spec.md) |
| **看板创建** | 2026-08-06 |
| **执行器** | codex（用户确认未来 10 版本沿用） |
| **Worktree** | F:\CamelTv-worktrees\codex-batch-107-api-spec-checklist |

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 批次工件 + 规范落盘（PRD/PM/Design/看板 + 接口测试考虑点.md） | ✅ | ✅ | ✅ | ✅ | ⏳ | commit 73404bb |
| 2 | 规则生成器扩展（9 类新模板 + 响应结构断言） | ✅ | ✅ | ✅ | ✅ | ⏳ | commit c27363a；实测 35 条含业务断言 |
| 3 | AI 提示词注入 + 前端/schema 模板默认值 | ✅ | ✅ | ✅ | ✅ | ⏳ | 上下文 6.6KB 含检查清单；tsc/build/vitest 通过 |
| 4 | 单测 + QA + Leader + 一次总确认 | ✅ | ✅ | ✅ | 🔄 ⬅️ | ⏳ | **当前位置**：等一次总确认 |

## 📍 当前位置

```
Batch 107 — 接口用例生成「测试考虑点」全量固化（完成，等一次总确认）
├── ✅ 规范落盘：接口测试考虑点【辅助作用】.md（101 节点）+ CLAUDE.md/api-checklist 引用
├── ✅ 生成器：9 类新模板 + 真实样本响应结构断言（list_visible 35 条含业务断言）
├── ✅ AI 提示词注入检查清单；前端/schema 默认模板 15 项
├── ✅ QA：54 pytest + tsc/build/vitest + scan HARD 0 + boundary PASS
└── 🔄 等一次总确认（push + Draft PR + required checks 后合入）
```

## 📜 批次记录

### Batch 107 — 接口用例生成规范补全 (2026-08-06)
- **产出**: PRD/PM/Design/看板 + 规范落盘 + 9 类新模板 + 响应结构断言 + AI 提示词 + 单测 10 条 + QA/Leader
- **审批**: Leader APPROVED（待用户一次总确认）
- **耗时**: 0.5d
- **记录**: QA B107-1（知识导入受阻）/ B107-2（场景待关联）；C107-1/C107-2 登记

## ⚠️ 阻塞与风险

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| 场景测试无接口关联信息 | P2 | 单接口生成器无关联图谱；先产出「场景测试建议」待关联用例 | 接口关联配置后续批次 | 2026-08-06 |
| 知识中心导入 | P2 | C102-2 capture 若仍 409，仅登记障碍 | 后续批次 | 2026-08-06 |

## 🔗 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD | [batch-107-api-spec-checklist-prd-summary.md](../batch-107-api-spec-checklist-prd-summary.md) | ✅ |
| PM 计划 | [batch-107-api-spec-checklist-pm-plan.md](../batch-107-api-spec-checklist-pm-plan.md) | ✅ |
| 设计规范 | [batch-107-api-spec-checklist-design-spec.md](../batch-107-api-spec-checklist-design-spec.md) | ✅ |
| QA 报告 | [batch-107-api-spec-checklist-qa-report.md](../batch-107-api-spec-checklist-qa-report.md) | ⏳ |
