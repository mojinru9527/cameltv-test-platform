# Batch 181 — PM 计划：TaskQueue 统一 / 软删统一 / 路由拆分

> 配套 PRD / Design：`batch-181-taskqueue-route-softdelete-{prd-summary,design-spec}.md`
> 全部任务 30–60 分钟粒度，按切片串行推进；每切片完成即本地提交（worktree-reset-hazard 策略）。

## 任务清单

| # | 任务 | 验收标准 | 涉及文件 | 参考 |
|---|------|---------|---------|------|
| T0 | 工件：PRD/PM/Design/看板 | 四件落库、mode:full | work-logs/* | pipeline-modes.md |
| T1 | `app/core/task_queue.py` 基类（QueueSpec/atomic_claim/reap_stale/finish_task/QueueWorkerLoop） | 单测 4+ 通过；SQLite 原子性验证 | core/task_queue.py、tests/test_task_queue.py | Design §1.2-1.4 |
| T2 | 迁移 `b181_task_queue_locks`：5 表锁列 | alembic upgrade/downgrade 通过、单头 | alembic/versions/*、models/* | Design §1.6 |
| T3 | 六队列接入基类（API/AI/DSH/证据包/Agent/UI） | 各队列认领-执行-终态集成测试通过；Agent TOCTOU 消除 | api_task_worker / ai_tasks / dsh_task_service / lanhu_evidence/worker / agent_queue / playwright_executor / task_worker | Design §1.5 |
| T4 | 迁移 `b181_soft_delete_unify`：knowledge 两表 is_deleted + 回填 | 幂等回填、downgrade 通过 | alembic/versions/*、models/knowledge.py | Design §2.2 |
| T5 | 软删调用点转换（§2.3 全表）+ `== False` 清零 | test_soft_delete_unify 通过；grep 断言清零 | source_service / knowledge 路由 / change_detector / snapshot_service / test_case_service / test_case_graph_sync / test_case_linker | Design §2.3 |
| T6 | 路由守卫：`test_route_inventory.py` 路径集基线 + `test_route_layer_orm_ban.py` 骨架 | 基线生成；守卫对 knowledge 域生效 | tests/* | Design §3.1/3.4 |
| T7 | knowledge.py 拆分（3 文件）+ ORM 全量收敛 | 域测试通过；knowledge 域模型 import 清零；路径集不变 | api/v1/knowledge_*.py、services/knowledge/* | Design §3.2/3.3 |
| T8 | requirement.py 拆分（3 文件）+ ORM 收敛 | 需求域测试通过 | api/v1/requirement_*.py | Design §3.2 |
| T9 | requirement_modules.py 拆分（3 文件）+ ORM 收敛 | 模块树域测试通过 | api/v1/requirement_modules_*.py | Design §3.2 |
| T10 | wiki.py 拆分（4 文件）+ ORM 收敛 | wiki 域测试通过 | api/v1/wiki_*.py | Design §3.2 |
| T11 | apitest.py 拆分（3 文件）+ ORM 收敛 | 接口测试域测试通过 | api/v1/apitest_*.py | Design §3.2 |
| T12 | test_case.py 拆分（3 文件）+ ORM 收敛 | 用例域测试通过 | api/v1/test_case_*.py | Design §3.2 |
| T13 | release_bundles.py 拆分（2 文件）+ ORM 收敛 | 发布包域测试通过 | api/v1/release_bundles_*.py | Design §3.2 |
| T14 | lanhu_evidence.py 拆分（3 文件）+ ORM 收敛 | 蓝湖域测试通过 | api/v1/lanhu_evidence_*.py | Design §3.2 |
| T15 | test_plan.py 拆分（2 文件）+ ORM 收敛 | 计划域测试通过 | api/v1/test_plan_*.py | Design §3.2 |
| T16 | 全量回归 + 硬门禁 | pytest 全绿/无新增失败；ruff F821；alembic 单头；OpenAPI 路径集相等 | — | AGENTS.md §3 |
| T17 | QA 报告 + 证据 + scan-common-bugs + audit-cconditions | 工件齐全；HARD=0 | work-logs/* | SKILL.md QA |
| T18 | Leader 判决 + 总确认 → push → Draft PR → audit → 合入 | audit 通过、required checks 全绿 | — | SKILL.md Git 工作流 |

## 风险提示

- T7-T15 机械拆分量大：每个文件拆分后**必须**跑该域测试 + OpenAPI 路径比对，防漂移。
- T3 触及生产执行链：认领语义逐项对照 batch-174 基准，禁止行为回归。
- 全部代码写入 worktree（C104-5 已核对）。
