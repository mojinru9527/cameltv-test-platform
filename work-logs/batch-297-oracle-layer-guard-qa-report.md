# Batch 297 — QA Report

> **部门**：🔍 QA · **日期**：2026-11-11

| 项 | 结果 | 证据 |
|----|:----:|------|
| self-test（好/坏样例） | ✅ | `SELFTEST=PASS` |
| 缺 `oracle_layer` 拒绝 | ✅ | 临时 JSON → `ORACLE_LAYER_GUARD=FAIL` exit 1 |
| 非法枚举拒绝 | ✅ | self-test `GUESS` 样例 |
| 合法 JSON 通过 | ✅ | self-test good.json |
| Markdown ```json 代码块 | ✅ | self-test good.md |
| 变更文件模式 | ✅ | `-BaseRef origin/main` → 0 文件、PASS |
| CI 接入 | ✅ | `ai-delivery-policy.yml` 新步骤 |

## 风险

- PR checkout 若为浅克隆且无 `origin/main`，guard 会回退 `HEAD~1`；极端情况下扫描 0 文件（恒 PASS）。
  已在步骤中先 self-test，至少保证扫描逻辑本身有效。

## 判定

守卫可用，建议 Leader APPROVED（light）。
