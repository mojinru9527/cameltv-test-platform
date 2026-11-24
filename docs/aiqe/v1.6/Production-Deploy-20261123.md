# V1.6 生产部署记录（2026-11-23）

> **STATUS: HISTORICAL** — 本文记录 2026-11-2x 当时的执行事实与结论；其中 PASS/VERIFIED 等表述不代表当前发布判定。当前状态以 `release-verdict.json`、`E2E-Coverage-and-Blockers.md` 与 `governance/production-evidence.json` 为准。


## 部署内容

- 生产地址：`https://swiftbugs.cn`
- 服务器：腾讯云广州单机
- 后端镜像：`cameltv-tp-backend:v16-api`
- 前端镜像：`cameltv-tp-frontend:v16`
- 后端容器：`cameltv-tp-production-backend-v16`
- 前端容器：`cameltv-tp-production-frontend-v16`

## 数据库

- 部署前备份：
  `/opt/cameltv-backup/pre-v16-20261123-182320.dump`（197 MB）
- 迁移前 revision：`20261124_aiqe_pr595_execution`
- 迁移后 revision：`20261122_v16_catalog_post_merge (head)`
- 迁移包含：
  - AUD-007 boolean 修复
  - policy_status 表名修复
  - v1.6 catalog/AUD merge + 线性 post-merge revision

## 回滚

旧容器保留且已停止：

- `cameltv-tp-production-backend-1-v15-rollback`
- `cameltv-tp-production-frontend-1-v15-rollback`

回滚方式：停止新容器，重命名/启动旧容器，恢复旧镜像；数据库按备份 dump 恢复（仅在迁移不可前向修复时使用）。

## 验证

- `GET https://swiftbugs.cn/` → 200，title `CamelTv 测试平台`
- `GET https://swiftbugs.cn/api/v1/open/health` → 200
- 后端容器 Up
- 前端容器 Up
- 生产 DB revision = `20261122_v16_catalog_post_merge`

## 运维债务

当前后端容器通过两个运行时补丁启动：

1. `/opt/aiqe-v16-deps` 挂载提供 `sqlglot`；
2. 最新迁移文件在容器创建后复制到 `/app/alembic/versions`。

功能已验证；后续重建镜像时必须把 `sqlglot` 和迁移文件固化进镜像，否则容器重建可能失败。
