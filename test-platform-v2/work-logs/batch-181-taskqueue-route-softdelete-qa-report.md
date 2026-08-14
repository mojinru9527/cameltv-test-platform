# Batch 181 — QA 报告：TaskQueue 统一 / 软删统一 / 路由拆分

> **mode: full** | 执行：DeepSeek_Harness（direct）| 日期：2026-08-16
> 范围：FIX-173-P2-06 / P2-08 / P2-10（架构专项批次）
> 分支：`feature/batch-181-taskqueue-route-softdelete`（基 51e5441，4 个 commit）

## 0. 结论

- ✅ **P2-06 TaskQueue 六队列统一**：交付完成（§1）
- ✅ **P2-08 软删三套语义统一**：交付完成（§2）
- ✅ **P2-10 路由大文件拆分 + 路由层禁 ORM**：交付完成（§3）
- 全量回归（子模块初始化后）：**1495 passed / 0 failed / 3 skipped**（基线 1459 passed / 6 failed；+36 净增测试，-6 环境失败，**本批新增失败 0**）

## 1. P2-06 验收证据

| 验收点 | 证据 |
|--------|------|
| 统一原语落地 | `app/core/task_queue.py`：QueueSpec / atomic_claim / atomic_claim_by_id / reap_stale / finish_task / QueueWorkerLoop |
| 六队列接入 | api_task_worker、ai_tasks、dsh_task_service、lanhu_evidence/worker、knowledge/agent_queue、playwright_executor(_claim_pending_run) + task_worker(reap_stale_ui_runs) |
| Agent TOCTOU 消除 | `agent_queue._process_queue_once` 改 atomic_claim_by_id（条件 UPDATE + rowcount，多副本安全） |
| 锁列补齐 | 迁移 `20260816_b181_task_queue_locks`：ai_task.locked_by、dsh_task.locked_at/locked_by、agent_queue_item.locked_at/locked_by、ui_test_run.locked_at/locked_by、lanhu_evidence_job.locked_by（缺表/缺列容忍，幂等） |
| 失联回收 6/6 | AI/DSH/Agent/UI 补齐（API/证据包已有）；阈值 300s（AI/DSH）~30min（API/Agent/UI），证据包沿用 heartbeat 活性 |
| 队列测试 | `tests/test_task_queue.py` 16 例（并发原子性/stale 重认领/回收/解锁/循环生命周期/Agent 集成/UI reap）+ 存量队列测试全绿 |
| 命令与退出码 | `pytest tests/test_task_queue.py test_ai_tasks.py test_api_task_worker.py test_dsh_tasks.py test_lanhu_evidence_worker.py test_task_worker.py test_playwright_executor.py test_continuous_learning.py test_agent_queue_locking.py test_agent_permissions.py -q` → **100+16=116 passed, exit 0** |

## 2. P2-08 验收证据

| 验收点 | 证据 |
|--------|------|
| 迁移+回填 | `20260816_b181_soft_delete_unify`：knowledge_source/chunk 新增 is_deleted，deprecated/superseded 幂等回填；downgrade 可执行 |
| 调用点转换 | source_service（默认过滤/衰减/废弃）、change_detector、snapshot_service、entity_service、regression_predictor、skill_service、vectorize、contract_extractor、knowledge 路由 8 处 |
| `== False` 清零 | `test_soft_delete_unify::TestStyleUnified` 静态断言（全 app 无 `is_deleted == False`）+ grep 复核（仅剩文档字符串 1 处） |
| 行为保持 | 检索不按 is_deleted 过滤（与旧全状态检索一致）；status 保留 UI 展示值（前端徽标不回归）；显式 status 筛选管理视图可用 |
| 测试 | `tests/test_soft_delete_unify.py` 9 例 + `test_knowledge.py` 79 例全绿（2 例按新语义更新断言） |

## 3. P2-10 验收证据

| 验收点 | 证据 |
|--------|------|
| 9 文件拆分 | 9 旧文件删除 → 25 新路由文件（knowledge×3/requirement×4/requirement_modules×4/wiki×4/apitest×3/test_case×3/release_bundles×2/lanhu_evidence×3/test_plan×2） |
| 路径零漂移 | `tests/test_route_inventory.py`：OpenAPI (path, method) 420 条与拆分前基线完全一致 |
| ORM 禁入 | `tests/test_route_layer_orm_ban.py` 4/4：9 域拆分文件 0 模型 import / 0 select( / 0 db.query(；SessionLocal 按 BackgroundTasks 豁免约定放行 |
| >20KB 清零 | `test_route_files_under_20kb` 通过（最大 knowledge_graph.py 19.9KB）；api/v1 56 文件全部 <20KB |
| ORM 收敛 | 新增 4 服务文件（release_bundle_service / requirement_module_service / lanhu_evidence/job_service / wiki/external_connection_service）+ 13 个既有服务补薄函数；knowledge 域直连 ORM（原 25 处）清零 |
| 契约 | 前后端无 schema 变更；OpenAPI 路径集不变 |

## 4. 拆分清单与回归

| 原文件 | 新文件 | 相关测试 | 退出码 |
|--------|--------|---------|--------|
| knowledge.py | knowledge_core/graph/artifacts.py | test_knowledge 79 | 0 |
| requirement.py | requirement_docs/ai/ai_generate/import.py | test_requirement 等 7 文件 73 | 0 |
| requirement_modules.py | requirement_modules_core/extract/interactions/links.py | 同上 | 0 |
| wiki.py | wiki_core/diff/external/sync.py | wiki 全组 164 | 0 |
| apitest.py | apitest_assets/cases/tasks.py | 同上 + 共享服务 95 | 0 |
| test_case.py | test_case_crud/taxonomy/files.py | test_testcase/test_testplan 72 | 0 |
| release_bundles.py | release_bundles_core/diff.py | release 相关 53 | 0 |
| lanhu_evidence.py | lanhu_evidence_jobs/assets/review.py | lanhu 全组 53 | 0 |
| test_plan.py | test_plan_crud/execution.py | plan 相关 24 | 0 |

## 5. 硬门禁与基线

- **全量 pytest（子模块已 init）**：`1495 passed / 0 failed / 3 skipped`（exit 0）
- **ruff F821**：`ruff check app/ --select F821` → All checks passed（exit 0）
- **Alembic**：单头 `20260816_b181_soft_delete_unify`；upgrade→downgrade→upgrade 循环通过
- **scan-common-bugs**：HARD=3 全部为**既有基线**（main.py:87、lanhu_provider.py:287/301，非本批文件）→ 豁免记录（C76-2）
- **audit-cconditions**：6 硬错为**既有孤儿**（C120-2/C163-1/C167-2/C168-1/C168-2/G1-G5 均已在 Closed 表）→ 本批未新增条件，合入前复核
- **基线失败对照**：原 6 失败（lanhu 子模块 ×5 + 迁移 ×1）→ 子模块初始化后全部通过；迁移测试本批修复后通过
- 已知环境项：本地 worktree 无 lanhu-mcp 子模块时会失败 5 项（CI 干净检出自动 init，不受影响）

## 6. 交付物

- 代码 commit：`81b496a`（P2-06）、`1f41ae0`（P2-08）、`85c2286`（守卫基线）、`348f023`（P2-10 集成）
- 文档：ADR-0019、backend/CLAUDE.md 三项约定、看板、本报告、Leader 判决

## 7. 复盘卡

| 字段 | 内容 |
|------|------|
| 计划耗时 | ~24h（计划）vs ~10h（实际） |
| 缺陷 | P0:0 / P1:0 / P2:3（子代理引入 confirm_prod 缺失、uuid 导入缺失、守卫路径 bug——均集成期修复）/ P3:1（设计调整：status 保留展示值） |
| 返工次数 | 3（迁移 helper 列反射、队列测试夹具、路由引用点 ×12） |
| 根因分类 | 工具链（子代理代码质量）/ 技术债 |
| 下次避免 | 路由拆分委托子代理后必须全量 pytest + 逐引用点核对；守卫测试先落地防路径漂移 |
