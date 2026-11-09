# Batch 277b-2 — 运维侧执行记录（P0-2 / P0-3 / P0-1 / P0-4 评估）

> **部门**：🟩 Dev + Ops
> **日期**：2026-11-09 22:00-22:30
> **执行方式**：SSH `root@111.230.155.116`（`~/.ssh/cameltv_tencent_lighthouse`）
> **生产**：swiftbugs.cn / 腾讯云广州 4C4G / Ubuntu 24.04

---

## 1. 已执行（真实生产操作）

### P0-2 备份恢复演练 ✅

| 项 | 值 |
|----|-----|
| 库 | `cameltv_production`（681 MB） |
| dump | `/root/backups/cameltv_production-20261109-221328.dump`（168 MB） |
| sha256 | `8f100def15b06cb7e53e4a2a1e35ff90bba065005c19bfd4afd2c43871f962ee` |
| 恢复 | scratch DB，`pg_restore rc=0`；10 张抽样表行数完全一致；scratch 已 DROP |
| 生产 alembic | `20260927_ai_guard_and_job_attempts` |

证据：`work-raw/p0-evidence/P0-2-backup-restore.json` + `raw/p0-2-backup-drill-20261109.log.txt`

### P0-3 磁盘清理 ✅（水位达标，48h 观察中）

| 项 | before | after |
|----|--------|-------|
| 根分区 | 87%（33G used / 5.1G avail） | **67%**（25G used / 13G avail） |
| Docker images | 18 个 / 15.95GB | 10 个 / 8.48GB |
| journal | 640.8M | 100M 上限（freed 572.9M） |

操作：删除 3 组旧 release 镜像 tag（20260919/24/1007，共 12 个，保留 `:main` 与运行中镜像）+ `journalctl --vacuum-size=100M`。
监控：`/etc/cron.d/p0-3-watermark` 每小时记录 `df -h /` 到 `/root/p0-3-watermark.log.txt`。

证据：`work-raw/p0-evidence/P0-3-disk-watermark.json` + `raw/p0-3-cleanup-20261109.log.txt`

---

## 2. 未完成（有明确阻塞）

### P0-1 Key 轮换 ❌

- 生产 `ai_provider` 3 条全部 **401**；env `AI_API_KEY` 未设置；
- 本地 3 个候选 Key + Agent 配置 Key 也全部 **401**；
- 未找到 DeepSeek 控制台账号凭据，无法自动创建新 Key。
- 详见 `work-raw/p0-evidence/P0-1-BLOCKED.md`。

### P0-4 `/uitest` 剥离 🟡

- 277b-1 契约已合入（PR #502）；
- 控制面 Chromium 还被 **蓝湖证据截图 / XHR 采集 / Playground** 使用，未迁移前不能删 Dockerfile；
- 生产 DB 仍停在 `20260927`，部署当前 main 会执行 **104 张表 DROP**（不可逆），需发布窗口 + 用户确认；
- 真实节点 E2E 未做。
- 详见 `work-raw/p0-evidence/P0-4-BLOCKED.md`。

---

## 3. 生产未变更项（明确声明）

- 未部署任何新镜像；未执行 `alembic upgrade`；
- 未改 `production.env`；未重启业务容器；
- 未删除数据库数据（仅 scratch DB 创建/删除）；
- 未触碰 PostgreSQL 数据卷。

---

## 4. 下一步

1. 用户提供有效 DeepSeek Key（或控制台账号）→ 完成 P0-1；
2. 2026-11-11 14:13Z 后复核 P0-3 水位日志 → 改 pass；
3. 发布窗口：确认 104 表 DROP → 部署 → P0-4 收口。
