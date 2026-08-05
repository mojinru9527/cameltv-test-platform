# Batch 98 — PRD（CI 迁移 + V1 工具删除）

> **Product (🟦)** | Date: 2026-08-05 | Status: Review

```markdown
mode: full
豁免理由: 无（CI 行为变更 + V1 代码删除，属重构/配置变更，走完整六部门流水线）。
非目标: 不移除 V1 web-ui/server（Batch 99 覆盖矩阵）；不补拉 Test5 契约（C95-1，待环境恢复）；
不重建 V1 报告看板（已被 V2 report 取代，本地看板无生产价值）；不回填 prod 业务 DB/Redis
（用户确认无法提供，C64-3 以 test 环境为准关闭）。
```

## 1. 问题陈述

Batch 96 已批准废弃 11 个 V1 工具，但发现两条每日 CI 工作流（`api-regression.yml` / `prod-smoke-test.yml`）
仍依赖其中 4 个（env_check / api_tester / report_dashboard / log_aggregator）。直接删除会导致每日回归与
生产冒烟断裂。本批先完成 CI 迁移（V1 CLI → 自包含脚本 + Playwright 直跑），再删除 11 个工具及其引用，
达成 C64-1 的「V1 工具删除清理批次」，并同步处理 C64-3（prod 业务 DB/Redis 无法提供，验收以 test 为准）。

## 2. 成功指标

| 指标 | 基线 | 目标 |
|------|------|------|
| CI 依赖 V1 CLI | 2 条工作流使用 `tp` 5 个命令 | 0 引用；改用 `scripts/ci/api-regression.ps1` + Playwright 直跑 |
| 11 个 V1 工具 | 存在 | 目录删除；`rg` 全仓 0 引用（排除 node_modules/venv/work-logs/docs） |
| prod smoke 有效性 | `--filter smoke` 匹配 0 用例（空跑） | 实际执行 6 个生成式 API spec，JUnit 有真实用例数 |
| C96-1 | V1 删除未执行 | V1 工具删除完成；C27 四项仍待 staging 执行（保持 Open） |
| C64-3 | prod 待提供 | 用户确认无法提供 → 以 test 环境为准关闭（同 C31-3 口径） |
| 门禁 | — | 全量 pytest、audit 0 硬错、repo-boundaries PASS、scan HARD 0 |

## 3. 用户故事 + 验收标准

- As a **平台负责人**, I want CI 不再依赖已废弃工具，so that 删除工具不破坏每日回归。
- As a **维护者**, I want 回归脚本自包含可读，so that 新项目可复用（脚本只依赖 PowerShell/Node/Playwright）。
- As a **验收负责人**, I want prod smoke 真实执行用例，so that 冒烟不再空跑。

Given 工作流已迁移且 11 个工具已删除，When 全仓检索 `tools.<tool>` 与 `tp <cmd>`，Then 0 引用，
且 CI 分类 docs+workflows 变更时 required contexts 返回明确结果。

## 4. 技术考量

- 生成式 API 用例（`test-platform/tests/api-testing/generated/`）自包含：只读 `CAMELTV_BASE_URL` /
  `CAMELTV_AUTH_TOKEN` / `HTTP_PROXY` / `JUNIT_OUTPUT` / `JSON_OUTPUT`，可直接 `npx playwright test`。
- V1 server 路由 `envcheck/api_test/datafactory` 引用被删工具，需一并移除路由与注册；`cli/tp.py` 仅保留
  config/sites（工具命令全部移除）。
- `tp report ingest` 本地看板无生产价值 → 由 GitHub Actions artifact 承接 JUnit 报告；
  `tp logagg batch` → 脚本内 JUnit 解析 + ELK 链接输出（stdlib，无第三方依赖）。
- prod smoke 原 `--filter smoke` 与生成用例标题不匹配（空跑）→ 迁移为实际执行 6 个只读 spec。
