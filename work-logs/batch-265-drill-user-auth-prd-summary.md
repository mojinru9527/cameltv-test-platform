# Batch 265 PRD-lite — 演练驱动改用用户凭据（修 C264-3）

> **Product/PM** | Date: 2026-09-19 | 档位：**轻量批次**
> `mode: light`
> 豁免理由：只改 **QA 驱动脚本**（`test-platform-v2/backend/scripts/drill_three_versions.py`）的鉴权参数选择 + 输出目录健壮性，不改平台运行时行为、不加接口/配置/依赖、不动 Schema 与权限模型（`pipeline-modes.md` §1：内部流程工具）。
> 非目标：不改 `POST /api/v1/execution-jobs` 的权限模型（那是平台行为变更，需完整批次）；不引入任何被测系统凭据。

## 1. 问题（Batch 264 发现，已登记 C264-3 / P1）

`drill_three_versions.py` 用**节点令牌**发 `X-AI-Agent-Token` 调 `POST /api/v1/execution-jobs`，
而该端点依赖 `require_permission("execution:manage")` —— **只认用户 JWT**，因此必然 401：

```
预检 6/6 全绿 → run_versions → 401 Unauthorized (POST /api/v1/execution-jobs)
对照：同库改用用户 JWT + X-Project-Id → 立刻 200，节点认领并执行
```

结论：**第 ⑦ 条无论环境多完整都跑不通**，这是驱动缺陷而不是环境问题。

## 2. 本次修复

1. 新增 `--user-token <JWT>`；或 `--username/--password` 由脚本现登录取 JWT；
2. 登记/查询任务/校验证据统一改用 `Authorization: Bearer <JWT>` + `X-Project-Id`；
3. 缺少用户凭据时**明确报错**（提示节点令牌不能用于登记），不再静默 401；
4. `--node-token` 保留参数以兼容旧命令行，但**不再用于任何 HTTP 请求**，并在 `--help` 说明；
5. 顺带修 `--out` 指向不存在目录时崩溃（实跑命中）。

## 3. 实跑证据（本机真实执行，非模拟）

| 运行 | 结果 |
|---|---|
| `--versions 1`（探路） | `[version 16.1] jobs=[2,3] evidence_complete=True` |
| `--versions 3`（验收本体） | `16.1 / 16.2 / 16.3` 三版全跑通，`evidence_complete=True`；报告 `evidence/batch-265/drill-three-versions.json` |
| SLO 判定 | `plan_within_2h ✓ · execution_within_3h ✓ · evidence_complete ✓ · reuse_hit_rate_50pct ✗（未提供复用数）` → `meets_all=false` |

环境：本机平台（uvicorn@8123 + SQLite 试点库）+ 本机 `cameltv-node`（在线）+ 真实 Test5 入口
（`http://camel-api-gateway05.svc.elelive.cn/camel-service`）。

## 4. 验收判据

| # | 判据 |
|---|------|
| A1 | 回归测试 3 例通过（用户令牌→Bearer 头；仅节点令牌→明确报错；调用点不再用 agent 头） |
| A2 | 修复后 `--versions 3` 实跑完成，3 个版本证据完整（不再 401） |
| A3 | 未改平台端点权限、未引入凭据到仓库 |
| A4 | 门禁：ruff F821、相关 pytest、scan-common-bugs、audit-cconditions |
