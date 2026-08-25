---
title: "旧环境（Vercel/Railway/Supabase）下线清单"
owner: "devops"
created: "2026-08-23"
status: "completed"
tags: ["production", "decommission", "vercel", "railway", "supabase", "tencent-migration"]
related: ["docs/ops/tencent-cloud-migration.md"]
---

# 旧环境（Vercel/Railway/Supabase）下线清单

> 2026-08-23 腾讯云迁移完成并稳定运行后，按本文逐步下线旧环境。
> **原则**：先确认新环境健康 → 数据/凭据备份 → 逐个下线 → 观察 → 删除。

## 0. 下线前置检查（每次执行前复核）

| # | 检查 | 期望 | 状态 |
|---|------|------|------|
| 0.1 | `https://swiftbugs.cn/api/v1/open/health` | 200 `status=ok` | ✅ 2026-08-23 |
| 0.2 | 三容器 healthy（backend/frontend/postgres） | healthy | ✅ 2026-08-23 |
| 0.3 | 发布控制台 `https://release.swiftbugs.cn/api/health` | `{"status":"ok"}` | ✅ 2026-08-23 |
| 0.4 | 最新备份存在（/opt/cameltv-backup/*.dump） | ≥1 份 | ✅ 20260823-011941 |
| 0.5 | 数据一致性抽查（用户/用例/计划计数） | 与迁移时一致 | ✅ 2026-08-22 |

> ⚠️ **下线前必须完成一次"近期真实发布"**（release.ps1 全链路），确认发布/回滚闭环无误。
> 2026-08-23 计划：D1（发布控制台真实发布演练）作为最后一道闸门。
> **D1 已完成（2026-08-25）**：发布→回滚→再发布→备份全链路演练通过，详见
> `docs/ops/tencent-cloud-migration.md` 附录 D5。

## 1. 下线顺序与步骤

### 1.1 Vercel 前端（最低风险，先下）

**保留观察原因**：暂无（Vercel 仅托管前端静态页，新前端已完全替代）。

- [ ] ① Vercel Dashboard → 项目 `cameltv-test-platform` → Settings → **Delete Project**
  - 部署域名 `cameltv-test-platform1.vercel.app` 随之失效
- [ ] ② 确认 DNS 无记录指向 vercel 域名（swiftbugs.cn 已全部指向 111.230.155.116）
- [x] ③ 仓库 `test-platform-v2/frontend/vercel.json` 已删除（本批清理，防误导）
- [ ] 观察 30 分钟后无异常 → 完成

### 1.2 Railway 后端（按量计费，尽快下）

**保留观察原因**：发布平台演练期间可能需回查后端日志/卷。

- [ ] ① Railway Dashboard → 项目 **keen-amazement** → 服务 **cameltv-test-platform**
- [ ] ② 到 **Volumes** 确认卷 `cameltv-test-platform-volume`（挂载 /app/storage）
  - 卷内容已在迁移时全量打包到腾讯云（`/tmp/railway-storage.tar.gz` + 服务器 `tp-artifacts` 卷）
- [ ] ③ 若需最后留证：`railway volume list` 截图 + 日志导出（无需保留数据）
- [ ] ④ Railway Dashboard → 项目 → **Settings → Delete Project**
  - ⚠️ Railway 按用量计费，下线后停止扣费
- [ ] ⑤ 确认本机 `railway.cmd` 登出或解绑（防误操作）
- [ ] 观察：新环境 24h 内无异常报错 → 完成

### 1.3 Supabase PG（数据已迁移，最后下）

**保留观察原因**：数据库 dump 外保留一份冗余（`F:\CamelTv-safe-backup\supabase-dump\` + 服务器备份）。

- [ ] ① Supabase Dashboard → 项目 `myhwdpjmxdsodqgeecpn`
- [ ] ② 复核迁移后数据：`sys_user=11, sys_project=5, test_case=13153, test_plan=16`（与 2026-08-22 一致）
- [ ] ③ Dashboard → Settings → **Delete Project**（或先 Transact 到 Free 保留）
- [ ] ④ 确认本地 dump 文件可读（`cameltv-prod.dump` 15.1MB）+ 服务器备份齐全
- [ ] 观察 → 完成

## 2. 下线后清理（仓库 + 本地）

- [x] `test-platform-v2/frontend/vercel.json`：已删除（本批清理，防误导）；`railway.json` 一并删除
- [x] 文档中旧地址批量归档（本批已更新）：
  - `docs/agent-team/staging-environment.md`（Vercel 作为 staging 替代 → 更新为 swiftbugs.cn 或标注退役）
  - `docs/生产级验收现状与体育平台承接规划.md`（旧架构表格 → 更新）
  - `docs/灰度放量SOP.md`（环境分层表 → test/prod 更新）
  - `test-platform-v2/README.md`（环境速览表）
  - `docs/DevOps基础设施操作手册.md`（退役横幅 + status=retired）
  - `docs/测试平台全功能验收文档-环境链接与账号汇总.md`、`docs/production-delivery/*`（历史标注）
- [ ] 本地 `F:\CamelTv-safe-backup\railway-link/`（链接凭据）删除（用户侧操作）
- [ ] migration-evidence（截图/报告）归档到 `docs/evidence/` 或保留本地（用户侧操作）

## 3. 回滚预案

| 场景 | 动作 |
|------|------|
| 新环境发布后异常 | 用发布控制台 `rollback` 切回上一镜像（无需旧环境） |
| 数据库需恢复 | 服务器备份 `/opt/cameltv-backup/cameltv-prod-*.dump` pg_restore |
| 意外删除数据 | `F:\CamelTv-safe-backup\supabase-dump\cameltv-prod.dump` 重导 |
| Railway 误删 | Railway 项目删除可申诉（30 天内）；**卷先确认已迁移** |

## 4. 执行登记

| 项 | 日期 | 执行人 | 备注 |
|----|------|--------|------|
| 前置检查 | 2026-08-23 | 用户 | ✅ 全部通过 |
| Vercel 删除 | 2026-08-23 | 用户 | ✅ 用户确认已下架（`cameltv-test-platform1.vercel.app` 已失效）；仓库 `vercel.json` 已删 |
| Railway 删除 | 2026-08-23 | 用户 | ✅ 用户确认已下架（`test-platform.up.railway.app` 已失效）；仓库 `railway.json` 已删 |
| Supabase 删除 | 2026-08-23 | 用户 | ✅ 用户确认已下架；数据已迁移本地 PG（备份见回滚预案 §3） |
| D1 发布演练 | 2026-08-25 | DSH | ✅ 全链路通过：发布 release-20260825-0001（PRODUCTION_VERIFIED）→ 回滚锚定版（PROD_ROLLED_BACK）→ 再发布（PRODUCTION_VERIFIED）→ 备份 cameltv-prod-20260825-020315.dump；期间修复发布控制台 5 处缺陷（#317/#320/#321），数据零丢失 |

## 5. 关联

- 迁移手册：`docs/ops/tencent-cloud-migration.md`（附录 A 执行记录）
- 发布控制台：`deploy/release-console/` + `release.swiftbugs.cn`
- 本地备份：`F:\CamelTv-safe-backup\`（dump/evidence/密钥）
