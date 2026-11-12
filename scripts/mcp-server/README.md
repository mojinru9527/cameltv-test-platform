# AIQE MCP Server

stdio JSON-RPC 2.0，供 Codex CLI / Claude Code / Cursor 注册。

## 启动

```bash
python scripts/mcp-server/aiqe_mcp/server.py
```

## 注册

Codex CLI：

```bash
codex mcp add cameltv-aiqe -- python /abs/path/scripts/mcp-server/aiqe_mcp/server.py
codex mcp list
```

Claude Code / Cursor：在 MCP 配置中加入同样的 stdio 命令（`command: python`, `args: [...server.py]`）。

## 工具

| 工具 | 模式 | 说明 |
|------|------|------|
| list_runs / get_run / get_run_events / get_artifact_meta | read | 查询 Run/事件/证据 |
| create_run / retry_run / close_defect | write | 需 `approval_token`（由上层审批签发） |

## 协议

- `initialize` → `protocolVersion=2024-11-05`；
- `tools/list` → 工具清单（`_meta` 标注 read/write）；
- `tools/call` → `{name, arguments}`；写操作参数需带 `approval_token`；
- 错误以 `result.isError=true` 返回，不中断连接。

## 安全

- 默认 reader 为占位；生产需注入后端 adapter（校验项目/权限）；
- 写操作无 token / token 无效一律拒绝。
