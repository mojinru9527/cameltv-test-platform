# Batch 289（M2 / TA-014）— DB Read-only Assertion Driver：PRD

> **部门**：🟦 Product · **日期**：2026-11-11 · **批次模式**：完整
> **分支**：feature/batch-289-m2-db-driver · **基线**：origin/main `1ba0d1d52`

## 1. 问题

断言需要读库核验业务状态，但直接执行 SQL 风险高：写操作、DDL、多语句、超大结果集都可能
破坏数据或拖垮平台。TA-014 要求只读、可拒绝、有行数上限。

## 2. 目标

1. `DbReadonlyDriver.query(sql, params, max_rows)`：仅单条 SELECT/WITH/EXPLAIN；
2. 拒绝 INSERT/UPDATE/DELETE/DDL/PRAGMA/SET/事务控制与多语句；
3. 字符串字面量/注释中的关键字的误报要排除；
4. 行数超限抛 `RowLimitExceeded`（不静默截断）；
5. SQLite `PRAGMA query_only=ON` / PostgreSQL `SET TRANSACTION READ ONLY` 双保险。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | SELECT 返回列/行 | `test_select_returns_rows_and_columns` |
| A2 | 参数绑定 | `test_params_binding` |
| A3 | 字面量/注释不误报 | `test_keyword_inside_literal_allowed` / `test_comments_allowed` |
| A4 | CTE 允许 | `test_cte_select_allowed` |
| A5 | 写/DDL/多语句全拒 | `test_write_and_multi_statement_rejected`（9 组） |
| A6 | 行数上限报错 | `test_row_limit_exceeded` |
| A7 | 全量 + ratchet | CI |

## 4. 非目标

- 断言 DSL/期望值比较（由 assertion 层）；
- PG 真实连接测试（CI 用 SQLite；PG 路径随 M2 集成批次）；
- 查询计划/索引建议。
