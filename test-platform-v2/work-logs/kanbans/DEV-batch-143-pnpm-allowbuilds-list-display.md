# 🗂️ Dev 看板 — batch-143-pnpm-allowbuilds-list-display
> pnpm 构建配置修复 + 列表展示问题修复 | Codex 执行

## 项目信息
| 字段 | 值 |
|---|---|
| 关联 PRD | work-logs/batch-143-pnpm-allowbuilds-list-display-prd-summary.md |
| 执行器 | codex |
| 创建 | 2026-08-10 |

## 交付切片进度
| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 |
|---|-------|:--:|:--:|:--:|:--:|:--:|
| 1 | pnpm-workspace.yaml allowBuilds 修复 | ✅ | ✅ | ✅ | ✅ | ⏳ |
| 2 | 列表分页条数（domain 8→20、doc 10→20）+ 测试同步 | ✅ | ✅ | ✅ | ✅ | ⏳ |
| 3 | 关键截断单元格补 title（12 文件 20 处） | ✅ | ✅ | ✅ | ✅ | ⏳ |
| 4 | 全平台复扫 + QA/Leader 工件 | ✅ | ✅ | ✅ | ✅ | ⏳ |

## 批次记录
### Batch 143 (2026-08-10)
- **产出**: PRD-lite / QA 报告 / Leader 判决 / 13 个文件修复（pnpm-workspace.yaml + requirement/lanhu-evidence/DefectTable/dataset/environment/TaskTab/SourceListTab/EntityTab/perftest/project/report + RequirementPage.test）
- **审批**: Leader APPROVED；待用户一次总确认
- **耗时**: 计划 3h / 实际 3h
- **QA 证据**: pnpm install 无阻断；typecheck/build/vitest(444) 全绿
