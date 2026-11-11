# Batch 312 — Design / Dev

## 接口

```python
AiqeMcpGateway(reader, writer, approval_verifier)
  .list_tools() -> [{name, description, mode, requires_approval?}]
  .supported_agents() -> ("claude-code","codex","cursor")
  .call(tool, arguments, approval_token=None)
```

## 门禁

| 工具类型 | 要求 |
|----------|------|
| read | reader 必须配置 |
| write | 非空 approval_token + verifier 通过，才调用 writer |
| 未知 | `UnknownTool` |

## 决策

| ID | 决策 | 理由 |
|----|------|------|
| D-312-1 | adapter 注入 | 与 DB/API 解耦，PoC 可测 |
| D-312-2 | 写动作默认拒绝 | fail-closed |
| D-312-3 | 审批与执行同 token | 审计可追溯 |
| D-312-4 | 三类 Agent 显式声明 | Skill + MCP 兼容性可验证 |

## 文件

- `scripts/mcp-server/aiqe_mcp/gateway.py`
- `tests/test_aiqe_mcp_gateway.py`（7 条）
