# 生产发布 release-m15（2026-11-14，M10 已交付部分）

> **范围**：M10 已完成的后端能力上线——batch-349 学习候选/BugPattern API、batch-347/347c 执行器与外部节点回写。
> 前端无变更；无数据库迁移（head 仍 `20261123_ta033_mutation_ledger`）。

## 1. 产物

| 项 | 值 |
|----|----|
| 镜像 | `cameltv-tp-backend:release-m15-20261114` |
| digest | `sha256:5d683bdd936906799f1d515a337536537bdc0147473a9f0455d469f6831962eb` |
| 基线 | `cameltv-tp-backend:main`（release-m14 e3d3d78a） |
| 回滚位 | `cameltv-tp-backend:prev-m15`（= 发布前 main） |
| 构建方式 | delta：`FROM cameltv-tp-backend:main` + 当前 main 的 app/alembic |
| 提交 | `ff5353a40` |

## 2. 发布步骤（已执行）

```bash
# 构建（服务器）
docker build -t cameltv-tp-backend:release-m15-20261114 -f /root/m23/Dockerfile /root/m23
docker tag cameltv-tp-backend:main cameltv-tp-backend:prev-m15
docker tag cameltv-tp-backend:release-m15-20261114 cameltv-tp-backend:main

# 重建 backend（仅 backend）
cd /opt/cameltv-tp/test-platform-v2/deploy
docker compose --env-file /root/production.env.bak-20261109-235015 \
  -f docker-compose.yml -f docker-compose.override.yml up -d backend
```

## 3. 验证

| 检查 | 结果 |
|------|------|
| `GET /api/v1/open/health`（HTTPS） | 200 |
| backend 容器镜像 digest | `sha256:5d683bdd…`（= release-m15） |
| 容器状态 | Up (healthy) |
| `GET /api/v1/aiqe/learning/candidates`（未登录） | 401（路由存在且鉴权生效） |
| `GET /api/v1/aiqe/learning/bug-patterns`（未登录） | 401 |
| OpenAPI 含 learning 路径 | ✅ |
| 前端 | 无变更，未重建 |

## 4. 回滚

```bash
docker tag cameltv-tp-backend:prev-m15 cameltv-tp-backend:main
cd /opt/cameltv-tp/test-platform-v2/deploy
docker compose --env-file /root/production.env.bak-20261109-235015 \
  -f docker-compose.yml -f docker-compose.override.yml up -d backend
```

> 回滚不涉及数据迁移（本次无 schema 变更），只需重建 backend 容器。

## 5. 说明

- AIQE 进程内执行器/外部 runner 开关在生产**保持关闭**，本发布只上线只读/写 API 与回写逻辑；
- 学习 API 在生产需要 `menu:aiqe_runs` + `defect:*` 权限（管理员可用）；
- M10 的 346/348 仍待外部环境，本次发布不改变其阻塞状态。
