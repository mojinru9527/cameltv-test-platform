# Batch 317（M6 / TA-034.2）— Asset-map 接入平台：PRD

> **部门**：🟦 Product · **日期**：2026-11-12 · **批次模式**：完整
> **分支**：feature/batch-317-m6-asset-map · **基线**：origin/main `7f9c437a8`
> **里程碑**：M6 第 3 批

## 1. 问题

版本任务 step 2 需要页面地图；24 准则 assertion 结果与覆盖率三指标要进 EvidenceBundle/判定页。

## 2. 目标

1. `build_page_map(pages)`：页面节点 + 跳转边；
2. `group_rule_results(results)`：固定 24 条规则（A01..A24），未知规则标记；
3. `coverage_metrics`：页面覆盖率 / 规则覆盖率 / 断言通过率；
4. `build_evidence_bundle`：三块聚合，供 EvidenceBundle 使用。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 页面地图 | `test_page_map_nodes_and_edges` |
| A2 | 24 准则分组 | `test_rule_grouping_has_24_rules` |
| A3 | 未知规则 | `test_unknown_rule_flagged` |
| A4 | 三指标 | `test_coverage_metrics` |
| A5 | Bundle 三块 | `test_evidence_bundle_contains_all_sections` |
| A6 | 非法输入 | `test_invalid_pages_rejected` |
| A7 | 全量 + ratchet | CI |

## 4. 非目标

- 前端页面地图渲染（数据契约先固化）；
- 真实覆盖率采集（由节点上报）。
