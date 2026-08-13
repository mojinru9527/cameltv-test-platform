# DEV Kanban — batch-167-version-coverage-pipeline

## 架构决策
- 后端: 新 `version_coverage_service`（只读聚合）、`requirement_source_service`（URL 适配）；覆盖/接口/UI 均走既有 service 分层。
- DB: 一次 Alembic 迁移（三张表加列，无新表）。
- 前端: BundleDetail 加覆盖面板与接入配置；AiResultModal 加质量徽标/接口生成按钮；PlanDetail 加 auto_ui。

## 任务与切片
| # | Slice | 状态 | 提交 |
|---|-------|------|------|
| 1 | 工件 PRD/PM/Design | done | — |
| 2 | Task1 Schema 迁移 + 模型/schema | todo | — |
| 3 | Task2 覆盖矩阵 API + 单测 | todo | — |
| 4 | Task3 需求源适配 + 分块提取 + meta | todo | — |
| 5 | Task4 接口端点绑定生成 + 单测 | todo | — |
| 6 | Task5 UI 变体 + 计划三类关联 + 单测 | todo | — |
| 7 | Task6 auto_ui 执行 + 单测 | todo | — |
| 8 | Task7 前端接入 + vitest | todo | — |
| 9 | QA 硬门禁 + QA/Leader 工件 | todo | — |
| 10 | 总确认 → push → Draft PR → 合入 | todo | — |

## 当前位置
Slice 3（覆盖矩阵）。
