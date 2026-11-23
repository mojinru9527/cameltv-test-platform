# TC-010 Benchmark Gate 用户豁免记录

日期：2026-11-23
项目：CamelTv AIQE V1.6
关联：TC-AIQE-010、候选 `81e7bc4d-a7cc-4415-82a1-651447217c05`

## 用户决定

用户明确表示：

> 没有这么多样本数据，先通过。

## 事实

Benchmark Run `02714449-6f28-4401-9ba7-0cdf1a1bcce8` 已真实执行：

- samples = 1；
- precision = 0.0；
- recall = 0.0；
- f1 = 0.0；
- unknown_rate = 1.0；
- gate_eligible = false；
- Gate 拒绝原因：
  - `SAMPLE_COUNT_BELOW_MIN(1 < 30)`
  - `THRESHOLDS_NOT_MET`
  - `UNKNOWN_RATE_TOO_HIGH(1.000 > 0.3)`
  - `BOOTSTRAP_NO_PUBLISHED_BASELINE`

候选状态：`rejected`。

## 豁免范围

用户接受在**没有 30+ 标注样本、没有 baseline、Benchmark Gate 未通过**的情况下继续后续发布流程。

本豁免**不改变** TC-010 的事实状态：

- TC-010 仍为 **BLOCKED**；
- 不得写成 VERIFIED；
- 不得宣称 10/10；
- 发布报告必须披露该豁免。

## 后续

如后续补齐样本/baseline，应重新执行 Benchmark Gate；通过后才能把 TC-010 改为 VERIFIED。
