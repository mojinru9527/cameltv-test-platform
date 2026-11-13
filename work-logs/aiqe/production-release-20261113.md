# AIQE P1 生产发布（release-m13，2026-11-13）

> **发布内容**：main `268150486`（batch-336 ~ 339 / P1）
> **镜像**：`cameltv-tp-backend:release-m13-20261113`、`cameltv-tp-frontend:release-m13-20261113`
> **迁移**：无（`alembic current` = `20261123_ta033_mutation_ledger`，与发布前一致）
> **结果**：生产后端/前端 healthy，`https://swiftbugs.cn/api/v1/open/health` = 200

## 1. 发布前状态

| 项 | 值 |
|----|----|
| 后端镜像（`main`） | `dc9ed67fee6a`（release-m12） |
| 前端镜像（`main`） | `d752fc528977` |
| Alembic head | `20261123_ta033_mutation_ledger` |
| 数据库备份 | `/root/backups/pre-m13-20261113-123502.dump`（179M）sha256 `62cfcf2ba042360b9ecc7cb8c1141fa7968a7f90f29fbf3d0ecd4549407257e0` |
| 磁盘 | 83%（6.7G 可用） |

## 2. 镜像与发布

| 项 | 内容 |
|----|------|
| 后端镜像 | delta：`FROM release-m12-20261112` + COPY 最新 `app/`、`alembic/`、`alembic.ini` → `f1a366048351` |
| 前端镜像 | delta：`FROM cameltv-tp-frontend:main` + 替换 `dist` → `0be6d0d05467` |
| 回滚位 | `cameltv-tp-backend:prev-m13` = `dc9ed67fee6a`；`cameltv-tp-frontend:prev-m13` = `d752fc528977` |
| compose | `/opt/cameltv-tp/test-platform-v2/deploy/docker-compose.yml` + `docker-compose.override.yml`（`--env-file ../config/runtime/production.env`） |
| 服务 | backend / frontend 已重建；`aitde-worker` 见 §4 |

## 3. 发布后验证

| # | 项 | 结果 | 证据 |
|---|----|:----:|------|
| 1 | 公网 health | ✅ 200 | `https://swiftbugs.cn/api/v1/open/health` |
| 2 | 后端容器 | ✅ healthy | `cameltv-tp-production-backend-1 Up (healthy)` |
| 3 | 前端容器 | ✅ healthy | `cameltv-tp-production-frontend-1 Up (healthy)` |
| 4 | UI 构建物 | ✅ 新 bundle | `https://swiftbugs.cn/` index 引用 `index-fCMe3vQ_.js` |
| 5 | OpenAPI 新接口 | ✅ | `/api/v1/aiqe/platform-matrix`、`/api/v1/aiqe/workflows` 在 spec 中 |
| 6 | 菜单权限种子 | ✅ | `sys_permission.menu:aiqe_runs` 存在；`sys_role_permission` 已分配给 `tester`（admin 走 `*`） |
| 7 | 数据库迁移 | ✅ 无变化 | `alembic current` = `20261123_ta033_mutation_ledger` |
| 8 | 既有容器 | ✅ | postgres / runner healthy，运行时长未受影响 |

> 说明：生产 `ADMIN_PASSWORD`（env）与库内 admin 密码哈希不一致（登录返回 401），属既有环境事实；
> 生产侧本次以 OpenAPI + DB 种子 + UI 构建物验证，登录级 E2E 已在隔离 Test 实例完成（`work-logs/aiqe/test-deploy-20261113.md`）。

## 4. 发布中发现的遗留服务（已处置，待规划清理）

重建 `aitde-worker` 时使用新镜像启动失败：

```
ModuleNotFoundError: No module named 'app.modules'
```

原因：`aitde-worker` 的启动脚本仍执行 `python -m app.modules.aitde.workflow.gateway`，而 AITDE 模块已在平台简化批次删除；
该容器此前 5 周未重建，一直跑在旧镜像上，旧镜像已不可用（无同名 tag、无 dangling 镜像）。

处置：**已 `docker compose stop aitde-worker`**，不再崩溃重启；生产 API/前端不依赖该服务。
后续动作（M9/M10 规划）：从 compose 移除 `aitde-worker`/`aitde-temporal`，或按需重建为独立 Temporal Worker（非本批范围）。

## 5. 回滚

```bash
cd /opt/cameltv-tp/test-platform-v2/deploy
docker tag cameltv-tp-backend:prev-m13 cameltv-tp-backend:main
docker tag cameltv-tp-frontend:prev-m13 cameltv-tp-frontend:main
docker compose --env-file ../config/runtime/production.env \
  -f docker-compose.yml -f docker-compose.override.yml up -d --no-deps backend frontend
# 如需 DB 恢复：pg_restore -U <user> -d cameltv_production /root/backups/pre-m13-20261113-123502.dump
```

## 6. 版本锁

`config/aiqe-version.lock` 已更新：commit `268150486` / image `release-m13-20261113` / head `20261123_ta033_mutation_ledger`。
