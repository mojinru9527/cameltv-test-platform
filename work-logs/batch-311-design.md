# Batch 311 — Design / Dev

## 判定矩阵

| P0 状态 | gate_status |
|---------|-------------|
| 全部 PASS | PASS |
| 任意 FAIL | FAIL |
| 任意 UNKNOWN / NOT_RUN / PENDING | BLOCKED |
| 无 P0 | BLOCKED |

## 接口

```python
evaluate_cases([{priority, status}]) -> {
  gate_status, p0_total, p0_passed, p0_failed, p0_unknown, p0_not_run, reasons
}
evaluate_stats({p0_total,p0_passed,p0_failed,p0_unknown,p0_not_run}) -> 同上
```

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-311-1 | UNKNOWN/NOT_RUN → BLOCKED 而非 FAIL | 未验证 ≠ 失败，但绝不能 PASS |
| D-311-2 | 无 P0 → BLOCKED | 无核心验证不发放行 |
| D-311-3 | 非 P0 不阻断 | P1/P2 失败记录但不作为放行条件 |
| D-311-4 | reasons 必填 | 门禁展示不可解释原因 |

## 文件

- `app/aiqe/services/quality_gate.py`
- `tests/test_aiqe_quality_gate.py`（9 条）
