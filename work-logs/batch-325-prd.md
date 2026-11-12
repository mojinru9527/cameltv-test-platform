# Batch 325（M8 / TA-040）— 小程序 Adapter：PRD

> **模式**：完整 · **分支**：feature/batch-325-m8-miniapp-adapter · **基线**：`e947af1eb`

## 目标

1. 微信版本兼容矩阵（≥3 版本，minium / weapp-dev-mcp 双后端）；
2. `resolve_backend()` 首选 minium，不支持时回退 weapp-dev-mcp；
3. 5 条小程序用例（首页/直播列表/赛事详情/收藏/分享）；
4. 未知版本/后端显式报错。

## 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 矩阵覆盖 | `test_matrix_covers_versions` |
| A2 | 首选 minium | `test_resolve_preferred_minium` |
| A3 | 回退 | `test_resolve_falls_back_to_weapp_mcp` |
| A4 | 非法版本 | `test_unknown_version_and_backend_rejected` |
| A5 | 5 用例 | `test_adapter_runs_five_cases` |
| A6 | 全量 | pytest + ratchet |

## 非目标

- 真实 minium/微信开发者工具执行（executor 注入）。
