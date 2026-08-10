# 🗂️ Dev 看板 — batch-142-ui-controls-dialog-sheet
> 全平台表单控件（v4→v3 变体修复）+ 弹窗/抽屉尺寸修复 | Codex 执行

## 项目信息
| 字段 | 值 |
|---|---|
| 关联 PRD | work-logs/batch-142-ui-controls-dialog-sheet-prd-summary.md |
| 执行器 | codex |
| 创建 | 2026-08-10 |

## 交付切片进度
| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 |
|---|-------|:--:|:--:|:--:|:--:|:--:|
| 1 | v4→v3 变体修复（15 个共享组件） | ✅ | ✅ | ✅ | ✅ | ⏳ |
| 2 | 弹窗/抽屉尺寸与滚动 + 命令面板崩溃修复 | ✅ | ✅ | ✅ | ✅ | ⏳ |
| 3 | QA 硬门禁 + 构建产物比对 + 浏览器验收 | ✅ | ✅ | ✅ | ✅ | ⏳ |
| 4 | Leader 判决 + 流程回写 | ✅ | ✅ | ✅ | ✅ | ⏳ |

## 批次记录
### Batch 142 (2026-08-10)
- **产出**: PRD-lite / QA 报告 / Leader 判决 / 21 个前端文件修复（switch、checkbox、select、dropdown-menu、command、button、badge、tabs、tooltip、card、avatar、input-group、popover、sidebar、calendar、dialog、sheet、LanhuEvidenceDialog、LanhuEvidenceJobDrawer、lanhu-evidence、PrototypePreview）
- **审批**: Leader APPROVED；待用户一次总确认（推送+PR+合入）
- **耗时**: 计划 4h / 实际 5h
- **QA 证据**: typecheck/build/vitest(444) 全绿；构建产物失效类全量 PRESENT；Playwright 浏览器验收通过
