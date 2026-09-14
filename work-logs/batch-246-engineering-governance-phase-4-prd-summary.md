# Batch 246 — Engineering Governance & Required Checks

> **Product (🟦)** | Date: 2026-09-15 | Status: Approved for planning

## 1. 问题陈述

Phase 1–3 已把运行时安全、契约与 UI 体验补齐，但工程治理仍存在“观察不等于门禁”的问题：

1. `pr-check.yml` 的完整 Ruff/mypy 使用 `continue-on-error` 和 `|| echo`，失败会被标记为成功，不能阻止回归。
2. required frontend/backend jobs 只覆盖 F821、全量测试与构建，没有 axe、Lighthouse、生产依赖审计或完整静态分析 ratchet。
3. `lighthouse:a11y` 引用未声明的 `lhci`，且 `|| echo` 会把真实失败吞掉。
4. `npm audit` 存在 `js-yaml`、Vitest 以及若干开发/传递依赖漏洞；LHCI 自身新增的开发依赖也需要明确边界。
5. `C244-1` 的 cross-project dashboard 仍按项目循环调用统计和执行过滤，查询数随项目数线性增长。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 完整 Ruff findings | 773（中文歧义规则排除后） | 只减不增，新增即失败 | `quality_ratchet.py` |
| mypy findings | 186（mypy 2.3.1 基线） | 只减不增，新增即失败 | `quality_ratchet.py` |
| 后端依赖漏洞 | 未阻断 | `pip-audit` 0 known vulnerabilities | required backend job |
| 前端生产依赖漏洞 | 7 total（4 high/3 moderate） | `npm audit --omit=dev` 0 high/critical | required frontend job |
| Lighthouse accessibility | 脚本未安装/可吞错 | accessibility >= 0.9，失败阻断 | required frontend job |
| axe | 仅扩展 observation | required frontend job | required frontend job |
| Cross-project dashboard 查询 | 项目数线性 | 固定 5 个批量统计查询 + 固定趋势查询 | query budget test |
| `|| echo` 掩盖 CI 失败 | 存在 | 0 | 静态契约测试 |

## 3. 非目标（本次不做）

- 不要求一次性清零全部历史 Ruff/mypy findings；采用可追踪 ratchet，新增问题必须阻断。
- 不升级 React、Vite、Tailwind 等无关大版本依赖。
- 不把 LHCI 的开发依赖漏洞通过盲目 major override 掩盖；生产依赖必须 0，高风险开发工具漏洞记录为受控边界。
- 不改动 Phase 1 的安全头、Phase 2 的 typed contract 与 Phase 3 的 UI 入口。
- 不重构 Dashboard 返回字段或前端展示口径。

## 4. 用户故事 + 验收标准

### US-1 失败必须阻断
As a 发布负责人, I want CI 工具失败时 job 真实失败, so that “绿色”代表检查和审计都通过。
- 验收：required backend/frontend jobs 不含 `continue-on-error` 或 `|| echo` 掩盖新检查。
- 验收：Ruff/mypy 新增 finding、后端漏洞、前端生产 high/critical、axe/Lighthouse 失败都会使 required job 失败。

### US-2 历史债务可控下降
As a 维护者, I want 完整 Ruff/mypy 以精确 baseline ratchet 运行, so that 不因历史债阻塞正常开发，也不允许新增坏味道。
- 验收：baseline 按 file/code/message + occurrence count 记录。
- 验收：新增 occurrence 失败，删除 occurrence 不失败并显示可收口数量。

### US-3 前端供应链和可访问性可验证
As a 前端维护者, I want 一条命令运行 axe、Lighthouse 和生产依赖审计, so that 发布前不依赖手工判断。
- 验收：`npm run lighthouse:a11y` 自动启动 preview，不允许失败吞错。
- 验收：`npm audit --omit=dev --audit-level=high` 通过。
- 验收：`js-yaml`、Vitest/coverage 的直接/传递漏洞被修复。

### US-4 Dashboard 查询不随项目数增长
As a 平台管理员, I want cross-project dashboard 固定查询预算, so that 项目增多不会线性拖慢首页。
- 验收：per-project 卡片通过批量 GROUP BY 得到。
- 验收：2 个项目与 20 个项目的批量统计查询数相同。

## 5. 技术考量

- Ruff 保留完整 `E/F/B/UP/RUF` 配置；中文项目允许明确的 `RUF001-003` 例外。
- mypy 锁定 `2.3.1`，避免工具版本升级导致 baseline 漂移。
- Lighthouse 用 `.lighthouserc.json` 管配置，脚本不得用 shell fallback 吞错。
- 全量开发依赖审计仍可作为 observation；required 门禁聚焦生产依赖 0 high/critical。
- Dashboard 批量统计函数必须同时兼容 SQLite 和 PostgreSQL。

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 本地开发 | Dev/QA | ratchet、pytest、Vitest、axe、Lighthouse 全部通过 |
| PR required | 发布负责人 | 三个 required checks 全绿且无吞错 |
| 合并后 | 平台维护者 | main smoke + 每日观察继续运行 |

## 7. 技能使用

`cameltv-agent-team` → 六部门交付；`cameltv-bug-guard` → SQLAlchemy/查询与 CI 排障；`playwright-cli` → Lighthouse/axe 本地复现；`writing-plans` → 任务拆分与门禁验收。
