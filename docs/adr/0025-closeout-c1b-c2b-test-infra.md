---
title: "ADR-0025: 收尾批次（C1b/C2b + 测试基建）"
owner: "qa-team"
created: "2026-09-02"
last_reviewed: "2026-09-02"
status: "accepted"
expires: "2027-09-02"
tags: ["adr", "browser", "binding", "test-infra"]
related: ["0024-execution-chain-c1c2.md", "0026-production-execution-resource-ownership.md"]
---

# ADR-0025 — 收尾批次（C1b/C2b + 测试基建，Batch 210）

> Status: Accepted (2026-09-02) | Owner: qa-team | Tags: browser, binding, test-infra

## 决策
- **C1b（部分）**：`browser_capability_available()` 观测；无 runner 的 browser 步骤区分
  `no_browser_runtime`（无 Playwright）与 `no_browser_runner_registered`（有能力、worker 未接），
  结果带 `browser_capability` 标志。真实 Playwright BrowserDriver 注入常驻 Temporal worker
  仍列 **C1c**（需真实 UI 环境/设备批次）。
- **C2b**：materialize 对「无 observations 且命令数==1（api/data）」的 APPROVED
  DB/EVENT/LOG oracle 按默认类型兜底物化（DB→DB_COLUMN 等）；多命令不臆测。
- **测试基建**：lanhu-mcp 子模块缺失时 lanhu/deploy 相关 40+ 测试改为 `pytest.skip`
  （带可操作原因），本地全量噪音 6→1；CI（子模块已初始化）仍执行。
- notification_channel 本地失败为本地 DB 环境项（CI 通过），记录不阻断。

## 移交（后续）
- C1c：真实 Playwright runner 注入 Temporal worker（需 UI 环境）。
