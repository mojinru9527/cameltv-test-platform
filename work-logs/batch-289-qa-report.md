# Batch 289 — QA Report

| # | 标准 | 结果 | 证据 |
|---|------|:----:|------|
| A1 | SELECT 列/行 | ✅ | `test_select_returns_rows_and_columns` |
| A2 | 参数绑定 | ✅ | `test_params_binding` |
| A3 | 字面量/注释不误报 | ✅ | `test_keyword_inside_literal_allowed` / `test_comments_allowed` |
| A4 | CTE | ✅ | `test_cte_select_allowed` |
| A5 | 写/DDL/多语句全拒 | ✅ | 9 组参数化 |
| A6 | 行数上限 | ✅ | `test_row_limit_exceeded` |
| A7 | 全量 + ratchet | ✅ | 1470 passed / 43 skipped；PASS |

## 缺陷

| # | 现象 | 根因 | 修复 |
|---|------|------|------|
| 1 | 字面量被替换成空串 | 校验清洗副本被当作执行 SQL | 执行原始 SQL（D-289-1） |

## 风险

- PG `SET TRANSACTION READ ONLY` 路径未在本机 PG 验证（CI 用 SQLite）；
- 只读驱动未接入断言执行链（TA-015/调度集成时）。

## 判定

A1–A7 全绿，建议 Leader APPROVED。
