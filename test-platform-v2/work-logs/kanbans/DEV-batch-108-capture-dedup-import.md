# 🗂️ Dev 部门项目看板 — Batch 108（capture 去重误判修复 + 规范导入闭环）

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | 知识中心 capture 409 误报修复 + 接口测试考虑点文档导入闭环 |
| **关联 PRD** | [batch-108-capture-dedup-import-prd-summary.md](../batch-108-capture-dedup-import-prd-summary.md) |
| **关联 PM 计划** | [batch-108-capture-dedup-import-pm-plan.md](../batch-108-capture-dedup-import-pm-plan.md) |
| **关联 Design** | [batch-108-capture-dedup-import-design-spec.md](../batch-108-capture-dedup-import-design-spec.md) |
| **看板创建** | 2026-08-06 |
| **执行器** | codex（用户确认未来 10 版本沿用） |
| **Worktree** | F:\CamelTv-worktrees\codex-batch-108-capture-dedup-import |

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 工件 + 根因（PRD/PM/Design/看板） | ✅ | ✅ | ✅ | ✅ | ⏳ | commit 8e7c9b2（根因：开关关+混义+hooks 翻转） |
| 2 | ingest 类型化 + 路由映射 + 配置 | ✅ | ✅ | ✅ | ✅ | ⏳ | CaptureIngestResult + 503/409/500/200 + env 开关 |
| 3 | 单测 + 生产导入闭环 | ✅ | ✅ | ✅ | ✅ | ⏳ | 107 pytest；规范文档 id=6 入库且 sources API 可见 |
| 4 | QA + Leader + 一次总确认 | ✅ | ✅ | ✅ | 🔄 ⬅️ | ⏳ | **当前位置**：等一次总确认 |

## 📍 当前位置

```
Batch 108 — capture 去重误判修复 + 规范导入闭环（完成，等一次总确认）
├── ✅ 根因：KNOWLEDGE_INGEST_ENABLED=false + API 混义 + hooks 失败翻转
├── ✅ 修复：CaptureIngestResult 类型化 + 路由 503/409/500/200 + hooks 容错 + env 开关
├── ✅ 闭环：规范文档入库生产知识中心（id=6，sources API total=6 可见）；107 pytest
└── 🔄 等一次总确认（push + Draft PR + required checks 后合入）
```

## 📜 批次记录

### Batch 108 — capture 修复 + 导入闭环 (2026-08-06)
- **产出**: 根因定位 + 类型化修复 + 路由映射 + 配置 + 单测 6 条 + 规范导入闭环 + QA/Leader
- **审批**: Leader APPROVED（待用户一次总确认）
- **耗时**: 0.5d
- **记录**: C107-1/C102-2(capture) 关闭；C108-1（Railway env 复验）登记

## ⚠️ 阻塞与风险

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| Railway 环境变量 | P2 | KNOWLEDGE_INGEST_ENABLED=true 需在 Railway 控制台设置（人工步骤，同 C106-1 模式） | 用户/运维 | 2026-08-06 |

## 🔗 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD | [batch-108-capture-dedup-import-prd-summary.md](../batch-108-capture-dedup-import-prd-summary.md) | ✅ |
| PM 计划 | [batch-108-capture-dedup-import-pm-plan.md](../batch-108-capture-dedup-import-pm-plan.md) | ✅ |
| 设计规范 | [batch-108-capture-dedup-import-design-spec.md](../batch-108-capture-dedup-import-design-spec.md) | ✅ |
| QA 报告 | [batch-108-capture-dedup-import-qa-report.md](../batch-108-capture-dedup-import-qa-report.md) | ⏳ |
