# Batch 181 — Design Spec：TaskQueue 统一 / 软删统一 / 路由拆分

> 配套 PRD：`batch-181-taskqueue-route-softdelete-prd-summary.md`。本文件为可执行的技术契约，含文件:行号锚点。

---

## 1. P2-06 TaskQueue 统一（`app/core/task_queue.py` 新增）

### 1.1 目标形状

六队列共用一套「原子认领 / 失联回收 / 解锁收尾」原语 + 线程循环助手。**各队列的状态词表与 execute 处理器保持域内原样**（P1-06 状态枚举统一不在本批）。

```
app/core/task_queue.py
├── @dataclass QueueSpec        # 队列契约：模型/列名/状态值/锁列/排序
├── atomic_claim(db, spec, *, worker_id, stale_seconds, extra_where=None) -> row|None
├── reap_stale(db, spec, *, stale_seconds, failed_value, error_message) -> int
├── finish_task(db, row, spec, *, status, **extra) -> None   # 置终态+解锁
└── class QueueWorkerLoop       # name/poll_interval/on_tick；start/kick/shutdown 幂等
```

### 1.2 `QueueSpec` 字段（全部有默认值）

| 字段 | 默认 | 说明 |
|------|------|------|
| `model` | 必填 | ORM 模型 |
| `id_col` | `"id"` | 主键列 |
| `status_col` | `"status"` | 状态列 |
| `pending` / `running` / `failed` | `"pending"/"running"/"failed"` | 词表值 |
| `lock_by_col` | `"locked_by"` | 持锁者 |
| `lock_at_col` | `"locked_at"` | 持锁时间（活性信号默认源） |
| `liveness_col` | `None` → 回落 `lock_at_col` | stale 判定列；证据包传 `"heartbeat_at"` |
| `order_col` / `order_asc` | `"id"` / True | 认领顺序；Agent 队列传 priority 组合 |
| `extra_order` | `None` | `(col, desc_bool)` 列表，追加在 order_col 后 |

### 1.3 `atomic_claim` 算法（SQLite/PG 通用，消除 TOCTOU）

```
1. reap_stale(db, spec)                    # 先回收失联 running
2. candidate = SELECT id FROM model
      WHERE status=pending [AND extra_where]
      ORDER BY [extra_order,] order_col LIMIT 1
3. updated = UPDATE model SET status=running, lock_by_col=worker_id,
      lock_at_col=now, started_at=COALESCE(started_at, now)
      WHERE id=candidate AND status=pending     # 条件 UPDATE
4. db.commit(); rowcount==0 → 返回 None（被并发方抢走）
5. db.refresh 后返回
```

> 与 batch-174 的 API 实现（skip_locked）等价且更可移植：条件 UPDATE + rowcount 在 SQLite 单写者与 PG 多副本下都原子。`api_task_worker` 一并切换到此原语（原 skip_locked 分支删除）。

### 1.4 `reap_stale` 算法

```
UPDATE model SET status=failed, lock_by_col='', finished_at=now,
   error_message='stale: 执行器失联超过 N 秒，已回收（Batch 181）'
WHERE status=running AND liveness_col < now - stale_seconds
```

- 证据包：`liveness_col="heartbeat_at"`，但保留其 `recover_stale_jobs` 的 COALESCE 回落（heartbeat→started→updated→created）兼容历史行 → **证据包保留原 recover 函数，认领切到 atomic_claim**。
- Agent 队列：新增周期 reap（`_queue_loop` 每次迭代调用）。
- UI run：`reap_stale_ui_runs` 挂到 `task_worker.poll_and_execute` 周期（阈值 30min，防误杀 300s 长任务）。

### 1.5 六队列接入矩阵

| 队列 | 文件 | 变更 |
|------|------|------|
| API | `services/api_task_worker.py` | claim 换 `atomic_claim`（保留 reap 前置）；`reap_stale_api_tasks` 改由 `reap_stale` 实现（locked_at 活性）；`_processor_loop` 换 `QueueWorkerLoop` |
| AI | `services/ai_tasks.py` | claim 换 `atomic_claim`（stale 300s，原 5min 改 300s 对齐 DSH 常量——设计统一 `_STALE_CLAIM_SECONDS=300`）；模型补 `locked_by`；loop 换 `QueueWorkerLoop`；`execute_task` 的解锁改用 `finish_task` |
| DSH | `services/dsh/dsh_task_service.py` | claim 换 `atomic_claim`（stale 300s）；模型补 `locked_at`+`locked_by`（原用 started_at 兼作锁 → 语义分离）；loop 换 `QueueWorkerLoop` |
| 证据包 | `services/lanhu_evidence/worker.py` | claim 换 `atomic_claim`（liveness=heartbeat_at，claim 时同时写 heartbeat_at+locked_by）；模型补 `locked_by`；`recover_stale_jobs` 保留 |
| Agent | `services/knowledge/agent_queue.py` | **修复 TOCTOU**：`_process_queue_once` 逐项改 `atomic_claim`（order=priority desc, id asc）；模型补 `locked_at`+`locked_by`；`_queue_loop` 补 `reap_stale` |
| UI run | `services/playwright_executor.py` | `_claim_pending_run` 改 `atomic_claim`（仅认领，不触状态机）；模型补 `locked_at`+`locked_by`；`task_worker.py` 补 `reap_stale_ui_runs` |

### 1.6 模型迁移（一张 Alembic revision：`20260816_b181_task_queue_locks`）

| 表 | 新增列 | 默认 |
|----|--------|------|
| `ai_task` | `locked_by` | `String(64), default ""` |
| `dsh_task` | `locked_at`(DateTime nullable)、`locked_by` | — / `""` |
| `agent_queue_item` | `locked_at`、`locked_by` | — / `""` |
| `ui_test_run` | `locked_at`、`locked_by` | — / `""` |
| `lanhu_evidence_job` | `locked_by` | `""` |

> `api_execution_task` 已有 locked_by/locked_at，不动。全部列 nullable 或带 default，**不设 NOT NULL**（兼容存量行）。server_default 按 SQLite/PG 双方言兼容写法（`sa.text("''")`）。

### 1.7 测试（`tests/test_task_queue.py` 新增）

1. `atomic_claim` 并发原子性：两 Session 同时认领同一任务，恰一个成功（SQLite 下串行验证 rowcount 语义）
2. stale 重认领：running + 锁超时 → 可被再次认领
3. `reap_stale`：超时 running → failed + 解锁；未超时不误伤
4. `finish_task`：置终态并清锁
5. 每队列集成：ai_tasks / dsh / agent_queue / lanhu worker / playwright claim / api_task_worker 的认领-执行-终态链路（复用现有 fixtures）
6. 双 404 约定（C86-1）仅约束路由测试，本批新增为服务级测试不涉及

---

## 2. P2-08 软删语义统一

### 2.1 约定（写入 `backend/CLAUDE.md`）

> **删除语义唯一约定**：需要「可恢复/默认隐藏」的删除一律用 `is_deleted` 布尔（True=已删）；业务硬删（需求/缺陷/计划/UI 任务/数据集/环境等）为显式审计删除，保留审计留痕，不建软删列。禁止再引入第三套删除语义（如 status=deprecated 兼作删除）。

### 2.2 模型迁移（`20260816_b181_soft_delete_unify`）

| 表 | 新增列 | 数据回填 |
|----|--------|----------|
| `knowledge_source` | `is_deleted` Boolean server_default 0 | `UPDATE knowledge_source SET is_deleted=1 WHERE status IN ('deprecated','superseded')` |
| `knowledge_chunk` | `is_deleted` Boolean server_default 0 | `UPDATE knowledge_chunk SET is_deleted=1 WHERE status='deprecated'` |

- 回填必须**幂等**（条件限定存量值）；`alembic upgrade head` 后 `downgrade` 反向可执行（删列）。
- `status` 列保留（历史生命周期值展示），**新代码不再产生** `deprecated` 值。

### 2.3 调用点转换表（行为不变原则）

| 调用点（现状） | 现状 | 改后 |
|------|------|------|
| `knowledge.py:135` overview source_count | `status.notin_(("deprecated","superseded"))` | `is_deleted.is_(False)` |
| `knowledge.py:136,178` chunk/embedded 计数 | `status == "active"` | `is_deleted.is_(False)` |
| `knowledge.py:139` deprecated_sources 计数 | `status == "deprecated"` | `is_deleted.is_(True)`（语义名保留） |
| `knowledge.py:94` `_graph_extract_availability` | chunk `status=="active"` | `is_deleted.is_(False)` |
| `source_service.py:113-116` list_sources 默认过滤 | `status.notin_(...)` | `is_deleted.is_(False)`；显式 status 筛选语义保留（管理视图） |
| `source_service.py:217,228` 保鲜衰减 | `.values(status="deprecated")` | `.values(is_deleted=True, status="deprecated")`（status 保留作 UI 展示值，过滤语义走 is_deleted） |
| `source_service.py:252,256` deprecate_source | `status="deprecated"`（源+切片） | `is_deleted=True`（源+切片）+ status 保留展示值 |
| `change_detector.py:65` | `status.notin_(...)` | `is_deleted.is_(False)` |
| `snapshot_service.py:233` | `status.notin_(...)` | `is_deleted.is_(False)` |
| `search_service.py` | 不按 status 过滤（含 deprecated 全状态检索） | **不按 is_deleted 过滤（行为保持）** |
| chunk 检索/切片列表（`chunk_service` 等） | 核对 `status=="active"` 处 | `is_deleted.is_(False)`（实现时 grep 全量核对） |
| `test_case_service.py` `== False` ×10 | `is_deleted == False` | `.is_(False)` |
| `knowledge.py:691`、`test_case_graph_sync.py:64`、`test_case_linker.py:317` | `== False  # noqa: E712` | `.is_(False)`（knowledge.py 处随路由拆分迁入 service） |
| `api_case_generation_service.py:121` | `isinstance(value, bool) is False` | 非删除语义，**不动**（属类型判断） |

### 2.4 测试（`tests/test_soft_delete_unify.py` 新增 + 存量调整）

1. deprecate_source → 源与切片 is_deleted=True；list_sources 默认隐藏、显式 status 可查（存量测试断言迁移到 is_deleted 语义）
2. 保鲜衰减 → is_deleted=True
3. 概览计数与现状口径一致（source_count 排除已删、deprecated_sources=已删数）
4. 检索行为不变：已删切片在 search 中仍可召回（与现状全状态检索一致）
5. `grep == False` 静态断言：backend 内 `is_deleted == False` 清零

---

## 3. P2-10 路由拆分 + ORM 收敛

### 3.1 总则

- 每个原文件按域拆成 2–4 个新文件，各自 `APIRouter(prefix=原prefix, tags=[域标签])`；`router.py` 逐文件 `include_router`。
- **URL 路径与 HTTP 方法零变化**；OpenAPI tags 分组变化不影响契约。
- **拆分文件禁 ORM**：不 `from app.models import ...`、不出现 `select(`/`db.query(`/`SessionLocal(`（除 test_plan/defect/report 既有的 BackgroundTasks 独立会话——会话管理豁免，模型查询仍禁）；查询收敛进 services（新增薄函数，签名为 `(db, ...)`，沿用调用方会话，不改变 commit 归属）。
- 新增守卫测试 `tests/test_route_layer_orm_ban.py`：对拆分后 9 域全部文件断言无模型 import / select / db.query；对 api/v1 其余文件维护 allowlist（收敛进度随批次推进，本批不动 allowlist 内文件）。

### 3.2 拆分映射

| 原文件 | 新文件 | 端点分组 |
|--------|--------|----------|
| `knowledge.py` 1668 行 | `knowledge_core.py` | overview / search / search/health / reembed / sources list+detail+chunks / chunks/{id} / deprecate / verify / capture |
| | `knowledge_graph.py` | graph/extract、entities stats+list+detail、relations list+approve+reject、view、backfill-source、evolve、auto-build、module-associations、sync-test-cases、hierarchy、design-assets import+image |
| | `knowledge_artifacts.py` | ai-artifacts 全部、skills、iterations 全部、predict/regression-scope |
| `requirement.py` 1148 行 | `requirement_docs.py` | list / detail / upload / delete / coverage |
| | `requirement_ai.py` | extract / extraction / extraction-quality / extraction/confirm / generate / generate-api-from-endpoints / match-api / extract-async / generate-async / ai-task/{id} |
| | `requirement_import.py` | import / cases / 评审相关（:856-973 组） |
| `requirement_modules.py` 1149 行 | `requirement_modules_core.py` | 列表 / 详情 / bundle tree / children / extract / build-from-document / link-test-cases / test-summary / import-tree / production-diff |
| | `requirement_modules_interactions.py` | extract-interactions / interactions PUT / classify-global-nav / global-nav / suggest-configures / confirm-configures / extract-attachments |
| | `requirement_modules_links.py` | admin-links GET+POST+DELETE |
| `wiki.py` 984 行 | `wiki_core.py` | config / import/lanhu / raw-sources / ingest-jobs / pages / search / approve / reject |
| | `wiki_diff.py` | diff/tasks 全部 / diff/items accept+reject+create-artifact |
| | `wiki_external.py` | external-connections 全部 / lint 全部 |
| | `wiki_sync.py` | sync/bundle coverage+diff+tree |
| `apitest.py` 977 行 | `apitest_assets.py` | 服务/端点 CRUD、import/confirm、curl、失败分析 |
| | `apitest_cases.py` | cases/generate、batch-generate |
| | `apitest_tasks.py` | tasks CRUD / cancel / retry / api-execute |
| `test_case.py` 710 行 | `test_case_crud.py` | 列表/详情/新建/更新/删除/批量/单用例执行/评审/版本 |
| | `test_case_taxonomy.py` | domains CRUD / stats / taxonomy |
| | `test_case_files.py` | xmind/excel 导入导出 |
| `release_bundles.py` 592 行 | `release_bundles_core.py` | list/create/detail/update/delete/coverage/import-requirement/version-chain/regression-scope/trigger-regression |
| | `release_bundles_diff.py` | diff / diff/confirm |
| `lanhu_evidence.py` 558 行 | `lanhu_evidence_jobs.py` | 任务列表/详情/取消/重试/删除/cookie/login |
| | `lanhu_evidence_assets.py` | 页面/资产/OCR/导入 |
| | `lanhu_evidence_review.py` | 审核/批量审核 |
| `test_plan.py` 587 行 | `test_plan_crud.py` | 计划 CRUD + 计划内用例管理 |
| | `test_plan_execution.py` | execute-all / auto-execute / batch-execute / async / triage / 缺陷草稿 |

### 3.3 ORM 收敛落点（knowledge 域，全量）

| 现查询（knowledge.py） | 收敛到 |
|------|------|
| overview 统计（:131-203） | `source_service.get_knowledge_overview(db, pid)` 新增 |
| `_graph_extract_availability`（:87-100） | `chunk_service.has_active_chunks(db, pid, source_id)` 新增 |
| `_knowledge_domain_filter`（:103-117） | `entity_service.knowledge_domain_filter(...)` 新增（供 graph 各端点复用） |
| search/reembed（:211-312） | 已走 search_service / embedding_service，确认无直连 |
| graph 各查询（:676-1096） | entity_service / relation_service 新增薄函数 |
| design-assets（:1148-1251） | 现有 design 服务（实现时核对） |
| hierarchy（:1414-1646） | entity_service.get_project_sphere_view 新增 |
| 回归预测（:1652） | 现有 predict 服务（实现时核对） |
| sync-test-cases（:1098） | 迁移 `test_case_graph_sync`/`test_case_linker` 现成服务 |

### 3.4 验证

1. `tests/test_route_inventory.py` 新增：快照「路径+方法」全集（拆分前从 main 生成基线 JSON），拆分后逐文件断言集合相等（防路径漂移）
2. 每个拆分文件落地后：`python -c "from app.main import app"` 导入冒烟 + 该域相关 pytest + OpenAPI `/openapi.json` 路径计数对比
3. 前端契约：`npm run gen:api` 不执行（无 schema 漂移）；CI 的 api.d.ts 校验不在本批触发

---

## 4. 实施顺序（依赖关系）

1. S1 P2-06（独立：core 新文件 + 迁移 + 六队列 + 测试）
2. S2 P2-08（独立：迁移 + 转换 + 测试）
3. S3 route 拆分前：先落 `test_route_inventory.py` 基线 + 守卫测试骨架
4. S4-S9 逐文件拆分（knowledge → requirement → requirement_modules → wiki → apitest → test_case → release_bundles → lanhu_evidence → test_plan），每文件后跑相关测试
5. S10 全量回归 + 工件 + 合入门禁

## 5. 回滚策略

- 迁移均单头、幂等、可 downgrade；代码与迁移同批合入。
- 若拆分中任一步 OpenAPI 路径集合漂移 → 立即回退该文件拆分（git checkout 还原），修复后重做。
- TaskQueue 基类与各队列适配独立提交，可单独 revert。
