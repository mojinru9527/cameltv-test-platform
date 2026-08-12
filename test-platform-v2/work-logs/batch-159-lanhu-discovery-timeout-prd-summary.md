# Batch 159 — 蓝湖提取失败热修（超时兜底 + 真实错误透出）（PRD-lite）

> **Product (🟦)** | Date: 2026-08-12 | Status: Approved | Mode: light

mode: light
豁免理由: 纯 Bug 修复（外部依赖超时/错误透出），无新接口/新配置/新依赖，紧急生产热修。
非目标: 不改 lanhu-mcp 本体；不改变提取语义。

## 1. 问题陈述
生产「提取需求」蓝湖任务返回 `status=failed / error=蓝湖页面发现失败`（job id=26，versionId=8527f9f7）。
- 同文档旧版本（versionId=7fd9001b）任务成功（job id=24），失败页 `9c1351a0` 不在旧版本 sitemap。
- lanhu-mcp 单请求超时默认 30s 且无整体超时；大版本顺序下载易触发超时。
- provider 捕获异常后 `str(e)` 为空时（如 TimeoutError）返回空 error → `discover_pages` 兜底成通用「蓝湖页面发现失败」，真实原因不可见且无重试。

## 2. 修复
- provider：证据发现整体超时 `asyncio.wait_for(600s)` + 瞬时失败（timeout/transport）重试 1 次。
- provider：异常透出 `str(e) or type(e).__name__`（两个外层 except），不再空 error。
- discover_pages：兜底文案带 provider status，不再丢信息。
- 资源上限放宽：max_resources 500→1000、max_total_bytes 100MB→300MB、download timeout 120s→300s（新 MCP 生效）。

## 3. 验收标准
- 超时后自动重试 1 次成功（单测）。
- 空 str 异常（TimeoutError）→ error 非空且含类型名（单测）。
- discover_pages 无 error 时兜底含 status（单测）。
- 部署后用户重试原链接不再静默失败；若仍失败，错误信息可定位。

## 4. 技能使用
- cameltv-bug-guard（外部依赖超时/错误链）、cameltv-agent-team 流水线

