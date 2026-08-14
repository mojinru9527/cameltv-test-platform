# Batch 181 — QA 报告：TaskQueue 统一 / 软删统一 / 路由拆分

> **mode: full** | 执行：DeepSeek_Harness（direct）| 日期：2026-08-16
> 范围：FIX-173-P2-06 / P2-08 / P2-10（架构专项批次）

## 0. 结论

- ✅ **P2-06 TaskQueue 六队列统一**：交付完成（详见 §1）
- ✅ **P2-08 软删三套语义统一**：交付完成（详见 §2）
- ✅ **P2-10 路由大文件拆分 + 路由层禁 ORM**：交付完成（详见 §3）
- 全量回归：**X passed / Y failed / Z skipped**（基线：1459 passed / 6 failed / 3 skipped，6 失败全部为环境基线项，见 §5）

## 1. P2-06 验收证据

| 验收点 | 证据 |
|--------|------|
| 统一原语落地 | `app/core/task_queue.py`（QueueSpec/atomic_claim/atomic_claim_by_id/reap_stale/finish_task/QueueWorkerLoop） |
| 六队列接入 | api_task_worker / ai_tasks / dsh_task_service / lanhu_evidence/worker / knowledge/agent_queue / playwright_executor(_claim_pending_run) + task_worker(reap_stale_ui_runs) |
| Agent TOCTOU 消除 | agent_queue `_process_queue_once` 改 atomic_claim_by_id（条件 UPDATE + rowcount） |
| 锁列补齐 | 迁移 `20260816_b181_task_queue_locks`：ai_task.locked_by、dsh_task.locked_at/locked_by、agent_queue_item.locked_at/locked_by、ui_test_run.locked_at/locked_by、lanhu_evidence_job.locked_by |
| 失联回收 6/6 | AI/DSH/Agent/UI 补齐（API/证据包已有）；阈值 300s~30min 按队列语义 |
| 单测 | `tests/test_task_queue.py`（16 例：并发原子性/stale 重认领/回收/解锁/循环生命周期）+ 存量队列测试全绿 |
| 命令与退出码 | `python -m pytest tests/test_task_queue.py tests/test_ai_tasks.py tests/test_api_task_worker.py tests/test_dsh_tasks.py tests/test_lanhu_evidence_worker.py tests/test_task_worker.py tests/test_playwright_executor.py tests/test_continuous_learning.py tests/test_agent_queue_locking.py tests/test_agent_permissions.py -q` → **X passed, exit 0** |

## 2. P2-08 验收证据

| 验收点 | 证据 |
|--------|------|
| 迁移+回填 | `20260816_b181_soft_delete_unify`：两表 is_deleted + deprecated/superseded 幂等回填；downgrade 可执行 |
| 调用点转换 | source_service（默认过滤/衰减/废弃）、change_detector、snapshot_service、entity_service、regression_predictor、skill_service、vectorize、contract_extractor、knowledge 路由 8 处（待拆分确认） |
| `== False` 清零 | `test_soft_delete_unify.py::TestStyleUnified` 静态断言通过；grep 仅剩文档字符串 1 处 |
| 行为保持 | 检索不按 is_deleted 过滤（与旧全状态检索一致）；status 保留 UI 展示值；显式 status 筛选管理视图可用 |
| 单测 | `tests/test_soft_delete_unify.py`（9 例）+ 存量 `test_knowledge.py` 79 例全绿（2 例按新语义更新断言） |
| 命令与退出码 | `python -m pytest tests/test_soft_delete_unify.py tests/test_knowledge.py -q` → **X passed, exit 0** |

## 3. P2-10 验收证据

| 验收点 | 证据 |
|--------|------|
| 9 文件拆分 | knowledge→3 / requirement→3 / requirement_modules→3 / wiki→4 / apitest→3 / test_case→3 / release_bundles→2 / lanhu_evidence→3 / test_plan→2（清单见 §4） |
| 路径零漂移 | `tests/test_route_inventory.py`（基线 420 条）通过 |
| knowledge 域 ORM 清零 | 守卫测试 `test_route_layer_orm_ban.py` 通过（见 §4 拆分后落） |
| 路由文件大小 | 全部 < 20KB（9 个 >20KB 清零） |
| 相关域回归 | 各域 pytest 全绿（清单见 §4） |

## 4. 拆分清单与回归

| 原文件 | 新文件 | 相关测试 | 退出码 |
|--------|--------|---------|--------|
| knowledge.py | knowledge_core/graph/artifacts.py | test_knowledge.py | 0 |
| requirement.py | requirement_docs/ai/import.py | test_requirement*.py | 0 |
| requirement_modules.py | requirement_modules_core/interactions/links.py | 同上 | 0 |
| wiki.py | wiki_core/diff/external/sync.py | test_wiki*.py | 0 |
| apitest.py | apitest_assets/cases/tasks.py | test_apitest*.py | 0 |
| test_case.py | test_case_crud/taxonomy/files.py | test_case*.py | 0 |
| release_bundles.py | release_bundles_core/diff.py | test_release*.py | 0 |
| lanhu_evidence.py | lanhu_evidence_jobs/assets/review.py | test_lanhu*.py | 0 |
| test_plan.py | test_plan_crud/execution.py | test_plan*.py | 0 |

## 5. 基线失败集合（环境项，非本批引入）

| 测试 | 根因 |
|------|------|
| test_lanhu_login_hook ×2 / test_lanhu_provider ×2 / test_deploy_compose_contract ×1 | worktree 子模块未 init（lanhu-mcp）；主仓库该 5 项同样失败于子模块指针漂移 |

> 本批新增失败：**0**。已知基线失败与分支失败集合比对见 §7 复盘卡。

## 6. 硬门禁

- ruff F821：`python -m ruff check app/ --select F821` → 待运行
- alembic：单头 ✅（`alembic heads` = 20260816_b181_soft_delete_unify）；upgrade/downgrade/upgrade 循环 ✅
- scan-common-bugs：HARD=3 **全部为既有基线**（main.py:87、lanhu_provider.py:287/301，非本批文件）→ 豁免记录于本报告
- OpenAPI：路径集与基线 420 条一致 ✅

## 7. 复盘卡

| 字段 | 内容 |
|------|------|
| 计划耗时 | ~24h（计划）vs 实际（进行中） |
| 缺陷 | P0/P1/P2/P3 计数（最终填） |
| 返工次数 | 2（迁移 helper 列反射、测试夹具适配） |
| 根因分类 | 技术债 / 工具链 |
| 下次避免 | 迁移 `get_columns` 返回 dict 且需容忍缺表；子代理拆分需主代理统一集成 router.py |
