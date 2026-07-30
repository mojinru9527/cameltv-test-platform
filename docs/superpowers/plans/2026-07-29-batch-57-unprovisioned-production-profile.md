# Batch 57 Unprovisioned Production Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 将尚未采购服务器的 production 实例标记为预留配置，不把缺少真实
URL 误报为 Batch 57 缺陷，同时保持未来部署所需的安全门禁。

**Architecture:** local 继续固定运行在 `http://localhost:5173`。production
只保留独立 profile、Compose project 和 PostgreSQL 契约；在服务器、域名和
数据库就绪前不创建真实 `production.env`、不启动、不形成部署通过证据。

**Tech Stack:** Markdown、PowerShell runtime profile contract、Docker Compose。

---

### Task 1: Record the provisioning boundary

**Files:**

- Modify: `test-platform-v2/config/runtime/production.env.example`
- Modify: `test-platform-v2/README.md`
- Modify: `test-platform-v2/deploy/README.md`

- [x] **Step 1:** State that the committed production profile is a blocked
  template, not a deployed address.
- [x] **Step 2:** Keep local and production identities distinct without
  inventing a reachable URL.
- [x] **Step 3:** Keep HTTPS, PostgreSQL, secure-cookie, placeholder and explicit
  confirmation checks unchanged for the future real deployment.

### Task 2: Pause the VPN runbook

**Files:**

- Modify: `test-platform-v2/docs/生产测试平台固定配置与双VPN切换验收手册.md`
- Modify: `docs/测试平台全功能验收文档-环境链接与账号汇总.md`

- [x] **Step 1:** Mark the runbook `paused` and add an explicit do-not-use notice.
- [x] **Step 2:** Remove active navigation links that present it as the current
  operating procedure.
- [x] **Step 3:** Mark infrastructure worksheet items `DEFERRED` instead of
  external acceptance blockers.

### Task 3: Align Batch 57 acceptance wording

**Files:**

- Modify: `test-platform-v2/work-logs/batch-57-environment-targets-and-batch56-acceptance.md`
- Modify: `docs/superpowers/plans/2026-07-29-batch-57-local-production-and-batch56-closure.md`

- [x] **Step 1:** Record the user's decision that production infrastructure is
  not provisioned in Batch 57.
- [x] **Step 2:** Separate static production-readiness checks from actual
  deployment acceptance.
- [x] **Step 3:** Preserve all Batch 56 product acceptance blockers unchanged.

### Task 4: Validate

**Files:**

- Verify all files above.

- [x] **Step 1:** Run `git diff --check`.
- [x] **Step 2:** Confirm no real URL, password, Token, Cookie or database
  credential was added.
- [x] **Step 3:** Confirm production startup remains blocked by committed
  placeholders.
