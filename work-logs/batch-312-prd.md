# Batch 312（M5 / TA-032）— AIQE MCP Gateway：PRD

> **部门**：🟦 Product · **日期**：2026-11-12 · **批次模式**：完整
> **分支**：feature/batch-312-m5-mcp-gateway · **基线**：origin/main `3e37752dc`
> **里程碑**：M5 第 4 批

## 1. 问题

外部 Agent（Claude Code / Codex / Cursor）需要通过 MCP 查询 Run；写动作若无审批门禁，
可能被 Agent 直接触发执行/关单。

## 2. 目标

1. `scripts/mcp-server/aiqe_mcp/gateway.py`：
   - 只读工具：`list_runs / get_run / get_run_events / get_artifact_meta`；
   - 写工具：`create_run / retry_run / close_defect`，**必须审批 token**；
2. 审批校验失败/缺失 → `ApprovalRequired`，不调用 writer；
3. 未知工具 → `UnknownTool`；
4. 元数据声明 read/write 与 `requires_approval`；
5. 声明支持的 3 类外部 Agent。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | Codex 可查 Run | `test_read_tool_delegates` |
| A2 | 写操作无 token 拒绝 | `test_write_requires_approval` |
| A3 | 无效 token 拒绝 | `test_write_invalid_token_rejected` |
| A4 | 有效 token 执行 | `test_write_with_valid_token` |
| A5 | 未知工具 | `test_unknown_tool` |
| A6 | 元数据/3 类 Agent | `test_tool_metadata_and_agents` |
| A7 | 全量 + ratchet | CI |

## 4. 非目标

- 真实 MCP stdio/HTTP server 封装（adapter 由调用方注入）；
- OAuth/审批中心（token 由上层签发校验）。
