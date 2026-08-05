# Batch 93 — PRD-lite（响应式回归常驻 CI）

> **Product (🟦)** | Date: 2026-08-05 | Status: Review

```markdown
mode: light
豁免理由: 纯 CI 配置 + 文档（无生产代码/接口/配置变更）；按 pipeline-modes.md 判定轻量批次（PRD-lite + QA + Leader + 看板）。
非目标: 不改响应式 spec 断言语义；不新增前端/后端代码；不改变 PR 门禁（仅定时 + 手动触发）。
```

## 1. 问题陈述

Batch 89 交付了双视口（768×1024 / 390×844）响应式回归 spec，但只在本地手动运行——没有常驻门禁，回归只能靠人工想起才跑。响应式是高频回归点（新页面/布局改动容易破坏移动端可用性），需要定时自动化兜底。

## 2. 成功指标

| 指标 | 基线 | 目标 |
|------|------|------|
| CI workflow | 无 | `.github/workflows/responsive-e2e.yml`：每日定时 + workflow_dispatch 手动触发 |
| 执行链路 | 手动 | CI 自动启动前后端（隔离 SQLite）→ 跑 batch89-responsive.spec → 上传截图/报告 |
| 文档 | 无 | `docs/agent-team/responsive-e2e-ci.md`：触发方式/扩展指引/失败处理 |
| 门禁 | — | workflow YAML 可解析；spec 本地仍 2/2 通过；不破坏 ai-delivery-policy 契约测试 |

## 3. 用户故事 + 验收标准

- As a **维护者**, I want 响应式回归每日自动执行，so that 移动端回归不依赖人工记忆。
  - Given workflow 配置完成，When 手动触发（workflow_dispatch），Then 前后端启动 → spec 2/2 → 证据上传。

## 4. 技术考量

- 独立 ubuntu runner；后端隔离 SQLite + 固定测试凭据（ADMIN/TESTER_PASSWORD 环境变量注入种子）。
- 前端 dev server + Playwright chromium（--with-deps）；spec 经 BASE_URL/E2E_USERNAME/E2E_PASSWORD 驱动。
- 不接入 PR 门禁（避免与现有 main-quality-gate 重复）；保留人工触发与每日定时。
