# Batch 251 — 生产验收证据（C250-1 修复）

> Date: 2026-09-17 | 分支：`fix/batch-251-migration-status-evidence`（commit `ebed7c96`）
> 目的：证明"成功发布也能在发布记录里看到迁移落点"

## Deployment

| 项 | 值 |
|----|----|
| Release | `release-20260917-0007` |
| Deployment id | `bfb6aad73bd947afb250edfa78dd553e` |
| State | `PRODUCTION_VERIFIED` |
| Git SHA（manifest） | `82aa9f4f…`（镜像内容 = -0006 的构建产物） |
| 控制面镜像 | `cameltv-release-console:release-20260917-3`（含本修复；`:release-20260917-2` 保留为回滚锚点） |
| 发布前备份 | `backup captured (7 kept)` |
| Runtime | split（api / runner / ai-gateway / frontend / aitde-worker） |

### 制品构成（服务器端复用 -0006 镜像生成，无重新构建）

| Part | RepoTags | config digest |
|---|---|---|
| backend | `cameltv-tp-backend:release-20260917-0007` | `sha256:7ff64bcf7f27…`（= -0006） |
| frontend | `cameltv-tp-frontend:release-20260917-0007` | `sha256:47d2f3b79b98…`（= -0006） |
| runner | `cameltv-tp-runner:release-20260917-0007` | `sha256:1be497fd93d7…`（= -0006） |
| ai-gateway | `cameltv-tp-ai-gateway:release-20260917-0007` | `sha256:3ab7ab754376…`（= -0006） |

execution config SHA-256：`7a612e43a5a8764d18b6411d1b9a74f7448a6a8eb5a4fa123f9485ac2151c77d`（同 -0006）。

## 核心证据：事件 reason 现在带迁移落点

修复前（`release-20260917-0006`）：

```
4 | PROD_OBSERVING | publish succeeded
```

修复后（`release-20260917-0007`，`GET /api/deployments/bfb6aad7…/events`）：

```
1 | DRAFT                | production deployment registered: release-20260917-0007
2 | VALIDATED            | manifest validated
3 | PROD_DEPLOYING       | publish started
4 | PROD_OBSERVING       | publish succeeded; migration target=20260922_ai_agent_token actual=20260922_ai_agent_token
```

`POST /verify` → `PRODUCTION_VERIFIED | production verified (health ok)`

## 生产验证

| # | 检查 | 结果 |
|---|------|------|
| 1 | 6 个容器 | 全部 `healthy` |
| 2 | DB `alembic_version` | `20260922_ai_agent_token`（= manifest target） |
| 3 | `GET /api/v1/open/health` | `{"code":0,…,"version":"2.3.0"}` |
| 4 | 前端 `https://swiftbugs.cn/` | 200 |
| 5 | 控制面 `https://release.swiftbugs.cn/` | 200；`/api/deployments` 无 token = 401 |
| 6 | 顺序 | 与 -0006 同路径：迁移 → 校验 → 停旧 → 起新（同一 `_activate` 命令序列） |

## 容量与回滚

- 为腾出容量：删除 `-0006` 的 4 个 tar（镜像保留）与两个历史控制面 tar → 8.68 GiB（门槛 8 GiB）。
- 回滚锚点：`cameltv-tp-*:release-20260917-0006` / `-0005` 及更早 release 镜像仍在服务器；
  控制面 `:release-20260917-2` / `:release-20260917` 亦保留（一条命令切回）。

## Findings

1. **[已修复] C250-1**：迁移状态改由执行器从**完整远端输出**解析并随 `ExecutorResult` 返回，
   事件 reason 不再受 4000 字符日志窗口影响（本次生产已实测带出 target/actual）。
2. **[观察] 失败路径未受影响且语义不变**：失败时状态行位于序列尾部，原有解析路径继续生效（单测覆盖）。
3. **[保持 Open] C248-8**：`--target runner` 本机仍不可构建；本次与 -0006 一样复用已验证镜像，
   差别是本轮**连 backend/frontend 也复用**（服务器端 retag），因此整轮验收没有任何本机构建。
