# Batch 320 — Design / Dev

## 协议处理

```python
handle_message(message, gateway) -> response | None
```

| method | 行为 |
|--------|------|
| initialize | 返回协议版本/capabilities/serverInfo |
| ping | `{}` |
| tools/list | 工具清单 + `_meta.mode/requires_approval` |
| tools/call | 取 `approval_token` 后调 gateway；McpError → `isError=true` |
| 其它 | `-32601` |

## 文件

- `scripts/mcp-server/aiqe_mcp/server.py`
- `scripts/mcp-server/README.md`
- `tests/test_aiqe_mcp_server.py`（5 条）

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-320-1 | 手写 JSON-RPC，不引 SDK | 零依赖、易审计、可 stdio 冒烟 |
| D-320-2 | 错误走 isError | MCP 客户端可继续会话 |
| D-320-3 | reader 可注入 | 生产接后端 adapter |
| D-320-4 | 只 stdio | Codex/Cursor 本地注册即用 |
