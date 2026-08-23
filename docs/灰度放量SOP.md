# 分环境灰度放量 SOP（C90-2 / batch-18-C14）

> 归属：发布运维 | 状态：生效 | 最后更新：2026-08-05（Batch 91）

## 1. 目的

规范测试平台的**分环境发布 / 灰度放量 / 回滚**流程，避免直接上生产、无灰度窗口、回滚不可逆等风险。

## 2. 环境分层

| 环境 | 用途 | 数据 | 入口 | 发布方式 |
|------|------|------|------|---------|
| dev（本地 worktree） | 开发/验收 | 独立 SQLite | localhost 端口（每任务独立） | 不发布 |
| test（staging 替代） | 内部联调/发布前验证 | 生产同构 PostgreSQL（本地/测试实例） | `https://swiftbugs.cn`（生产）或本地实例 | PR 合入后按发布火车部署 |
| staging（如启用） | 发布前验证 | staging 库 | 独立域名/实例 | 手动触发 |
| prod | 对外生产 | 本机 PostgreSQL（容器卷 `pg-data`） | `https://swiftbugs.cn`（Caddy→Nginx→FastAPI→PostgreSQL） | **灰度放量** |

> 2026-08-22 起生产迁移至腾讯云广州单机（`swiftbugs.cn`，ICP 粤ICP备2026121122号-1）；
> 旧 Vercel（前端）+ Railway（后端 `/api` 反代）+ Supabase 已下线；staging 未单独启用时，test 承担预发布验证。

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
  → 构建前端/后端镜像（本机构建 docker save/load 或服务器可用网络时 compose build）
  → 腾讯云服务器部署（docker compose up -d --build；Caddy 自动 HTTPS）
  → 冒烟 https://swiftbugs.cn/api/v1/open/health 200
  → 灰度观察窗口（默认 30 分钟）：
      1. 冒烟：登录 / 工作台 / 关键链路（用例→计划→执行→报告）
      2. 监控：容器日志无 5xx 峰值、无 console 报错（docker compose logs）
      3. 数据：无异常写入/回滚请求
  → 灰度通过：宣布完成，登记交付清单
```

**灰度比例建议**（如需分流量）：首日 10% → 次日 50% → 观察 24h → 全量。当前单实例架构下以「观察窗口」代替流量切分；启用多实例后按此节奏执行。

## 5. 回滚

- **前端/后端**：腾讯云服务器回滚到上一镜像或上一代码版本（`git revert` 后重新构建镜像）；Caddy 可临时指向旧部署。
- **数据**：灰度期禁止破坏性 DDL；需要迁移时先备份、演练 upgrade/downgrade 双向（batch-18-C7/C21-P1-5 要求的 staging 演练）。迁移前保留 `cameltv-prod-<date>.dump`（`pg_dump -Fc`），必要时整库重导。
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
| 前端发布 | 腾讯云服务器镜像构建/部署（Caddy + Nginx 容器） |
| 后端发布 | 腾讯云服务器 `docker compose up -d --build`（含 Alembic 迁移） |
| 灰度观察与回滚决策 | 运维/测试负责人 |
| 回滚执行 | 运维（服务器镜像/代码回退 + `pg_restore` 数据回滚） |
