# Batch 186 — Design Spec：遗留收口（C182-1 单一事实源 / C182-2 回填验证 / C184-1 沙箱评估）

> 配套 PRD：`batch-186-single-fact-source-closeout-prd-summary.md`

## 1. C182-1 单一事实源：移除计划执行双写（`app/services/test_plan_service.py`）

### 1.1 现状

`auto_execute_api_cases` / `execute_all_cases` 两条计划执行路径：

1. 每条 API 用例写 `TestExecution`（计划执行事实）；
2. 同时调 `_ensure_plan_api_task`（按 plan 找/建 `ApiExecutionTask(trigger_type="plan")`）+
   `_register_plan_api_snapshot`（写 `ApiExecutionTaskItem`）——为「接口测试任务页」展示计划任务；
3. `TestExecution.api_task_id` 与 `item.test_execution_id` 双向互指。

**双写为纯冗余**：batch-175 已定统计/报告/追溯口径=test_execution；report_aggregator/statistics
均不读 trigger_type=plan 任务；唯一消费方是任务页列表（历史数据仍可展示）。

### 1.2 改后

- 删除 `_ensure_plan_api_task`、`_register_plan_api_snapshot` 两函数及其全部调用点；
- `execute_all_cases` / `auto_execute_api_cases` 只写 `TestExecution`；
- `TestExecution.api_task_id` 不再初始化（保持 NULL）；不再有批量提交后刷新 api_task 的代码；
- **不动**：`api_execution_task` / `item` 表结构与列（`test_execution.api_task_id`、
  `item.test_execution_id` 保留历史链接，仅不再写入）；手动批量任务/retry_failed 路径
  （`create_execution_task`）零改动；前端 TaskTab 零改动（存量数据继续展示）。

### 1.3 测试

`tests/test_single_fact_source.py`（新，4 例）：

| 用例 | 断言 |
|------|------|
| execute_all 仅落 test_execution | 3 条 API 用例 → TestExecution=1/plan_case；ApiExecutionTask(plan)=0；Item=0；api_task_id is None |
| auto_execute 仅落 test_execution | 2 条失败用例 → TestExecution=2；plan 任务/items=0 |
| 历史 plan 任务可读 | 预置 trigger_type=plan 任务+item → 查询仍返回（含 items） |
| 手动批量任务不受影响 | `create_execution_task(trigger_type="manual")` 正常创建 |

`tests/test_batch169_plan_async.py`：`test_execute_all_batch_commit_keeps_results_and_api_task`
改为断言 `trigger_type="plan"` 计数 == 0（不再断言快照存在）；测试名/文档字符串同步更新。

## 2. C182-2 回填脚本验证（`scripts/backfill-domain-naming-b182.py`）

### 2.1 可测化重构（行为不变）

- 抽出 `collect_changed(session) -> (total, distinct, [(src, dst, cnt)])`：只读聚合，
  dry-run 与 apply 共用同一口径（预览=实际写入）；
- 抽出 `apply_changes(session, changed) -> int`：逐映射 UPDATE（仅未软删行）+ commit；
- `main()` 收敛为「聚合 → 报告 → 可选写入」；sqlalchemy 导入保持函数内惰性（脚本可脱离
  backend 包路径直接导入）；
- `load_database_url` 补两个边界：`sqlite:///:memory:` 不解析路径；Windows 盘符绝对路径
  （`sqlite:///F:/...`）不解析路径（此前会被误当相对路径重写）。

### 2.2 单测（`tests/test_backfill_domain_naming_b182.py`，30 例）

- `normalize_domain` 规则 17 例参数化（裸域补前缀/平台前缀含变体保留/体育-运营后台保留/
  空值不修改/空白 strip）+ 幂等 1 例；
- `collect_changed`：映射与计数、软删排除、空库；
- `apply_changes`：写入+软删行保留+原值清零复核、幂等（二次 apply=0）、无变更短路；
- `load_database_url`：环境变量优先、.env 解析+相对路径绝对化、`:memory:`、Windows 绝对路径、
  缺失报错（SystemExit）。

### 2.3 本地 dry-run 证据

`work-logs/evidence/batch-186/backfill-domain-b182-dryrun.txt`：临时库（17 行：16 活动+1 软删，
含审查点名裸域/平台前缀/体育-运营后台/空值/已归一）三阶段 CLI 实跑——

1. dry-run：16 活动、7 映射 8 行（50%）、已知样本命中 7；
2. --apply：写 8 行、复核原裸域剩余 0；
3. 再 dry-run：0 变更（幂等）。

### 2.4 生产执行手册

脚本 docstring「生产执行手册」六步：备份 → 生产环境登录+确认 DATABASE_URL（凭据环境变量注入，
不落库）→ dry-run 逐条核对（仅裸域映射）→ --apply → 复核（剩余 0 + SQL 抽查）→ 回滚预案。

## 3. C184-1 OS 级沙箱评估（`docs/adr/0020-os-level-sandbox-deployment-assessment.md`）

- 隔离模型三层：L1 进程内（batch-184 已落地）/ L2 容器级（Railway 生产现状）/ L3 OS 级（未启用）；
- 决策：现状不引入 OS 级沙箱；**触发条件**=自托管裸机部署 DSH（无 L2）时，首选 bubblewrap、
  备选 nsjail，并登记新 C 条件；
- 弃选：容器内叠加 nsjail（收益不成比例）、手写 seccomp（维护责任）、双容器分离（低频任务
  架构复杂度）；
- ADR README 索引同步新增 0020 行。

## 4. 文档

- `C-CONDITIONS.md`：C182-1/C184-1 → Closed（附 commit + 测试/ADR 证据）、C182-2 → Deferred
  （解除条件=生产窗口人工 `--apply`）；最后更新日期同步 2026-08-16。
- ADR README 新增 0020 行；脚本 docstring 生产手册。
