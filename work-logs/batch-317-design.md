# Batch 317 — Design / Dev / QA

## 接口

```python
build_page_map(pages) -> {nodes:[{id,title}], edges:[{from,to}]}
group_rule_results(results) -> {rules:{A01..A24:{total,passed,failed}}, unknown_rules, total, covered_rules}
coverage_metrics(pages, results) -> {page_coverage, rule_coverage, assertion_pass_rate}
build_evidence_bundle(pages, results) -> {page_map, rule_results, coverage}
```

## QA

| # | 结果 | 证据 |
|---|:----:|------|
| A1 | ✅ | `test_page_map_nodes_and_edges` |
| A2 | ✅ | `test_rule_grouping_has_24_rules` |
| A3 | ✅ | `test_unknown_rule_flagged` |
| A4 | ✅ | `test_coverage_metrics` |
| A5 | ✅ | `test_evidence_bundle_contains_all_sections` |
| A6 | ✅ | `test_invalid_pages_rejected` |
| A7 | ✅ | 6 单测；全量通过；ratchet PASS |

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-317-1 | 规则固定 A01..A24 | 与 24 准则一一对应 |
| D-317-2 | 未知规则不静默 | 防止规则漂移 |
| D-317-3 | 三指标独立 | 页面/规则/断言可分别看 |

## 文件

- `app/aiqe/services/asset_map_integration.py`
- `tests/test_aiqe_asset_map.py`（6 条）
