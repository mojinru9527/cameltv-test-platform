# Batch 289 — Design / Dev

## 校验流水线

```text
assert_readonly(sql)
  ├─ 非空
  ├─ 去注释（-- / /* */）
  ├─ 去字符串字面量（'...' / "..."）→ 防关键字误报
  ├─ 分号切分：必须只有 1 条
  ├─ 首 token ∈ {SELECT, WITH, EXPLAIN}；WITH 必须含 SELECT
  └─ 全词匹配禁用关键字（INSERT/UPDATE/DELETE/DDL/PRAGMA/SET/事务控制…）
→ 返回原始 SQL（不是清洗后的，保留字面量）
```

## 执行

```python
with engine.connect() as conn:
    sqlite: PRAGMA query_only=ON
    postgres: SET TRANSACTION READ ONLY
    result = conn.execute(text(sql), params)
    rows = result.mappings().fetchmany(max_rows + 1)
if len(rows) > max_rows: raise RowLimitExceeded
```

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-289-1 | 校验用清洗副本、执行用原 SQL | 保留字符串字面量真实性 |
| D-289-2 | 行数超限报错而非截断 | 断言不能静默丢数据 |
| D-289-3 | 禁用词采用词边界匹配 | 避免 SELECT 列名/关键字误伤 |
| D-289-4 | SQLite/PG 各设只读会话 | 解析器之外的第二道防线 |

## 文件

- `app/aiqe/drivers/db_readonly_driver.py`
- `tests/test_aiqe_db_readonly_driver.py`（16 条）
