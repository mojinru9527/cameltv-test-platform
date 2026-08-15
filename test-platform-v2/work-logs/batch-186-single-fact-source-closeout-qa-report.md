# Batch 186 — QA 报告：遗留收口（C182-1 单一事实源 / C182-2 回填验证 / C184-1 沙箱评估）

> **mode: full** | 执行：DeepSeek_Harness（direct）| 日期：2026-08-16
> 分支：`feature/batch-186-single-fact-source-closeout`

## 0. 结论

✅ **C182-1（P2）关闭**：计划执行移除双写，唯一事实源 = test_execution；历史 plan 任务保留可读；手动/retry_failed 路径零改动。
✅ **C182-2（P3）转 Deferred**：脚本 30 例单测 + 本地 dry-run→apply→幂等三阶段证据 + 生产执行手册已交付；生产 `--apply` 为人工运维步骤（凭据策略），解除条件=生产窗口。
✅ **C184-1（P3）关闭**：ADR-0020 评估成文（L1 进程内 / L2 Railway 容器 / L3 OS 级三层隔离模型；现状不引入 OS 级沙箱，自托管裸机部署触发重新评估）。

## 1. 验收证据

| 项 | 证据 |
|----|------|
| C182-1 移除双写 | `test_plan_service.py` 删除 `_ensure_plan_api_task`/`_register_plan_api_snapshot`（-143 行）；execute_all/auto_execute 仅写 TestExecution（commit b88a4b9） |
| C182-1 测试 | `test_single_fact_source.py` 4 例（execute_all/auto_execute 仅落 test_execution、历史 plan 任务可读、手动任务不受影响）；`test_batch169_plan_async` 断言 trigger_type=plan==0；`test_batch157_exec_link` 2 例改为新契约（无 plan 任务、api_task_id is None）——首轮全量 2 失败即此旧契约测试，更新后全绿 |
| C182-2 单测 | `test_backfill_domain_naming_b182.py` 30 例：normalize 规则 17 例参数化+幂等、collect 聚合/软删/空库、apply 写入/幂等/短路、load_database_url 5 例（env 优先/.env/相对路径绝对化/:memory:/Windows 绝对路径/缺失报错） |
| C182-2 本地证据 | `work-logs/evidence/batch-186/backfill-domain-b182-dryrun.txt`：临时库 17 行（16 活动+1 软删，含审查点名裸域）三阶段 CLI 实跑——dry-run 7 映射 8 行（50%）→ --apply 写 8 行、复核剩余 0 → 再 dry-run 0 变更（幂等）；软删行保持原值复核 ✅ |
| C182-2 生产手册 | 脚本 docstring「生产执行手册」六步（备份 → 生产环境+DATABASE_URL 核对 → dry-run 逐条核对 → --apply → 复核 SQL 抽查 → 回滚预案） |
| C184-1 ADR | `docs/adr/0020-os-level-sandbox-deployment-assessment.md` + ADR README 索引；结论=现状不引入、触发条件=自托管裸机、首选 bubblewrap/备选 nsjail |
| C-CONDITIONS | C182-1/C184-1 → Closed（commit b88a4b9）、C182-2 → Deferred（解除条件=生产窗口 `--apply`）；最后更新 2026-08-16 |

## 2. 硬门禁

| 门禁 | 结果 |
|------|------|
| 后端 pytest 全量 | **1578 passed / 0 failed / 3 skipped**（含子模块初始化后复跑；首轮 1576+2 旧契约失败 → 更新 batch-157 测试 → 复跑全绿） |
| ruff F821（app/） | All checks passed |
| ruff（本批新增/修改 5 文件） | 0 errors（含顺手清理既有 E501） |
| alembic | 单头 `20260816_b182_status_unify`；无新迁移 |
| audit-cconditions | 13 硬错 = **存量工具误报**（main HEAD d2ac7ea 已有 10 个同类：`~~C-xxx~~` 删除线关闭行的 ID 注册被 next-char 过滤误判孤儿；batch-182/184/185 均带同款合入）+ 本批 3 个同类（C182-1/2、C184-1）；无新错误类型；audit-ai-pr 不调用此工具 |

## 3. 复盘卡

| 字段 | 内容 |
|------|------|
| 计划耗时 | ~8h（计划）vs ~5h（实际） |
| 缺陷 | P0:0 / P1:0 / P2:0 / P3:2（测试自身：batch-157 旧契约断言未随单测更新暴露于全量；脚本测试首跑 1 例排序期望笔误） |
| 返工次数 | 2（batch-157 契约更新；证据文件编码重录） |
| 根因分类 | 契约演进不同步 / 工具链（Windows 管道编码） |
| 下次避免 | 双写行为变更时同步 grep 全仓旧断言（`trigger_type="plan"`、`api_task_id is not None`）；CLI 证据输出用 cmd 重定向+PYTHONIOENCODING 避免 PowerShell 管道乱码 |
