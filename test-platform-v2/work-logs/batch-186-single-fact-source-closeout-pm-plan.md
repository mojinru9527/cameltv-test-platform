# Batch 186 — PM 计划：遗留收口（C182-1 单一事实源 / C182-2 回填验证 / C184-1 沙箱评估）

> 配套 PRD/Design：`batch-186-single-fact-source-closeout-{prd-summary,design-spec}.md`
> mode: full（重构 C182-1 + 交付物 C182-2/C184-1）

## 任务清单

| # | 任务 | 验收标准 | 执行 |
|---|------|---------|------|
| T0 | 工件 PRD/PM/Design/看板 | 四件落库、mode:full、C 条件引用齐 | 主代理 ✅ |
| T1 | C182-1 移除双写：`test_plan_service` 不再创建 api_execution_task/items（execute_all + auto_execute） | 计划执行仅落 test_execution；无 trigger_type=plan 新行、无 api_task_id 互指；历史任务可读 | 主代理 ✅ |
| T2 | C182-1 测试：`test_single_fact_source.py`（4 例）+ 更新 `test_batch169_plan_async` | 计划执行/自动执行/历史可读/手动任务四场景全绿 | 主代理 ✅ |
| T3 | C182-2 脚本可测化重构（collect_changed/apply_changes 助手 + `:memory:`/Windows 绝对路径处理） | 脚本行为不变（dry-run 输出逐字对齐） | 主代理 ✅ |
| T4 | C182-2 单测（映射规则/聚合/apply/幂等/load_database_url 共 30 例）+ 本地 dry-run/apply/幂等三阶段证据 | 30 例绿 + `work-logs/evidence/batch-186/backfill-domain-b182-dryrun.txt` | 主代理 ✅ |
| T5 | C182-2 生产执行手册（脚本 docstring） | 备份/dry-run 核对/apply/复核/回滚六步齐 | 主代理 ✅ |
| T6 | C184-1 ADR-0020（OS 级沙箱部署层评估）+ ADR README 索引 | 结论=现状不引入、自托管裸机触发条件明确 | 主代理 ✅ |
| T7 | C-CONDITIONS 更新：C182-1/C184-1 Closed、C182-2 Deferred（解除条件=生产窗口） | audit-cconditions 0 硬错 | 主代理 |
| T8 | 全量回归 + 门禁：backend pytest 全量、ruff F821 | 无新增失败 | 主代理 |
| T9 | QA/Leader 工件 + kanban | 六件齐备 | 主代理 |
| T10 | 总确认 → push → Draft PR → audit（-RequireSuccessfulChecks）→ 合入 | required checks 全绿 | 主代理 |

## 风险提示

- C182-1 移除双写：仅停止**新建** plan 任务；接口任务页历史数据走存量；手动/retry_failed 路径零改动。
- 聚合口径：statistics/report 早已以 test_execution 为口径（batch-175），无读方依赖 trigger_type=plan。
- C182-2 生产 apply：外部人工步骤，条件转 Deferred；脚本幂等，重复执行无副作用。
- C184-1：纯评估结论，无代码变更；触发条件登记防静默敞口。
