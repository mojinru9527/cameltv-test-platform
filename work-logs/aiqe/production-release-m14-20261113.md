# AIQE M9-5 生产发布 release-m14（2026-11-13）

> **发布内容**：main `503d0e07c`（batch-340 attempt/retry、341 回归 API、342 Workflow 写 API + 审批权限）
> **镜像**：`cameltv-tp-backend:release-m14-20261113`、`cameltv-tp-frontend:release-m14-20261113`
> **迁移**：无（head `20261123_ta033_mutation_ledger`）
> **结果**：生产 backend/frontend healthy，`https://swiftbugs.cn/api/v1/open/health` = 200

## 1. 镜像与 digest

| 镜像 | digest | 构建方式 |
|------|--------|----------|
| `cameltv-tp-backend:release-m14-20261113` | `sha256:e3d3d78a23b4…` | **delta**（`FROM release-m13-20261113` + COPY app/alembic） |
| `cameltv-tp-frontend:release-m14-20261113` | `sha256:3fd462f78301…` | **全量**（`FROM nginx:alpine` + dist/nginx.conf/security-headers.conf） |

回滚位：`cameltv-tp-backend:prev-m14`（release-m13，`dc9ed67…` 链）、`cameltv-tp-frontend:prev-m14`。
版本锁：`config/aiqe-version.lock` → commit `503d0e07c` / `release-m14-20261113` / head `20261123`。

### 全量后端镜像重建（未完成，已登记）

按 M9-344 计划尝试从零重建 backend（`--target runner`）：

1. 首次 `docker build` → `pip install --require-hashes` 连接 `files.pythonhosted.org` **ReadTimeout**；
2. 改用清华 PyPI 镜像重试 → 构建 50+ 分钟仍未完成（DSH/Playwright 依赖层），磁盘余量降至 4.5G，主动取消；
3. 回退 **delta 镜像**完成本次发布，避免阻塞生产窗口。

结论：**backend 全量重建受外部依赖源/构建时长阻塞**，作为 M9 残项跟踪（建议：CI 镜像构建机预置 wheelhouse，或使用固定依赖缓存层后再全量重建）。

## 2. 遗留服务清理（生产 compose）

| 项 | 处置 |
|----|------|
| `aitde-worker` | 从 server compose 与 override 删除服务定义；删除容器；旧启动脚本引用已删除的 `app.modules.aitde` |
| `ai-gateway` | 从 server compose 删除（平台简化批次已移除模块，容器本未运行） |
| `aitde-temporal` | 停止容器、`restart=no`，compose 文件改名 `.disabled-20261113` |
| compose 服务清单 | 收敛为 backend / frontend / postgres / runner / volume-permissions（`docker compose config --services`） |

## 3. 发布后验证

| # | 项 | 结果 |
|---|----|:----:|
| 1 | 公网 health | ✅ 200 |
| 2 | backend / frontend 容器 | ✅ healthy |
| 3 | OpenAPI 新接口 | ✅ `/aiqe/runs/{id}/attempts`、`/aiqe/regressions`、`/aiqe/workflows`（POST/PATCH） |
| 4 | 新权限种子 | ✅ `aiqe:workflow:approve` 已入库（admin 经 `*`；无额外角色绑定） |
| 5 | 迁移 | ✅ 无变化，head 保持 `20261123` |
| 6 | UI | ✅ `https://swiftbugs.cn/` 200，bundle `index-fCMe3vQ_.js` |
| 7 | 遗留容器 | ✅ 无 aitde-worker/ai-gateway/aitde-temporal 运行 |

## 4. 回滚

```bash
cd /opt/cameltv-tp/test-platform-v2/deploy
docker tag cameltv-tp-backend:prev-m14 cameltv-tp-backend:main
docker tag cameltv-tp-frontend:prev-m14 cameltv-tp-frontend:main
docker compose --env-file ../config/runtime/production.env \
  -f docker-compose.yml -f docker-compose.override.yml up -d --no-deps backend frontend
```

> 发布中曾出现 502：backend 重建后 IP 变化而旧 frontend nginx 缓存了旧 upstream；随 frontend 发布重建后恢复（health 200）。
