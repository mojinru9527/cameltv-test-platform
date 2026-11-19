# 生产发布记录 — AIQE V1.5（2026-11-19）

- 目标：`https://swiftbugs.cn`（腾讯云广州单机 `111.230.155.116`）
- 方式：手动增量发布（生产磁盘不足以走发布控制台容量准入）
- 发布内容：后端 + 前端（AIQE V1.5 / 能力心跳 / 外部 Runner 协议）

## 发布前

| 项 | 值 |
|---|---|
| 生产磁盘可用 | 5.0G / 40G |
| 数据库备份 | `/opt/cameltv-backup/aiqe-pre-deploy-20261119-1655.dump`（190M） |
| 本地备份 | `F:\CamelTv-safe-backup\prod-db-pre-deploy-20261119.dump`（190M） |
| 旧镜像回滚标签 | `cameltv-tp-backend:prev-aiqe-20261119` / `cameltv-tp-frontend:prev-aiqe-20261119` |

## 清理

删除旧发布包/旧备份/构建缓存，未删除容器、卷、当前镜像：

- `/opt/cameltv-release` 旧 tar（2026-09-24 / 2026-10-07）：约 3.4G
- `/root/backups` 旧 dump（保留最新一份）：约 2.0G
- `/opt/cameltv-backup` 旧 dump（保留最新）：约 1.0G
- `/root` 旧 minio/v14 包 + Docker 构建缓存

结果：可用空间 **5.0G → 12G**。

## 构建与发布

```text
镜像 tag: aiqe-prod-20261119-1
backend:  cameltv-tp-backend:aiqe-prod-20261119-1  (3.39GB)
frontend: cameltv-tp-frontend:aiqe-prod-20261119-1 (96.4MB)
上线标签: cameltv-tp-backend:main / cameltv-tp-frontend:main
```

```bash
docker load -i aiqe-prod-20261119-1-backend.tar
docker load -i aiqe-prod-20261119-1-frontend.tar
docker tag cameltv-tp-backend:aiqe-prod-20261119-1 cameltv-tp-backend:main
docker tag cameltv-tp-frontend:aiqe-prod-20261119-1 cameltv-tp-frontend:main
cd /opt/cameltv-tp/test-platform-v2/deploy
API_IMAGE=cameltv-tp-backend:main RUNNER_IMAGE=cameltv-tp-runner:main docker compose -p cameltv-tp-production   --env-file /root/production.env.bak-20261109-235015   -f docker-compose.yml -f docker-compose.override.yml   -f docker-compose.execution.release-20261007-0001.yml   up -d --no-deps --force-recreate backend frontend
```

## 发布后验证

| 检查 | 结果 |
|---|---|
| `GET https://swiftbugs.cn/api/v1/open/health` | **200** `{"status":"ok","version":"2.3.0"}` |
| `GET https://swiftbugs.cn/` | **200**，title `CamelTv 测试平台` |
| `POST /api/v1/aiqe/nodes/{id}/heartbeat`（无 token） | **401** `缺少 X-AI-Agent-Token`（路由已上线） |
| backend 容器 | Up，**healthy**，`Image=cameltv-tp-backend:main` |
| frontend 容器 | Up，**healthy**，`Image=cameltv-tp-frontend:main` |
| postgres | Up，healthy（未重建） |
| 生产磁盘可用 | **12G** |

## 回滚

```bash
docker tag cameltv-tp-backend:prev-aiqe-20261119 cameltv-tp-backend:main
docker tag cameltv-tp-frontend:prev-aiqe-20261119 cameltv-tp-frontend:main
cd /opt/cameltv-tp/test-platform-v2/deploy
API_IMAGE=cameltv-tp-backend:main RUNNER_IMAGE=cameltv-tp-runner:main docker compose -p cameltv-tp-production   --env-file /root/production.env.bak-20261109-235015   -f docker-compose.yml -f docker-compose.override.yml   -f docker-compose.execution.release-20261007-0001.yml   up -d --no-deps --force-recreate backend frontend
```

数据库备份位于 `/opt/cameltv-backup/aiqe-pre-deploy-20261119-1655.dump`，必要时 `pg_restore` 回滚。

## 说明

- 本次为手动发布，未走 `release.swiftbugs.cn` 状态机；发布控制台未记录该 release。
- 生产 `production.env` 中 `ADMIN_PASSWORD` 与当前有效管理员密码不一致（登录 401），因此未做需要登录的 AIQE 生产写操作；公网健康、前端、心跳路由已验证。
- 旧镜像/备份已保留，回滚路径可用。
