# Batch 289 — Dev Summary

| 文件 | 说明 |
|------|------|
| `app/aiqe/drivers/db_readonly_driver.py` | assert_readonly + DbReadonlyDriver + QueryResult |
| `tests/test_aiqe_db_readonly_driver.py` | 16 条（SELECT/参数/CTE/注释/字面量/9 类写操作/行数上限） |

## 行为

- `assert_readonly()` 返回**原始 SQL**（校验用清洗副本），保证字面量不被改写；
- 执行前按方言设置只读会话（SQLite `PRAGMA query_only=ON` / PG `SET TRANSACTION READ ONLY`）；
- `query()` 用 `fetchmany(max_rows+1)` 判断超限并抛 `RowLimitExceeded`，不截断；
- 多语句、写/DDL/PRAGMA/SET/事务控制一律 `UnsafeSqlError`。

## 验证

```text
pytest tests/test_aiqe_db_readonly_driver.py → 16 passed
pytest -q                                    → 1470 passed / 43 skipped
quality_ratchet.py                           → PASS
```
