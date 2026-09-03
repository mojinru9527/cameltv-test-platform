---
title: "Batch 226 体育 16.0.0 AI 全链路证据索引"
owner: "qa-team"
last_reviewed: "2026-09-03"
status: "active"
expires: "2027-03-03"
tags: ["batch-226", "sports", "16.0.0", "ai-e2e", "evidence"]
related:
  - "work-logs/batch-226-sports-v16-ai-e2e-qa-report.md"
  - "work-logs/evidence/batch-226-sports-v16-ai-e2e/b1-b15-matrix.json"
---

# Batch 226 证据索引

本目录记录在 `origin/main@cacfaeec` 上，以体育业务 `16.0.0` 需求执行的最终验收。证据只包含业务结果、网络计数和截图，不包含账号、密码、Token、API Key 或运行数据库。

## 输入与环境

- 输入：`体育平台-16.0.0-需求规格说明书.md`
- SHA-256：`C039115C51A5BAD50B354AE1FB708FA985AF406FA03AA5AE864B6D1CD7F74466`
- 大小：4315 bytes；72 行
- Worktree：`feature/batch-226-sports-v16-ai-e2e`
- 基线：`cacfaeec3e832374d918664bd32b6da059d55f57`
- 本地服务：frontend `5566` / backend `8899`

## 证据地图

| 路径 | 内容 |
|------|------|
| `manifests/input-manifest.json` | 体育 16.0.0 输入文件哈希、大小与行数 |
| `runtime/environment.json` | 隔离 worktree、基线和本地端口（无凭据） |
| `b1-b15-matrix.json` | B1-B15 逐项 PASS/BLOCKED 结论与解除条件 |
| `version-task/version-chain-audit.json` | VersionTask 任务、方案、执行、证据包、知识、回归、对比和指标快照 |
| `aitde/aitde-chain.json` | AITDE Source→Scope→Contract→Scenario→Run 首轮链路 |
| `aitde/aitde-continuation.json` | Campaign、Quality Gate、Acceptance 和 AI Operation 结果 |
| `aitde/network-guard.json` | Source/Contract 页 GET 次数、500 和控制台错误核对 |
| `blackbox/final-blackbox.json` | tester 五入口、B14/B15、响应式与 HTTP 结果 |
| `screenshots/` | VersionTask 及入口走查截图 |
| `aitde/screenshots/` | AITDE 各阶段与失败态截图 |
| `blackbox/` | tester 桌面端及关键页平板/手机截图 |

## 防假成功结论

- VersionTask：30 个无执行目标的方案全部记为 `blocked`，通过数为 0，放行按钮禁用。
- AITDE：确定性降级产物可以继续供人工审阅，但对应 AI Operation 保持 `FAILED`；零执行时 Quality Gate 为 `FAIL`。
- B15：缺 OpenAPI 时保持 `onboarding/step=1`，不创建虚假基线、不切为 `active`。

空的本地服务 stdout/stderr 文件不纳入交付；本地 SQLite 数据库不纳入版本控制。
