# Release Console（独立发布控制台）

> 与测试平台**完全解耦**的运维发布入口。测试平台（swiftbugs.cn）即使不可用，
> 依然可以通过本控制台发布/回滚/备份/查看发布历史。

## 为什么独立

见 ADR-0015「控制面与执行面分离」：发布控制面不能运行在被发布对象内部
（鸡生蛋问题——平台挂了则无法网页回滚）。本控制台是唯一例外：它只依赖
FastAPI + SQLite + SSH，与测试平台 backend 无任何代码/运行时耦合。

## 架构

```
浏览器 → https://release.swiftbugs.cn（Caddy 自动 HTTPS）
              ↓
        release-console 容器 :8003（独立 compose 服务）
              ↓ SSH（密钥经 RELEASE_CONSOLE_TOKEN/TENCENT_* 注入）
        111.230.155.116（测试平台生产）
```

## 环境变量（全部必填，缺失即 fail-closed 503）

| 变量 | 说明 |
|------|------|
| `RELEASE_CONTROL_DATABASE_PATH` | 状态库路径（独立于测试平台业务库） |
| `RELEASE_CONSOLE_TOKEN` | 控制台访问令牌（Bearer，前端 localStorage 保存） |
| `TENCENT_EXECUTOR_HOST` / `USER` / `SSH_KEY` | SSH 目标 + base64 私钥 |
| `TENCENT_EXECUTOR_COMPOSE_DIR` / `RELEASE_DIR` / `BACKUP_DIR` | 服务器目录 |
| `TENCENT_EXECUTOR_IMAGE_BACKEND` / `FRONTEND` | 目标镜像（**必须与服务器 compose override 引用的 tag 一致**） |
| `TENCENT_EXECUTOR_COMPOSE_PROJECT` / `TIMEOUT` / `KEEP_BACKUPS` | 发布参数 |

> ⚠️ **IMAGE_* 与 compose tag 对齐**：腾讯云生产 compose（`test-platform-v2/deploy/docker-compose.override.yml`）
> 引用 `cameltv-tp-backend:main` / `cameltv-tp-frontend:main`，因此服务器上 `release-console.env` 必须配置
> `TENCENT_EXECUTOR_IMAGE_BACKEND=cameltv-tp-backend:main`、`TENCENT_EXECUTOR_IMAGE_FRONTEND=cameltv-tp-frontend:main`。
> 若两者不一致，deploy/rollback 会 retag 到 compose 未引用的 tag，容器不重建（**假成功**）。

## 部署

```bash
cd deploy/release-console
docker build -t cameltv-release-console:latest .
# 生产实际运行参数（腾讯云 111.230.155.116）：
docker run -d --name release-console --restart unless-stopped \
  -p 127.0.0.1:8111:8003 \
  -v /opt/cameltv-release-console/data:/data \
  --env-file /opt/cameltv-release-console/release-console.env \
  cameltv-release-console:latest
```

Caddy 添加：

```
release.swiftbugs.cn {
    reverse_proxy 127.0.0.1:8111
}
```

## 使用

1. 浏览器打开 https://release.swiftbugs.cn
2. 首次使用在浏览器 console 设置 token：
   `localStorage.setItem('console_token', '<RELEASE_CONSOLE_TOKEN>')`
   （或使用页面顶部「访问令牌」输入框保存）
3. 状态机闭环：提交登记（DRAFT）→ 验证（VALIDATED）→ 发布（PROD_OBSERVING）→ 确认上线（PRODUCTION_VERIFIED）；
   任意非终态可回滚（PROD_ROLLED_BACK），备份随时可做。
4. 命令行一键：`pwsh scripts/ops/release.ps1 -Tag release-YYYYMMDD-NNNN -Publish`
   （构建 → digest → 提交 → 上传 → 验证 → 发布 → 确认上线全自动）

## 安全

- 所有 API 需要 `Authorization: Bearer <token>`；token 缺失时服务拒绝启动（fail-closed）
- SSH 私钥仅环境变量注入，临时文件 0600 用完即删
- 状态机强制合法流转；无用户输入拼接进命令
