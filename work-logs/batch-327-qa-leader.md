# Batch 327 — Design / QA / Leader

## 接口

```python
PACKS = {ecommerce, saas, iot}
get_pack(key) -> DomainPack
validate_pack(pack) -> {key, valid, checks}
apply_pack(key) -> {pack, roles, entities, checks, capabilities, validation}
```

## QA

| # | 结果 | 证据 |
|---|:----:|------|
| A1–A7 | ✅ | 7 单测 |
| A8 | ✅ | 全量 + ratchet PASS |

## Leader Verdict

# ✅ APPROVED

- TA-043/044/045 验收达成（三域 Pack + 必备检查门禁）；
- 全量 + ratchet 通过，无迁移。

放行：合入 main → M8 发布 + 收口。
