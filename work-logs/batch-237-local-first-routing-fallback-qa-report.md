# Batch 237 — 本地优先路由与云端兜底（Phase 3）— QA 报告
> **QA (🔍)** | Date: 2026-09-13 | Verdict: PASS

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 7 | 7 | 0 | 0 |

## 可执行门禁

| 门禁 | 命令 | 退出码 | 结果 |
|------|------|--------|------|
| 后端全量 | `python -m pytest -q` | 0 | **2628 passed, 51 skipped, 1 xfailed**, 691.67s |
| 后端 F821 | `ruff check app/ --select F821` | 0 | All checks passed |
| Alembic 单头 | `python -m alembic heads` | 0 | `20260917_b236_ai_shadow_run (batch27) (head)` |
| 前端类型 | `npm run typecheck` | 0 | PASS |
| 前端 lint | `npm run lint` | 0 | PASS |
| 前端构建 | `npm run build` | 0 | 3671 modules transformed；10.89s |
| Dev Gate | `pwsh scripts/git/dev-gate.ps1` | 2 | `PASS_WITH_WARN`：HARD=0，G1/G2 PASS |
| WARN 审计 | `run-warn-audit.ps1 -NoTrendAppend` | 2 | Batch 237 新增文件无告警；剩余为 main 既有漂移 |

## 逐条件验证

### C1: cloud_only 默认行为不变
`test_build_route_cloud_only_has_no_shadow_or_fallback` PASS。默认路由仍是云端，无 fallback/shadow。

### C2: shadow 模式使用本地观察对端
`test_build_route_shadow_uses_local_as_observation` PASS。云端主调用，local 只作为 shadow。

### C3: local_preferred 路由计划
`test_build_route_local_preferred_has_cloud_fallback`、`test_local_preferred_uses_local_primary` PASS。local 主调用，cloud 作为 fallback/shadow。

### C4: 本地失败自动云端兜底
`test_local_preferred_falls_back_to_cloud`、`test_async_local_preferred_falls_back_to_cloud` PASS。sync/async 都返回云端结果并标注 `route_status=fallback`。

### C5: local_only 安全失败
`test_build_route_local_only_requires_local_runtime` PASS。无本地配置直接抛错，不暗中回云。

### C6: Shadow 证据转策略建议
`test_shadow_policy_recommends_local_preferred_when_evidence_passes` PASS。返回 recommendation、样本率、JSON 合法率、一致率、延迟差；不自动改配置。

### C7: API 与路由基线
`test_runtime_and_shadow_api_are_published`、`test_route_inventory.py` PASS。`/ai-config/shadow-policy` 已进入 OpenAPI、前端类型和路由基线。

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 1 | P2 | 路由改造初期 cloud_only 下 shadow 仍可能被调度 | 修复为 RoutePlan 显式提供 `shadow_config`；覆盖策略测试通过 | ✅ 已修复 |

## 发布建议

状态: **READY（本地门禁）**  
必修复: 0  
建议修复: 0  

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 本会话完成 | 0/0/1/0 | 1 | shadow 对端隐式耦合 | 路由与 shadow 必须通过同一 RoutePlan 传递 |

**技能使用**: `cameltv-agent-team` → 工件与门禁；`cameltv-bug-guard` → sync/async、fallback、缓存边界核查。
