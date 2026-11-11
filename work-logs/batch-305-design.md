# Batch 305 — Design / Dev

## 数据

`defect_regressions`：id / defect_id(FK CASCADE) / fixed_sha / previous_run_id /
verification_run_id / status(pending|passed) / created_at。

## 接口

```python
create_regression(db, defect_id, fixed_sha, previous_run_id=None, verification_run_id=None)
compare_runs(previous_results, current_results) -> {
  fixed, regressed, still_failing, new_assertions, total_previous, total_current
}
POST /defects/{id}/regressions  {fixed_sha, previous_run_id?, verification_run_id?}
```

## 前端

- `RegressionDialog`：SHA ≥7 位校验，提交回调；
- `RunComparison`：旧/新断言四分类 + 空态；
- 路由基线 322 → 323。

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-305-1 | 回归记录独立表 | 保留每次回归历史 |
| D-305-2 | compare_runs 纯函数 | 保证旧 Run 不被修改 |
| D-305-3 | 无 verification_run 为 pending | 调度器接真实 Run 后再落 passed |
| D-305-4 | SHA 长度 ≥7 | 与短 SHA 习惯一致 |

## 文件

- `app/models/defect.py`、`app/services/defect_service.py`、`app/api/v1/defect.py`、`app/schemas/defect.py`
- `alembic/versions/20261120_ta027_defect_regressions.py`
- `frontend/src/pages/defect/RegressionDialog.tsx`、`RunComparison.tsx`
- tests: backend 7 + frontend 4
