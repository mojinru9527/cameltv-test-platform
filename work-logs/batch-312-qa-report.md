# Batch 312 — QA Report

| # | 标准 | 结果 | 证据 |
|---|------|:----:|------|
| A1 | 只读查询 | ✅ | `test_read_tool_delegates` |
| A2 | 写需审批 | ✅ | `test_write_requires_approval` |
| A3 | 无效 token | ✅ | `test_write_invalid_token_rejected` |
| A4 | 有效 token | ✅ | `test_write_with_valid_token` |
| A5 | 未知工具 | ✅ | `test_unknown_tool` |
| A6 | 元数据/Agent | ✅ | `test_tool_metadata_and_agents` |
| A7 | 适配器缺失 | ✅ | `test_missing_reader_adapter` |
| A8 | 全量 + ratchet | ✅ | 见 CI |

## 判定

A1–A8 全绿，建议 Leader APPROVED。
