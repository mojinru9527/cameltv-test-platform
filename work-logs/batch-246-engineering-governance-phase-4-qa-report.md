# Batch 246 — QA 报告

> **QA (🔍)** | Date: 2026-09-15 | Verdict: PASS（本地；最终由 PR required checks + 用户总确认封口）

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 2（C243-4 / C244-1） | 2 | 0 | 0 |

## 可执行门禁

| 检查 | 命令 | 退出码 | 结果 |
|------|------|:------:|------|
| 后端全量 | `python -m pytest -q` | 0 | 2678 passed / 51 skipped / 1 xfailed |
| 前端 clean install | `npm ci` | 0 | 850 packages |
| 前端类型 | `npm run typecheck` | 0 | PASS |
| 前端 lint | `npm run lint` | 0 | PASS（`--max-warnings=0`） |
| 前端全量 | `npm test` + `npm run test:coverage` | 0 | 164 files / 710 tests；Stmts 40.91% |
| 前端构建 | `npm run build` | 0 | PASS |
| Ruff/mypy ratchet | `python scripts/ci/quality_ratchet.py` | 0 | Ruff baseline/current 768/768；mypy 193/193；new=0 |
| 后端依赖审计 | `pip-audit -r requirements.txt` | 0 | No known vulnerabilities |
| 前端生产依赖审计 | `npm audit --omit=dev --audit-level=high` | 0 | 0 vulnerabilities |
| 完整 npm audit ratchet | `node scripts/ci/npm_audit_ratchet.mjs` | 0 | baseline/current 16 keys，new=0；当前 2 low / 1 moderate / 7 high / 0 critical dev-only |
| axe required | `npm run test:a11y:ci` | 0 | 28 passed，无 axe violations |
| Lighthouse required | `npm run lighthouse:a11y` | 0 | accessibility assertion >= 0.9 通过 |
| CI 契约 | `python scripts/ci/test_batch59_quality_contracts.py` | 0 | 10 passed |
| CI 范围分类契约 | `python scripts/ci/test_classify_ci_changes.py` | 0 | 10 passed |
| 工作流 YAML | Python `yaml.safe_load` 全量解析 | 0 | PASS |
| G0–G2 | `pwsh scripts/git/dev-gate.ps1 -RepositoryPath (Get-Location).Path` | 2 | `PASS_WITH_WARN`；HARD=0，WARN=330；新增 ratchet/audit 全绿 |

> `dev-gate` 的 WARN 330 为仓库既有机械扫描基线，不是本批新增缺陷；本轮新增的 Ruff/mypy ratchet 与依赖审计均无新增问题。

## CI 首轮修复记录

- 首轮 `后端全新检出与全量回归` 在 Linux mypy 上额外报告 `openvpn_service.py` 的 3 类 Windows API（`CREATE_NO_WINDOW` / `WINFUNCTYPE` / `WinDLL`，共 6 occurrence）。
- 修复：mypy baseline 改为平台分片，Windows 基线 193，Linux 基线 199；Ruff baseline 保持共享。
- 本地复验：Windows ratchet PASS，Linux baseline 选择逻辑 PASS；新提交必须重新跑 required checks。
- 前端 required job 首轮已通过。

## 逐条件验证

### C243-4：required checks 工程治理
**变更文件**:
- `scripts/ci/quality_ratchet.py`
- `scripts/ci/npm_audit_ratchet.mjs`
- `.github/workflows/main-quality-gate.yml`
- `.github/workflows/pr-check.yml`
- `.github/workflows/main-merge-smoke.yml`
- `test-platform-v2/frontend/.lighthouserc.json`

| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 完整 Ruff/mypy ratchet | ✅ | 按 file/code/message + occurrence count，禁止新增 |
| required backend 集成 | ✅ | F821 + ratchet + `pip-audit` 均在 required backend job |
| required frontend 集成 | ✅ | production audit + full npm ratchet + axe + Lighthouse 均在 required frontend job |
| 禁止 `|| echo` | ✅ | Lighthouse/pr-check 静态分析与审计步骤 fail closed |
| axe/PW 稳定性 | ✅ | required suite 使用 route stub/guest 页面；真实后端 theme suite 独立为 `test:a11y:full` |
| Lighthouse | ✅ | 自动启动 preview，accessibility >= 0.9 |
| production 依赖 | ✅ | 前后端均为 0 known vulnerabilities |
| 现有 dev advisories | ✅ | LHCI dev-chain 由 baseline ratchet 记录，新增即失败；C246-1 跟踪上游清理 |

### C244-1：Cross-project dashboard 聚合
**变更文件**:
- `test-platform-v2/backend/app/services/statistics_service.py`
- `test-platform-v2/backend/app/services/dashboard_service.py`
- `test-platform-v2/backend/tests/test_batch244_query_budget.py`

| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 批量项目统计 | ✅ | `get_projects_statistics` 固定 5 个 GROUP BY 查询 |
| 项目数独立性 | ✅ | 20 个项目仍固定 5 查询；测试通过 |
| cross-project 汇总 | ✅ | 不再循环调用 `get_dashboard_stats` / `_execution_filter_for_project` |
| 剩余固定查询 | ✅ | 缺陷计数 1 + 趋势 2；总预算不随项目数增长 |
| 返回契约 | ✅ | Batch 59 管理验收 5/5、查询预算 4/4 通过 |

## 代码实现逻辑审计

- `quality_ratchet.py` 使用工具固定版本（ruff 0.15.22 / mypy 2.3.1）和精确 baseline，新增 finding 会 fail；历史 finding 删除不会造成假失败。
- `npm_audit_ratchet.mjs` 直接运行完整 `npm audit --json`，按包/严重级/advisory identity 做 baseline；生产依赖仍单独执行 0 漏洞硬门禁。
- required frontend 不再运行依赖真实后端的五主题套件；`test:a11y:ci` 使用稳定 fixture 套件，`test:a11y:full` 保留需要后端的扩展验收。
- `statistics_service.get_projects_statistics` 使用聚合 SQL，且仍保持 `is_deleted=False`/status/时间筛选口径。
- CI 分类器未改；scope skip 仍走原固定 required job 名称，不新增易漏配置的 job context。

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|:------:|------|------|------|
| 1 | P2 | LHCI dev chain 仍有 7 high / 1 moderate / 2 low advisories，生产依赖为 0 | `npm-audit-all.json`，full ratchet new=0 | Tracked as C246-1 |
| 2 | P3 | `test:a11y:full` 仍需真实后端，不能作为无依赖 required suite | required 拆分为 `test:a11y:ci` 后通过；full 保留手动入口 | 可接受 |
| 3 | P3 | dev-gate 仍有 330 个历史 WARN | `dev-gate.log`；HARD=0，新增门禁全绿 | 后续 ratchet |

## 发布建议

状态: READY（本地门禁通过）
必修复: 0
建议修复: 1（C246-1：清理 LHCI dev-only advisories）

## 复盘卡（Batch 75 起强制）

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 8h 计划 / 约 7h 实际 | 0/0/1/2 | 2 | required a11y 与真实后端耦合；静态分析基线需 line-independent | required 测试必须使用无外部依赖 fixture；ratchet key 不含行号 |

**技能使用**:
- `cameltv-agent-team` → Product/PM/Design/Dev/QA 工件
- `cameltv-bug-guard` → SQLAlchemy 聚合、测试夹具和 CI 排障
- `playwright-cli` → axe/Lighthouse 稳定套件验证
