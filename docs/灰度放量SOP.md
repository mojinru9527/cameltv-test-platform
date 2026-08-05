# 分环境灰度放量 SOP（C90-2 / batch-18-C14）

> 归属：发布运维 | 状态：生效 | 最后更新：2026-08-05（Batch 91）

## 1. 目的

规范测试平台的**分环境发布 / 灰度放量 / 回滚**流程，避免直接上生产、无灰度窗口、回滚不可逆等风险。

## 2. 环境分层

| 环境 | 用途 | 数据 | 入口 | 发布方式 |
|------|------|------|------|---------|
| dev（本地 worktree） | 开发/验收 | 独立 SQLite | localhost 端口（每任务独立） | 不发布 |
| test | 内部联调 | 测试库 | Vercel Preview + Railway test 实例 | PR 合入后自动 |
| staging（如启用） | 发布前验证 | staging 库 | 独立域名/实例 | 手动触发 |
| prod | 对外生产 | Supabase PG | `cameltv-test-platform1.vercel.app` + Railway | **灰度放量** |

> 当前仓库以 Vercel（前端）+ Railway（后端 `/api` 反代）承载；staging 未单独启用时，test 承担预发布验证。

## 3. 发布前置检查（每次必做）

- [ ] `audit-ai-pr.ps1 -RequireSuccessfulChecks` 通过（分支/文件/凭据策略）
- [ ] `audit-cconditions.ps1` 0 硬错（C 条件口径）
- [ ] 前端 `npm run typecheck && npm run build`、后端 `pytest` 全量、`scan-common-bugs` HARD=0
- [ ] 生产环境 Secret 完整（production.env 无占位符，C58-04）
- [ ] 变更范围与上一版 diff 已确认（`git log origin/main..HEAD`）

## 4. 灰度放量节奏

```text
PR 合入 main
  → CI 全绿（required checks）
  → Vercel 自动部署前端（Preview → Production）
  → 后端 Railway 部署（health /api/v1/open/health 200）
  → 灰度观察窗口（默认 30 分钟）：
      1. 冒烟：登录 / 工作台 / 关键链路（用例→计划→执行→报告）
      2. 监控：Vercel/Railway 日志无 5xx 峰值、无 console 报错
      3. 数据：无异常写入/回滚请求
  → 灰度通过：宣布完成，登记交付清单
```

**灰度比例建议**（如需分流量）：首日 10% → 次日 50% → 观察 24h → 全量。当前单实例架构下以「观察窗口」代替流量切分；启用多实例后按此节奏执行。

## 5. 回滚

- **前端**：Vercel 回滚到上一 Production Deployment（1 键）。
- **后端**：Railway 回滚到上一部署版本；若涉及迁移，先执行 `alembic downgrade <target>`（禁止 `downgrade -1` 相对回退，见 runbook）。
- **数据**：灰度期禁止破坏性 DDL；需要迁移时先备份、演练 upgrade/downgrade 双向（batch-18-C7/C21-P1-5 要求的 staging 演练）。
- 回滚后 24h 内复盘，登记缺陷并转下批修复。

## 6. 检查清单（发布后 24h）

- [ ] 公开入口 200（登录页 + `/api/v1/open/health`）
- [ ] 关键用户路径冒烟通过（真实浏览器）
- [ ] 无新增 WARN 类别（`run-warn-audit.ps1`）
- [ ] 审计日志正常（无异常权限变更）

## 7. 责任矩阵

| 动作 | 负责 |
|------|------|
| PR 合并与 checks | Agent Team Leader + CI |
| 前端发布 | Vercel（自动） |
| 后端发布 | Railway（自动/手动触发） |
| 灰度观察与回滚决策 | 运维/测试负责人 |
| 回滚执行 | 运维（Vercel/Railway 控制台） |
