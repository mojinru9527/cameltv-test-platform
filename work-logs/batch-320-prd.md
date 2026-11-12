# Batch 320（M7 / TA-036）— 内网 MCP Server：PRD

> **部门**：🟦 Product · **日期**：2026-11-12 · **批次模式**：完整
> **分支**：feature/batch-320-m7-mcp-server · **基线**：origin/main `291a89850`
> **里程碑**：**M7 第 1 批**

## 1. 问题

前面只有 MCP Gateway 纯函数，外部 Agent 无法真正通过 `mcp add` 连接；TA-036 要提供
可运行的 stdio MCP Server。

## 2. 目标

1. `scripts/mcp-server/aiqe_mcp/server.py`：JSON-RPC 2.0 stdio；
2. 支持 `initialize / ping / tools/list / tools/call`；
3. `tools/call` 写操作必须 `approval_token`；错误以 `isError` 返回而非崩溃；
4. Codex CLI 注册命令写入文档。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | initialize | `test_initialize` |
| A2 | tools/list | `test_tools_list` |
| A3 | 只读 call | `test_tools_call_read` |
| A4 | 写无 token 报错 | `test_write_without_token_returns_error` |
| A5 | 未知 method | `test_unknown_method` |
| A6 | stdio 冒烟 | initialize 手动通过 |
| A7 | 全量 + ratchet | CI |

## 4. 非目标

- HTTP/SSE 传输（先 stdio）；
- 真实后端 adapter（reader/writer 可替换）。
