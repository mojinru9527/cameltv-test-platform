# Batch 325 — Design / QA / Leader

## 接口

```python
WECHAT_MATRIX[version] = {minium, weapp_dev_mcp, notes}
resolve_backend(version, preferred="minium") -> backend
MiniappAdapter(executor).run() -> summary
CASES = MP-001..MP-005
```

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-325-1 | 双后端矩阵 | 微信版本差异大，回退兜底 |
| D-325-2 | 未知版本拒绝 | 防“看起来跑通”的假兼容 |
| D-325-3 | executor 注入 | 真机/开发者工具后续接 |

## QA

| # | 结果 | 证据 |
|---|:----:|------|
| A1–A5 | ✅ | 5 单测 |
| A6 | ✅ | 全量 + ratchet PASS |

## Leader Verdict

# ✅ APPROVED

- TA-040 验收达成（版本矩阵 + 后端回退 + 5 用例）；
- 全量通过、ratchet PASS、无迁移。

放行：合入 main → TA-041 Desktop Driver。
