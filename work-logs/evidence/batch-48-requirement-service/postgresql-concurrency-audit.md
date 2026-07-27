# Batch 48 真实 PostgreSQL 并发验收

## 环境与安全边界

- 数据库容器：Batch 48 专用 clone `codex-batch48-oldpg-final-20260727`。
- 独立数据库：`batch48_concurrency_20260727`。
- 原始数据卷：未启动、未挂载写入、未修改。
- Schema revision：`20260727_batch48_pg_parity`。
- 迁移后 `alembic check`：`No new upgrade operations detected.`
- 密码、连接串、Token：仅通过当前进程环境注入，未写入测试、日志、报告或 Git。

## B47-REQ-022 — 重复导入同一 `source_case_index`

执行方式：

- 4 个独立 SQLAlchemy Session / PostgreSQL 连接。
- 通过线程屏障同时调用生产 `requirement_service.import_cases`。
- 4 个事务导入同一 `project_id + source_doc_id + source_case_index`。
- 生产路径使用需求文档行级 `SELECT ... FOR UPDATE`，数据库同时保留唯一约束。

结果：

| 检查项 | 结果 |
|---|---|
| winner | 1 个：`imported=1, skipped=0, total=1` |
| loser | 3 个：`imported=0, skipped=1, total=1` |
| 最终 `test_case` 行数 | 1 |
| `requirement_document.imported_count` | 1 |
| `imported_func_count` | 1 |
| `imported_api_count` | 0 |
| `imported_func_indices` | 仅 `[0]` |
| 计数漂移 | 无 |

结论：loser 为幂等跳过，最终身份唯一，累计计数不漂移。

## B47-MOD-007 — 重复创建同一 `module_admin_link`

执行方式：

- 6 个并发 HTTP `POST /api/v1/requirement-modules/admin-links` 请求。
- 请求使用相同的 `project_id + client_module_id + admin_module_id + relation_type`。
- 每个 HTTP 请求由独立数据库 Session 处理。
- 生产路由同时具备应用层查重、数据库唯一约束和 `IntegrityError → HTTP 409` 映射。

结果：

| 检查项 | 结果 |
|---|---|
| winner | 1 个 HTTP 200 |
| loser | 5 个 HTTP 409，消息明确为关联已存在 |
| 最终 `module_admin_link` 行数 | 1 |
| 成功审计行数 | 1 |
| 计数漂移 | 无 |

结论：并发 loser 返回明确冲突，业务行与审计行均仅一条。

## 可复用自动化

测试文件：`test-platform-v2/backend/tests/test_batch48_postgresql_concurrency.py`

默认状态为跳过。仅同时配置以下环境变量时执行：

```text
BATCH48_RUN_PG_INTEGRATION=1
BATCH48_PG_INTEGRATION_URL=<一次性 PostgreSQL 数据库连接>
```

未配置时执行结果为 `2 skipped`；在专用 PostgreSQL 数据库显式开启后结果为 `2 passed`。

## 验收结论

- `B47-REQ-022`：PASS。
- `B47-MOD-007`：PASS。
- 本轮未发现新的生产并发缺陷。
