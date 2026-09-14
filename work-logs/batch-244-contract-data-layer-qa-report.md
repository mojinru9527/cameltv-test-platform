# Batch 244 — QA Report
> **QA (🔍)** | Date: 2026-09-14 | Verdict: PASS

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 4 | 4 | 0 | 0 |

## 可执行门禁

| 检查 | 命令 | 结果 |
|------|------|------|
| Backend full | `pytest -q` | ✅ 2673 passed, 51 skipped, 1 xfailed in 641.32s |
| Query budget | `pytest -q tests/test_batch244_query_budget.py` | ✅ 3 passed |
| Backend targeted | dashboard/testplan/apitest/openapi/worker regression | ✅ 62 passed |
| Backend F821 | `ruff check app --select F821` | ✅ All checks passed |
| Frontend typecheck | `npm run typecheck` | ✅ |
| Frontend lint | `npm run lint` | ✅ |
| Frontend build | `npm run build` | ✅ 3671 modules transformed |
| Frontend full | `npm test -- --reporter=dot --maxWorkers=2` | ✅ 160 files / 700 tests passed |
| API contract/cache focused | `vitest api-contract + client-cache` | ✅ 9 passed |
| API/system/auth focused | `vitest src/api/__tests__ src/pages/system/__tests__ src/stores/__tests__/auth.test.ts` | ✅ 147 passed |
| G0 | `scripts/git/scan-common-bugs.ps1` | ✅ HARD=0 |
| G1/G2 | `scripts/git/dev-gate.ps1` | ✅ PASS_WITH_WARN（331 存量 WARN） |

## 逐条件验证

### C1: OpenAPI typed contract

- 新增 `src/api/apiContract.ts`，直接引用 `src/types/api.d.ts` 的 `components['schemas']`。
- Core API 已使用生成类型：LoginOut、PublicAccessOut、UserCreate/Update、RoleCreate/Update、TestCaseCreate/Update、Defect、Report 等别名。
- `src/types/index.ts` 的 LoginResult 改为生成 LoginOut，保留 UI 兼容类型。
- 证据：`test-platform-v2/frontend/src/api/__tests__/api-contract.test.ts`。

### C2: 生产 API `any` 清零

- 生产 `src/api/**/*.ts` 的 `any` 为 **0**。
- 生产 API 目录增加 ESLint `no-explicit-any: error` override。
- 错误 DTO 改为 `unknown`/`Record<string, unknown>`，Axios 扩展配置改为 `ApiRequestConfig`。

### C3: N+1 查询收敛

- OpenAPI confirm：一次预取 service endpoint map，循环内只做内存 upsert。
- 计划 add/ensure/auto-execute：TestCase 一次 `IN` 加载为 map，循环内不再 `db.get`。
- Dashboard：项目级 defect count 一次 GROUP BY；7 天趋势改为 2 个窗口查询 + 内存聚合。
- 证据：查询监听测试 `tests/test_batch244_query_budget.py`，最终 SQL 查询数由固定预算断言。

### C4: 缓存失效

- TestCase mutation 清空 `/test-cases` 前缀（domains/stats/taxonomy）。
- Environment variable mutation 清空 `/environments`。
- Role mutation 清空 `/system/menus`。
- cache key 继续包含 projectId，项目切换隔离不回归。
- 证据：`client-cache.test.ts` 新增 `/test-cases` 全前缀失效测试。

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 1 | P2 | Cross-project dashboard 的 per-project 卡片仍会按项目调用 `get_dashboard_stats`；项目数量很大时仍有线性查询增长 | `dashboard_service.get_cross_project_stats` | 记录为 C244-1；本轮已消除最重的 project×day 趋势 N+1 |
| 2 | P3 | 页面组件层仍有存量 `any` 和测试 act/NaN warning，不属于本批 API 层范围 | frontend full stderr | Phase4 治理 |

## 发布建议

状态：READY。  
合并前置：用户一次总确认、required checks 全绿、最终 `audit-ai-pr.ps1 -RequireSuccessfulChecks` 通过。

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 14h planned | 0/0/1/1 | 3 | 同名 contract 文件冲突、生成类型严格度、测试数据 identity map | 新入口命名先查同目录；类型迁移先读生成 schema 的 required/optional |

**技能使用**：`cameltv-agent-team`、`cameltv-bug-guard`、`karpathy-guidelines` → 契约/查询预算/最小改动。
