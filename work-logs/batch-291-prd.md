# Batch 291（M3 / TA-016）— Playwright MCP Explorer PoC：PRD

> **部门**：🟦 Product · **日期**：2026-11-11 · **批次模式**：完整
> **分支**：feature/batch-291-m3-playwright-mcp-explorer · **基线**：origin/main `fdf719824`
> **里程碑**：M3 第 1 批（M2 已收口，生产 20261115 已部署）

## 1. 问题

AI 需要"看懂"测试页面（DOM/A11y）并执行动作，但直接给浏览器权限风险高：任意域名、
元数据 IP、file:// 都可能外泄。TA-016 先用 PoC 验证：输出 DOM/A11y + 动作日志，且越权域名被拒。

## 2. 目标

1. `PlaywrightExplorer.explore(url, actions)`：复用 batch-288 Driver，输出 DOM/A11y/动作日志/证据；
2. 动作：click / fill / wait_for / text；失败记录并停止；
3. 域名 allowlist：精确或 `*.example.com`；拒绝非 http(s)、IP 元数据；
4. 纯函数 `handle_tool("explore_page", …)`，后续可薄封装为 MCP server。

## 3. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 允许域名返回 DOM/A11y/日志 | `test_explore_allowed_domain` |
| A2 | 越权域名拒绝且不导航 | `test_disallowed_domain_rejected_before_navigation` |
| A3 | 通配子域 / 后缀伪装拒绝 | `test_wildcard_subdomain_allowed` |
| A4 | 非 http(s) 拒绝 | `test_non_http_scheme_rejected` |
| A5 | 动作失败停止并记录 | `test_action_failure_stops_and_logs` |
| A6 | 未知动作/元数据 IP | `test_unknown_action_logged` / `test_metadata_ip_rejected` |
| A7 | 工具入口 | `test_handle_tool_explore_page` |
| A8 | 全量 + ratchet | CI |

## 4. 非目标

- MCP SDK/stdio server 封装（后续批次）；
- 真实 AI 定位策略（先用确定性动作序列）；
- 多标签/下载/上传。
