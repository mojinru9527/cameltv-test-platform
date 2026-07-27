# Batch 48 真实 PostgreSQL Alembic 漂移审计

## 审计边界

- 数据来源：`2026-07-14` 脱敏 PostgreSQL staging 数据卷的只读复制品。
- 原卷：未启动、未写入、未修改。
- 审计 clone：独立卷 `codex-batch48-oldpg-final-20260727`。
- 脱敏规则：仅记录表名、列名、类型、nullable/index 差异和行数；不记录连接串、密码、Cookie、Token 或业务字段值。
- 初始 revision：`20260714_lanhu_pg_reconcile`。
- 首次 Batch 48 升级后的 revision：`20260727_batch48`。

## 分类口径

- **A — Batch 48 需求服务相关**：需求文档、审查队列、API 匹配或测试用例追溯直接使用的 schema。
- **B — 其他历史迁移/模型契约遗漏**：非需求服务模块的历史迁移与当前 ORM metadata 不一致。
- **C — 旧环境预期额外对象**：数据库存在、但当前 metadata 未注册且 Alembic 建议删除的对象。

## 修复前完整差异清单

`alembic check` 共检出 **51** 项；其中 A 类 19 项、B 类 32 项、C 类 0 项。不存在 `remove_table`、`remove_column`、`remove_index` 或 `remove_constraint`。

| # | 类别 | 差异 |
|---:|:---:|---|
| 001 | A | `add_column api_endpoint.remark TEXT NOT NULL` |
| 002 | B | `modify_type av_check_measurement.created_at TIMESTAMP(timezone=True) → DateTime metadata` |
| 003 | B | `modify_type av_check_measurement.updated_at TIMESTAMP(timezone=True) → DateTime metadata` |
| 004 | B | `modify_nullable perf_device.device_id true → false` |
| 005 | B | `modify_nullable perf_device.device_name true → false` |
| 006 | B | `modify_nullable perf_device.device_model true → false` |
| 007 | B | `modify_nullable perf_device.platform true → false` |
| 008 | B | `modify_nullable perf_device.os_version true → false` |
| 009 | B | `modify_nullable perf_device.status true → false` |
| 010 | B | `modify_nullable perf_device.last_seen_at true → false` |
| 011 | B | `modify_nullable perf_device.created_at true → false` |
| 012 | B | `modify_nullable perf_metric.session_id true → false` |
| 013 | B | `modify_nullable perf_metric.timestamp true → false` |
| 014 | B | `modify_nullable perf_metric.elapsed_s true → false` |
| 015 | B | `modify_nullable perf_metric.metric_type true → false` |
| 016 | B | `modify_nullable perf_metric.data_json true → false` |
| 017 | B | `modify_nullable perf_session.project_id true → false` |
| 018 | B | `modify_nullable perf_session.session_id true → false` |
| 019 | B | `modify_nullable perf_session.device_id true → false` |
| 020 | B | `modify_nullable perf_session.device_name true → false` |
| 021 | B | `modify_nullable perf_session.device_model true → false` |
| 022 | B | `modify_nullable perf_session.platform true → false` |
| 023 | B | `modify_nullable perf_session.pkg_name true → false` |
| 024 | B | `modify_nullable perf_session.metrics true → false` |
| 025 | B | `modify_nullable perf_session.status true → false` |
| 026 | B | `modify_nullable perf_session.duration true → false` |
| 027 | B | `modify_nullable perf_session.actual_duration_s true → false` |
| 028 | B | `modify_nullable perf_session.summary_json true → false` |
| 029 | B | `modify_nullable perf_session.error_message true → false` |
| 030 | B | `modify_nullable perf_session.creator_id true → false` |
| 031 | B | `modify_nullable perf_session.created_at true → false` |
| 032 | B | `modify_nullable perf_session.updated_at true → false` |
| 033 | A | `add_column requirement_document.doc_id VARCHAR NOT NULL` |
| 034 | A | `add_column requirement_document.version VARCHAR NOT NULL` |
| 035 | A | `add_column requirement_document.parent_id INTEGER NULL` |
| 036 | A | `add_column requirement_document.diff_json VARCHAR NOT NULL` |
| 037 | A | `add_column requirement_document.diff_status VARCHAR NOT NULL` |
| 038 | A | `add_index requirement_document.ix_requirement_document_doc_id(doc_id)` |
| 039 | A | `add_index requirement_document.ix_requirement_document_parent_id(parent_id)` |
| 040 | A | `modify_nullable requirement_review.requirement_id true → false` |
| 041 | A | `modify_nullable requirement_review.case_index true → false` |
| 042 | A | `modify_nullable requirement_review.case_type true → false` |
| 043 | A | `modify_nullable requirement_review.status true → false` |
| 044 | A | `modify_type requirement_review.edited_data TEXT → VARCHAR metadata` |
| 045 | A | `modify_nullable requirement_review.edited_data true → false` |
| 046 | A | `modify_nullable requirement_review.reviewer_id true → false` |
| 047 | A | `add_column test_case.api_endpoint_id INTEGER NULL` |
| 048 | A | `add_column test_case.requirement_module_id INTEGER NULL` |
| 049 | A | `add_index test_case.ix_test_case_api_endpoint_id(api_endpoint_id)` |
| 050 | A | `add_index test_case.ix_test_case_requirement_module_id(requirement_module_id)` |
| 051 | B | `add_index wiki_review_item.ix_wiki_review_item_decision(decision)` |

## 收敛方式

新增 forward-only revision `20260727_batch48_pg_parity`：

1. 只新增遗漏列和索引，不删除或重命名任何数据库对象。
2. 对 `requirement_review`、`perf_device`、`perf_metric`、`perf_session` 收紧 `NOT NULL` 前，先查询目标列是否存在 NULL。
3. 如果存在 NULL，迁移抛出仅含表名、列名和数量的错误；在 PostgreSQL 上事务整体回滚，不会删除、覆盖或伪造历史数据。
4. `requirement_review.edited_data` ORM 类型改为 `Text`，保留数据库适合 JSON 文本的既有类型。
5. `av_check_measurement.created_at/updated_at` ORM metadata 改为 `DateTime(timezone=True)`，保留 PostgreSQL 既有时区语义。

## 真实 clone 结果

| 检查 | 结果 |
|---|---|
| `alembic upgrade head` | 通过 |
| 第二次 `alembic upgrade head` | 通过，无重复变更 |
| 最终 revision | `20260727_batch48_pg_parity` |
| `alembic check` | `No new upgrade operations detected.` |
| 目标 nullable 漂移 | 0 |
| 目标新增索引 | 5/5 |
| 删除数据/对象 | 0 |

代表性数据保留计数：

| 表 | 升级前 | 升级后 |
|---|---:|---:|
| `environment` | 0 | 0 |
| `knowledge_source` | 1 | 1 |
| `requirement_document` | 1 | 1 |
| `test_case` | 0 | 0 |

## 结论

51 项差异可以通过一个无删除的后续迁移和两处 metadata 类型校正收敛。真实旧 PostgreSQL clone 已达到唯一 head，升级幂等，完整 `alembic check` 为零漂移。
