# Batch 277b-2 — 运维证据：QA Report

> **部门**：🔍 QA
> **日期**：2026-11-09
> **立场**：证据批次，门禁 = 证据可复核 + 不伪造 + 不越权。

---

## 1. 证据验收

| 项 | 验收 | 依据 |
|----|:----:|------|
| P0-2 JSON schema（status/checked_at/evidence） | ✅ | 守卫解析通过，`checked_at=2026-11-09`、5 项 evidence |
| P0-2 dump sha256 | ✅ | `8f100def15b06cb7e53e4a2a1e35ff90bba065005c19bfd4afd2c43871f962ee`（服务器 `sha256sum` 输出） |
| P0-2 恢复一致性 | ✅ | 10 张表 prod/restored 行数全等；`pg_restore rc=0`；scratch 已 DROP |
| P0-3 before/after | ✅ | 87% → 67%；docker images 15.95GB → 8.48GB；journal freed 572.9M |
| P0-3 状态诚实 | ✅ | `in_progress`（48h 未到），守卫按预期红 |
| P0-1 阻塞证据 | ✅ | 生产 3 条 provider + 本地 3 个 Key 全 401；env Key absent |
| P0-4 阻塞证据 | ✅ | Dockerfile 仍含 playwright；生产 alembic `20260927`；xhr/lanhu/playground 仍用浏览器 |
| 生产未变更声明 | ✅ | 未部署、未 upgrade、未改 env、未删业务数据 |

## 2. 守卫输出（本批合入后）

```text
P0-1 False（证据缺失，已文档说明 BLOCKED）
P0-2 True （checked_at=2026-11-09 evidence=5 项; upgrade() 内无裸 DROP）
P0-3 False（status=in_progress）
P0-4 False（Dockerfile 仍安装浏览器）
P0-5 True （0 残留; alembic heads=1）
GATE_RESULT=FAIL (3/5)
```

## 3. 风险

| 风险 | 说明 | 缓解 |
|------|------|------|
| 生产部署会触发 104 表 DROP | 生产 `alembic current=20260927` | 发布窗口 + 用户确认 + 已有 168MB dump |
| P0-3 48h 未满 | cron 每小时记录 | 2026-11-11 14:13Z 后复核并改 pass |
| P0-1 无 Key | 全部 401 | 用户提供新 Key / 控制台账号 |

## 4. 复盘卡

| 字段 | 内容 |
|------|------|
| 计划耗时 | 0.5 人日 / 实际 ≈ 40min（含生产操作） |
| 缺陷 | 0；无生产数据损失 |
| 返工次数 | 1（容器内脚本 `PYTHONPATH` 与执行用户权限） |
| 根因分类 | 运维环境差异（非 root 容器用户 / 无 PYTHONPATH） |

## 5. 判定

- 证据真实、可复核、未伪造；**建议 Leader APPROVED（证据批次）**；
- M0 仍有 3 项未绿，batch-279 不启动。
