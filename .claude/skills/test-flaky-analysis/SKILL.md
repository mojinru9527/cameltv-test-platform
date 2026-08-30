---
name: test-flaky-analysis
description: 用于 AITDE V3.8 Flaky 分析（V38-006/007）。Use when analyzing flaky clusters, listing scenario stability, or when a real BUSINESS_FAIL must not be auto-flagged flaky. Triggers: "flaky 分析", "flaky analysis", "稳定性", "stability".
---

# Flaky 分析（Flaky Analysis）
> AITDE V3.8 V38-006..007。只把 AUTOMATION/ENV 波动纳入 Flaky；BUSINESS_FAIL 默认排除。

## 硬不变量

- `BUSINESS_FAIL` **永不**产生 flaky signal，也**永不**被自动判 pass。
- 结合 adapter / step_key / error_type / locator / environment / sample_size 聚类。
- 样本可回链到 Run（traceable）。

## 流程

1. `GET /api/v2/flaky?scenario_adapter_id=...` → 聚类列表。
2. `GET /api/v2/scenarios/{id}/stability` → 单场景稳定性。
3. 对每个聚类核对 sample_size / failure_rate / classification。

## 提交前自检

- [ ] 未把 BUSINESS_FAIL 纳入 flaky。
- [ ] 聚类样本可追溯。
- [ ] 未自动跳过 P0。
