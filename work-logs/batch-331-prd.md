# Batch 331（P2）— MCP HTTP Adapter + 真实执行探针：PRD

> 模式：完整 · 分支：feature/batch-331-p2-mcp-adapter · 基线：`b902e9f79`

## 目标

1. `HttpMcpAdapter`：生产 reader/writer 走后端 HTTP API，写操作带 `X-Approval-Token`；
2. 探针：Appium `/status`、minium CLI、pywinauto、paho-mqtt 可用性；
3. 未知工具/HTTP 错误显式抛出。

## 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 只读 HTTP | `test_reader_get_run` |
| A2 | 写审批头 | `test_writer_passes_approval_header` |
| A3 | HTTP 错误 | `test_http_error_raises` |
| A4 | 探针 | `test_probes` |
| A5 | ratchet | PASS |

## 非目标

- 三端截图（需真实客户端）。
