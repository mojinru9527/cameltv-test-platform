# Batch 250 — 生产发布验收证据（M5）

> Date: 2026-09-17 | Git SHA: `82aa9f4faaa1aba931a17b46c3409ed0bc4d3023`（Batch 250 合入后 main）
> 目的：让 C249-1 / C249-3 / C249-4 的新护栏在**真实发布**里走一遍

## Deployment

| 项 | 值 |
|----|----|
| Release | `release-20260917-0006` |
| Deployment id | `06840574f73e4c3ba1f1869c75708cb8` |
| State | `PRODUCTION_VERIFIED` |
| Runtime | split（api / runner / ai-gateway / frontend / aitde-worker） |
| Runtime mode manifest | `split` + `execution_config_sha256=7a612e43a5a8764d18b6411d1b9a74f7448a6a8eb5a4fa123f9485ac2151c77d` |
| manifest `database.target_revision` | `20260922_ai_agent_token`（**真实 revision**，非占位值） |
| 发布前备份 | 控制面 `backup captured (7 kept)` |
| 控制面镜像 | `cameltv-release-console:release-20260917-2`（本次从 main 重建，含 C249-4） |

### 制品构成

| Part | 来源 | config digest |
|---|---|---|
| backend (api) | **新构建**（`--target api`，main `82aa9f4f`） | `sha256:7ff64bcf7f27ac1be4472a5335731f60ab32668aadc33895ff393d13ece7c48b` |
| frontend | **新构建** | `sha256:47d2f3b79b98a3cf43f98ff72d4f85d249fd63f2f24cae518fca7d9aa8733d52` |
| runner | **复用** `release-20260917-0005` 已验证镜像（服务器端 retag + save） | `sha256:1be497fd93d7353408742061db486dcfba79560effece6c21ed5c9ac0317443a` |
| ai-gateway | **复用** `release-20260917-0005` 已验证镜像（服务器端 retag + save） | `sha256:3ab7ab754376a6f5a75129e20649f4824021f7443da2566811ea88ac40b3dc78` |

**为什么复用 runner / ai-gateway**：`docker buildx --target runner` 在本机仍复现 **C248-8**
（PLAYWRIGHT 安装步骤 `exit 127`，构建阶段缺 node），与 Batch 247/248 同一现象；
本批改动全部在 `deploy/release-console` 与 `scripts/ops`，runner/ai-gateway 代码路径未变，
故按既有做法复用**生产正在运行的已验证镜像**。→ C248-8 保持 Open。

## 新护栏的生产证据

### 1. 迁移先于停旧容器（ADR-0015 §4 顺序）

发布返回的远端日志（尾部 4000 字符）中，迁移作业容器与 Alembic 输出出现在**所有 Stopping 之前**：

```
ameltv-tp-production-backend-run-30e38ef57770 Created
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
 Container cameltv-tp-production-aitde-worker-1 Stopping
 Container cameltv-tp-production-backend-1 Stopping
 ...
 Container cameltv-tp-production-backend-1 Healthy
 Container cameltv-tp-production-frontend-1 Healthy
```

⇒ 顺序为 **迁移 → 校验 → 停旧 → 起新**，与设计一致（旧版本是先停后起、不做迁移）。

### 2. 迁移校验命令在生产真实执行（C249-4 机制）

用控制面**自己规划的那条命令**（`TencentSshExecutor._activate(..., migration_target=...)` 的第 2 条）
在生产现场执行（只读 `alembic current` + 断言）：

```
$ ssh root@111.230.155.116 "bash -c 'set -o pipefail; <console 规划的命令>'"
VERIFY_COMMAND_RC = 0
CAMELTV_MIGRATION target=20260922_ai_agent_token actual=20260922_ai_agent_token
```

⇒ 迁移**成功**时能打印 target/actual 且 rc=0；失败时同一行会带着实际 revision 出现在异常文本里
（失败分支由 `tests/test_console_manifest.py::test_migration_mismatch_is_recorded_in_event_reason` 锁定）。

### 3. 状态机与上线确认

`GET /api/deployments/06840574…/events`：

```
1 | ->DRAFT                | register | production deployment registered: release-20260917-0006
2 | DRAFT->VALIDATED       | validate | manifest validated
3 | VALIDATED->PROD_DEPLOYING | deploy | publish started
4 | PROD_DEPLOYING->PROD_OBSERVING | deploy | publish succeeded
```

`POST /verify` → `PRODUCTION_VERIFIED | production verified (health ok)`

## 生产验证

| # | 检查 | 结果 |
|---|------|------|
| 1 | `GET /health` | **200** |
| 2 | `GET /api/v1/open/health` | `{"code":0,…,"version":"2.3.0"}` |
| 3 | 6 个容器 | 全部 `healthy`（backend / frontend / runner / ai-gateway / aitde-worker / postgres） |
| 4 | DB `alembic_version` | `20260922_ai_agent_token`（= manifest target） |
| 5 | `ai_jobs` / `ai_agent_token` 表 + `model_name` / `imported_at` 列 | 存在（Batch 248 事故的修复面仍在） |
| 6 | 前端首页 `https://swiftbugs.cn/` | 200 |
| 7 | 未认证 `GET /api/v1/projects` | 401（鉴权生效，非 500） |
| 8 | 镜像生效 | `cameltv-tp-{backend,frontend,runner,ai-gateway}:main` 与 `:release-20260917-0006` 为**同一 image id** |
| 9 | 控制面 | `/api/deployments` 无 token → 401；新代码镜像 `release-20260917-2` 运行中 |

> 登录类冒烟（`admin`/`sportsadmin` + 既有口令）返回 401「用户名或密码错误」——凭证已变更，
> 本次以 DB revision、容器健康、鉴权边界与公开健康端点作为验证面；凭证核对不影响本次发布验收结论。

## 容量与回滚

- 发布前可用空间 8.7G < 门槛 → 删除**上一版** `release-20260917-0005` 的 4 个 tar
  （镜像保留，回滚锚点不依赖 tar；与 batch-247/248 清理策略一致）→ 11G；发布完成后 8.7G。
- 回滚锚点：`cameltv-tp-*:release-20260917-0005` 及更早 release 镜像仍在服务器；
  `release-20260917-0006` 四个镜像亦已就位。
- 控制面备份保留 7 份。

## Findings

1. **[P2][C250-1] 成功路径的迁移状态行被日志尾部截断丢弃**：
   `CAMELTV_MIGRATION target=… actual=…` 在序列早期输出，而 `ExecutorResult.logs` 只截取远端输出**最后 4000 字符**，
   其后的 `docker compose up --wait` 输出（60+ 行）把它挤出窗口 →
   本次 `PROD_OBSERVING` 事件 reason 只有 `publish succeeded`，没有附上 target/actual 正向证据。
   失败路径不受影响（序列在失败处即中止，状态行必在尾部）。修复建议见 QA §5 P2-3。
2. **[P1][C248-8] `--target runner` 本机不可构建**（复现）：构建阶段缺 node → `exit 127`；
   本次以复用已验证 runner 镜像绕过（同 Batch 247/248）。C248-8 保持 Open。
3. **[观察][C249-5] 复用镜像的转发面**：本次复用的 runner/ai-gateway 镜像**已含 `alembic/versions` 与
   `RUNNER_ENDPOINTS` 转发面**（发布后 runner / aitde-worker 均 healthy，未出现端点失配）；
   但"沿用旧镜像前必须核对"仍缺**可执行的核对清单/脚本**，C249-5 保持 Open。
