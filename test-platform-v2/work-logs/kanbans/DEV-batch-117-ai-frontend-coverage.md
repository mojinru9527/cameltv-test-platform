# 🗂️ Dev 部门项目看板 — Batch 117（AI 生成前端轮询闭环 + 覆盖缺口报告）

| 字段 | 值 |
|------|-----|
| **项目名称** | C116-2 前端 async 轮询 + C116-3 覆盖缺口报告 |
| **执行器** | codex（用户确认延续） |
| **分支** | feature/batch-117-ai-frontend-coverage |

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 覆盖缺口报告（C116-3） | ✅ | 🔄 | ⏳ | ⏳ | ⏳ | coverage_report.py |
| 2 | 前端 async 轮询（C116-2） | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | api + index/ReviewPage |
| 3 | QA/Leader + 一次总确认 | ✅ | ⏳ | ⏳ | 🔄 ⬅️ | ⏳ | **当前位置**：Task 1 编码中 |

```
Batch 117 — AI 生成前端轮询 + 覆盖缺口报告
├── ✅ PRD/PM/看板
├── 🔄 Task 1：coverage_report
├── ⏳ Task 2：前端 async 轮询
└── ⏳ QA → Leader → 一次总确认
```