# DEV Kanban — batch-167-version-coverage-pipeline

## 架构决策
- 后端: 新 `version_coverage_service`（只读聚合）、`requirement_source_service`（URL 适配）；覆盖/接口/UI 均走既有 service 分层。
- DB: 一次 Alembic 迁移（三张表加列，无新表）。
- 前端: BundleDetail 加覆盖面板与接入配置；AiResultModal 加质量徽标/接口生成按钮；PlanDetail 加 auto_ui。

## 任务与切片
| # | Slice | 状态 | 提交 |
|---|-------|------|------|
| 1 | 工件 PRD/PM/Design | done | — |
| 2 | Task1 Schema 迁移 + 模型/schema | done | b71b826 |
| 3 | Task2 覆盖矩阵 API + 单测 | done | e7cdbf6 |
| 4 | Task3 需求源适配 + 分块提取 + meta | done | 72054ee |
| 5 | Task4 接口端点绑定生成 + 单测 | done | fb36d01 |
| 6 | Task5 UI 变体 + 计划三类关联 + 单测 | done | 722a992 |
| 7 | Task6 auto_ui 执行 + 单测 | done | cfb12df |
| 8 | Task7 前端接入 + vitest | done | a470c60/6f22255 |
| 9 | QA 硬门禁 + QA/Leader 工件 | done | 6b12eb1 |
| 10 | 总确认 → push → Draft PR → 合入 | in-progress | — |

## 当前位置
全部 Slice 完成；待用户一次总确认后推送/PR/合入。

