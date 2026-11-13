# AIQE Test 实例部署验证（2026-11-13）

> 目标：把 main `c2573eecb`（batch-336 ~ 339 / P1）部署到隔离 Test 实例，验证 Console 新入口与新 API。
> 环境：腾讯云 Lighthouse `111.230.155.116` 上的隔离 Test（`aiqe-test-net` / 端口 18000 + 18080），不触碰生产容器与数据库。

## 1. 部署物

| 组件 | 内容 | 来源 |
|------|------|------|
| 后端镜像 | `cameltv-tp-backend:release-m13-20261113`（delta：`FROM release-m12-20261112` + COPY `app/`、`alembic/`、`alembic.ini`） | main `c2573eecb` |
| 容器 | `aiqe-test-backend`（替换 `aiqe-test-backend-prev-m12`，保留用于回滚） | 原 env/network/ports 不变 |
| 前端 | `/opt/aiqe-test/frontend`（nginx bind mount） | `npm run build` dist |
| 数据库 | 既有 `aiqe_test`（head `20261123`，**本批无新迁移**） | — |

备份：旧前端 `/opt/aiqe-test/frontend-backup-20261113`；旧容器 `aiqe-test-backend-prev-m12`；env 快照 `/root/m13/aiqe-test.env`（600）。

## 2. 验证结果

| # | 项 | 结果 | 证据 |
|---|----|:----:|------|
| 1 | 后端启动 | ✅ | 日志 `Application startup complete`，`alembic upgrade head` 单头 |
| 2 | Test API health | ✅ | `http://127.0.0.1:18000/api/v1/open/health` → 200 |
| 3 | Test UI | ✅ | `http://127.0.0.1:18080/` → 200，index 引用新 bundle `index-fCMe3vQ_.js` |
| 4 | SPA 新路由 | ✅ | `/aiqe/platform-matrix` → 200（nginx try_files） |
| 5 | OpenAPI 新接口 | ✅ | `/api/v1/aiqe/platform-matrix`、`/api/v1/aiqe/workflows` 均在 spec 中 |
| 6 | 菜单权限点 | ✅ | `/system/menus` 返回含 `menu:aiqe_runs`（admin） |
| 7 | 平台矩阵真实数据 | ✅ | 200，`{platforms:[],nodes:[],available_nodes:0}`（无节点注册，不造 mock） |
| 8 | Workflow 列表 | ✅ | 200，返回真实 `workflow_definitions`（version 2 等） |
| 9 | Profile 列表 | ✅ | 200 |
| 10 | 质量门禁 | ✅ | `p0_total=2,p0_passed=2` → `gate_status=PASS` |
| 11 | 登录 | ✅ | admin 登录拿到 access_token（限流内 1 次） |

## 3. 复现命令（服务器）

```bash
# 后端镜像（/root/m13）
docker build -f /root/m13/Dockerfile.m13 -t cameltv-tp-backend:release-m13-20261113 /root/m13

# 容器替换（保留旧容器做回滚）
docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' aiqe-test-backend > /root/m13/aiqe-test.env
docker stop aiqe-test-backend && docker rename aiqe-test-backend aiqe-test-backend-prev-m12
docker run -d --name aiqe-test-backend --network aiqe-test-net --restart unless-stopped \
  -p 127.0.0.1:18000:8000 --env-file /root/m13/aiqe-test.env \
  cameltv-tp-backend:release-m13-20261113

# 前端
find /opt/aiqe-test/frontend -mindepth 1 -delete
tar -xzf /root/aiqe-frontend-main.tgz -C /opt/aiqe-test/frontend
```

## 4. 回滚

```bash
docker stop aiqe-test-backend && docker rm aiqe-test-backend
docker rename aiqe-test-backend-prev-m12 aiqe-test-backend
docker start aiqe-test-backend
rm -rf /opt/aiqe-test/frontend && cp -a /opt/aiqe-test/frontend-backup-20261113 /opt/aiqe-test/frontend
```

## 5. 结论

P1 代码已在隔离 Test 实例完成真实登录 + 菜单 + 新接口验证；生产保持不变（`release-m12`，health 200）。
