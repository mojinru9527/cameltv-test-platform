# 🗂️ Dev 部门项目看板 — Batch 124（需求/设计稿入库 + 图谱 P0 修复）

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | 需求/设计稿入库（批次 C，文本+图片完整）+ 图谱 P0 崩溃修复 |
| **关联 PRD** | [batch-124-requirement-design-ingestion-prd-summary.md](../batch-124-requirement-design-ingestion-prd-summary.md) |
| **看板创建** | 2026-08-08 |
| **执行器** | codex（用户已确认） |
| **Worktree** | F:\CamelTv-worktrees\codex-requirement-design-ingestion |

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 图谱 P0 崩溃修复（graph_view 去重 + 清理脚本 + 测试） | ✅ | ✅ | ✅ | 🔄 ⬅️ | ⏳ | dedup 测试 1/1；dedup-entities.py 登记 |
| 2 | 需求文档入库（用户端 98 页 + 运营后台 72 页，文本+图片完整） | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 输入源 backend/data/axure_extract_test/ |
| 3 | 设计稿图片入库（每页 images/ 完整，可预览） | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | |
| 4 | 生产导入 + 知识中心验证 + QA/Leader | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | |

## 📍 当前位置

```
Batch 124 — 需求/设计稿入库 + 图谱 P0
├── ✅ PRD 已提交；Slice 1 图谱去重修复完成（测试 1/1）
└── 🔄 下一步 Slice 2：需求文档入库（文本+图片完整）
```
