---
title: "生产备份恢复演练手册（PostgreSQL）"
owner: "qa-team"
created: "2026-09-19"
last_reviewed: "2026-09-19"
status: "active"
expires: "2027-03-19"
tags: ["ops", "backup", "restore", "drill", "postgresql", "tencent-cloud"]
related:
  - "docs/ops/tencent-cloud-migration.md"
  - "docs/platform-refactor/09-platform-landing-plan.md"
  - "docs/platform-refactor/10-landing-plan-task-backlog.md"
---

# 生产备份恢复演练手册（PostgreSQL）

> **存在的理由**：09 方案 §5.2 与验收清单第 ⑨ 条都要求「按 `docs/ops/restore-drill.md` 复演一次」。
> 本文在 2026-09-19 首次演练后补写——此前**该文档不存在**（B0-3 交付物缺失），
> 因此当时的"恢复演练"是临时脚本，不是"照文档复演"。本文把那次演练固化成可重复流程。

## 1. 环境事实（2026-09-19 实测）

| 项 | 值 |
|---|---|
| 生产主机 | `111.230.155.116`（腾讯云广州轻量，Ubuntu 24.04 / 4C4G，hostname `VM-0-7-ubuntu`） |
| 访问方式 | `ssh -i ~/.ssh/cameltv_tencent_lighthouse root@111.230.155.116`（**root**；`ubuntu`/`lighthouse` 用户会被拒） |
| 数据库 | 容器 `cameltv-tp-production-postgres-1`，`POSTGRES_USER=cameltv`，`POSTGRES_DB=cameltv_production` |
| 备份目录 | 主机 `/opt/cameltv-backup/`（`-Fc` 自定义格式 `.dump`，单份约 57–67MB） |
| 生产应用栈 | `cameltv-tp-production-{postgres,backend,frontend,runner,ai-gateway,aitde-worker}-1` + `release-console` + `aitde-temporal` |

> ⚠️ **密钥被安全软件锁过的历史**：`~/.ssh/cameltv_tencent_lighthouse` 曾被火绒驱动级文件保护锁死（连属主 `takeown`/`icacls` 均 Access denied，当时靠临时退出防护解决）。
> 建议把 `ssh.exe` 或 `.ssh` 目录加入白名单；**不要**为了让脚本跑通而长期关闭防护。

## 2. 演练步骤（15 分钟内可完成；实测 20 秒）

前提：已 `ssh` 上生产。**全部操作只在临时库上进行，绝不触碰 `cameltv_production`。**

```bash
set -uo pipefail
PG=cameltv-tp-production-postgres-1
DUMP=/opt/cameltv-backup/cameltv-prod-<日期>-<时间>.dump   # 取 ls -t 里最新的一份
DRILL=restore_drill_$(date +%Y%m%d_%H%M%S)

# 1) 建临时库
docker exec $PG psql -U cameltv -d postgres -qAtc "CREATE DATABASE $DRILL;"

# 2) 恢复（用 stdin 灌入，避免把 dump 拷进容器）
docker exec -i $PG pg_restore -U cameltv -d $DRILL --no-owner --no-privileges < $DUMP

# 3) 抽查（表数 / 迁移版本 / 执行记录抽样）
docker exec $PG psql -U cameltv -d $DRILL -qAtc \
  "select count(*) from information_schema.tables where table_schema='public'"
docker exec $PG psql -U cameltv -d $DRILL -qAtc "select version_num from alembic_version"
docker exec $PG psql -U cameltv -d $DRILL -qAtc "select count(*) from test_execution"
docker exec $PG psql -U cameltv -d $DRILL -qAtc \
  "select id||' | '||status||' | '||coalesce(executed_at::text,'-') from test_execution order by id desc limit 3"

# 4) 清理（必做；否则临时库会长期占盘）
docker exec $PG psql -U cameltv -d postgres -qAtc "DROP DATABASE $DRILL;"
```

## 3. 2026-09-19 演练证据（首次留档）

```
dump    : /opt/cameltv-backup/cameltv-prod-20260917-145752.dump   67M   (mtime 2026-09-17 22:58)
drill_db: restore_drill_20260919_131847

public 表数            = 197
alembic 版本           = 20260922_ai_agent_token
test_execution 行数    = 137642
最近 3 条执行记录      = 137650 | failed | 2026-09-17 04:00:00.552398
                         137649 | failed | 2026-09-17 04:00:00.552398
                         137648 | failed | 2026-09-17 04:00:00.552398
临时库 DROP            = 成功
演练耗时               = 20 秒        ← 远低于 DoD「2h 内完成」
```

**结论**：备份可用，能从 dump 完整恢复到可查询状态并抽查到真实执行记录。

## 4. 本次演练暴露的三个缺口（需处理，勿当作"通过"）

| # | 缺口 | 证据 | 处理建议 |
|---|------|------|---------|
| G1 | **生产库落后于主干**：`execution_jobs`(B1)、`impact_edge`(B3) 在生产库中**不存在**，`alembic_version` 停在 `20260922_ai_agent_token`（主干为 `20260926_...`） | 演练抽查中两表查询返回 "不存在" | 随下一次发布火车执行 `alembic upgrade head`；B1/B3/B4 迁移尚未上生产 |
| G2 | **备份节奏不满足"每日"**：最新 dump 为 09-17 22:58，而演练日是 09-19；`crontab -l` 无备份任务 | `ls -lh /opt/cameltv-backup/` 与 `crontab -l` | 确认备份是人工/发布控制台触发还是已掉；若要求每日，需固化定时任务（与 B0-2 一并处理） |
| G3 | **无磁盘水位告警**：`df -h` 当前 73%（达标），但 crontab 中不存在任何 85% 阈值告警 | `df --output=pcent /` = 73%；`crontab -l` 仅腾讯云 stargate + 系统任务 | 落 B0-2「磁盘与容量告警固化」 |

## 5. 复演频率与判定

- **频率**：方案 §5.2 要求「每周恢复演练」；本手册可整段复制执行（不需要额外脚本）。
- **通过判定**：① 临时库建成功；② `pg_restore` 无致命错误；③ `alembic_version` 可读；④ 能抽查到执行记录；⑤ 临时库已 DROP。
- **失败处置**：若 dump 损坏或恢复失败，**先保留现场**（不要 DROP 临时库），再按 `docs/ops/tencent-cloud-migration.md` 的发布/回滚章节处理，并把失败样本留证。
