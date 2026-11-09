# Batch 283（M2 / TA-009）— QA Report

> **部门**：🔍 QA · **日期**：2026-11-10

| # | 标准 | 结果 | 证据 |
|---|------|:----:|------|
| A1 | 合法样例通过 | ✅ | `test_valid_sample_passes` |
| A2 | 环/悬空依赖/重复 key | ✅ | `test_dependency_cycle` / `test_missing_dependency` / `test_duplicate_node_key` |
| A3 | 未注册 driver/capability | ✅ | `test_unregistered_*` |
| A4 | 悬空变量/非祖先/未声明输出 | ✅ | `test_variable_*` |
| A5 | 非幂等写重试 | ✅ | 拒绝 + 带 idempotency 放行 |
| A6 | assertion expected / exploratory | ✅ | `test_assertion_*` |
| A7 | edge 一致性 / checksum | ✅ | `test_edge_*` / `test_checksum_*` |
| A8 | 全量 + ratchet | ✅ | 1414 passed / 43 skipped；PASS |

## 缺陷

无（首轮 16/16 通过；ratchet 首轮即 PASS）。

## 风险

- capability 注册表尚未落地（当前可选）；TA-015 时强制；
- 规则 6（写动作 profile policy）未实现，TA-010 接入。

## 判定

A1–A8 全绿，建议 Leader APPROVED。
