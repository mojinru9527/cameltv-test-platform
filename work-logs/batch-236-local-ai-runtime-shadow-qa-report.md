# Batch 236 — 本地 AI Runtime 与 Shadow Mode（Phase 2）— QA 报告
> **QA (🔍)** | Date: 2026-09-13 | Verdict: PASS

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 7 | 7 | 0 | 0 |

## 可执行门禁

| 门禁 | 命令 | 退出码 | 结果 |
|------|------|--------|------|
| 后端全量 | `python -m pytest -q` | 0 | **2619 passed, 51 skipped, 1 xfailed**, 659.46s |
| 后端 F821 | `ruff check app/ --select F821` | 0 | All checks passed |
| Alembic 单头 | `python -m alembic heads` | 0 | `20260917_b236_ai_shadow_run (batch27) (head)` |
| SQLite 升级 | `DATABASE_URL=sqlite:///... alembic upgrade head` | 0 | 全链迁移成功，含 `ai_shadow_run` |
| 前端类型 | `npm run typecheck` | 0 | PASS |
| 前端 lint | `npm run lint` | 0 | PASS |
| 前端构建 | `npm run build` | 0 | 3671 modules transformed；9.29s |
| Dev Gate | `pwsh scripts/git/dev-gate.ps1` | 2 | `PASS_WITH_WARN`：HARD=0，G1/G2 PASS |
| WARN 审计 | `run-warn-audit.ps1 -NoTrendAppend` | 2 | Batch 236 新增文件无告警；剩余为 main 既有漂移 |

## 逐条件验证

### C1: Runtime 配置默认关闭且不泄露 Key
`test_runtime_status_does_not_expose_api_key` PASS。状态返回 `api_key_configured` 布尔值，不返回 Key。

### C2: Shadow 默认关闭与采样控制
`test_schedule_shadow_is_disabled_by_default`、`test_schedule_shadow_sample_rate_and_payload` PASS。默认不提交；采样 1.0 正确入队。

### C3: 主模型成功触发后台 Shadow
`test_primary_success_schedules_shadow` PASS。主响应保持同步返回，Shadow 调度仅携带结构化参数。

### C4: 对比结果结构化落库
`test_compare_outputs_records_structured_deltas`、`test_run_shadow_once_records_success` PASS。保存 JSON 合法性、hash、延迟、usage、长度差。

### C5: 本地失败不影响主链
`test_run_shadow_once_isolates_local_failure` PASS。本地异常记录 `failed`，主链结果不变。

### C6: Runtime health check
`test_local_runtime_health_check` PASS。可探测 `/models` 并校验目标模型存在性。

### C7: API 与路由基线
`test_runtime_and_shadow_api_are_published`、`test_route_inventory.py` PASS。三个新接口进入 OpenAPI、前端类型和路由基线。

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 1 | P2 | 同步函数新增 Shadow 参数后，async 路径漏传参数，定向测试 2 条失败 | 修复后 32/32 定向测试通过；全量 2619 passed | ✅ 已修复 |

## 发布建议

状态: **READY（本地门禁）**  
必修复: 0  
建议修复: 0  

下一步：等待用户一次总确认（推送 + Draft PR + required checks 通过后合入 main）。

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 本会话完成 | 0/0/1/0 | 1 | sync/async 路径分叉 | 共享签名变化后必须先跑双路径回归 |

**技能使用**: `cameltv-agent-team` → 工件与门禁；`cameltv-bug-guard` → 后台线程、Session、迁移边界核查。
