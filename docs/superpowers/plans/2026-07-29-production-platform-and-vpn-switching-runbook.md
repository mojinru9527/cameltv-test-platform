# Production Platform and VPN Switching Runbook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 交付一份可逐项填写的生产测试平台固定配置手册，以及 vpn07/OpenVPN
互斥切换、校验、证据与回滚 SOP。

**Architecture:** 不让两套全局隧道同时参与验收。网络状态固定为
`NEUTRAL → TEST_OPENVPN → NEUTRAL → PROD_VPN07`，每次转换先停止业务请求，
再关闭旧隧道、清理 DNS/浏览器连接、启用新隧道并执行 fail-closed 校验。
生产配置只写入 Git 忽略的 `production.env`，文档只保存字段名和逻辑资源 ID。

**Tech Stack:** Windows 11、PowerShell 7、OpenVPN Connect、vpn07 TUN、
Docker Compose、PostgreSQL 16、CamelTv Test Platform v2。

---

### Task 1: Map current configuration and network controls

**Files:**

- Inspect: `test-platform-v2/config/runtime/production.env.example`
- Inspect: `test-platform-v2/scripts/start-platform-environment.ps1`
- Inspect: `test-platform-v2/backend/app/services/openvpn_service.py`
- Inspect: `docs/测试平台全功能验收文档-环境链接与账号汇总.md`

- [x] **Step 1:** Confirm production uses an ignored fixed profile, HTTPS,
  PostgreSQL, secure cookies and explicit startup confirmation.
- [x] **Step 2:** Confirm the existing OpenVPN preflight can connect OpenVPN but
  cannot stop or restore vpn07.
- [x] **Step 3:** Confirm the current Windows host exposes separate vpn07 Meta
  Tunnel and OpenVPN TAP adapters, so an explicit mutual-exclusion guard is needed.

### Task 2: Write the operator runbook

**Files:**

- Create: `test-platform-v2/docs/生产测试平台固定配置与双VPN切换验收手册.md`

- [x] **Step 1:** Add a non-secret production profile worksheet and exact
  initialization/validation commands.
- [x] **Step 2:** Add the four-state transition model, TEST and PROD procedures,
  PowerShell adapter/proxy guards, target probes and browser/DNS reset steps.
- [x] **Step 3:** Add evidence boundaries, rollback rules, external input order and
  the contract for a future one-click switcher.

### Task 3: Validate the document

**Files:**

- Verify: `test-platform-v2/docs/生产测试平台固定配置与双VPN切换验收手册.md`

- [x] **Step 1:** Run `git diff --check`.
- [x] **Step 2:** Verify commands do not print profile contents, passwords,
  Tokens, Cookies or Authorization headers.
- [x] **Step 3:** Verify no undocumented vpn07 CLI is invented and no step allows
  vpn07/OpenVPN to remain active together.

## Self-review

- Spec coverage: production URL/database worksheet, secret handling, test-to-prod
  switching, validation, evidence and rollback are all present.
- Placeholder policy: operator-entered values are intentionally represented as
  worksheet cells; implementation steps contain exact paths and commands.
- Safety: the runbook never changes routes automatically and fails closed when
  both tunnel adapters are active.
