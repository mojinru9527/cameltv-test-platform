# CamelTv 测试平台 v2 — Docker 部署指南

## 前置要求

- Docker 20.10+
- Docker Compose v2
- 已初始化根仓 `lanhu-mcp` 子模块：

```bash
git submodule update --init --recursive lanhu-mcp
```

## 快速开始

长期运行环境使用独立 profile 和 Compose project。真实 profile 位于
`../config/runtime/*.env`，已被 Git 忽略；仓库只提交不含真实凭据的
`*.env.example`。

```bash
# 1. 测试环境只配置一次
cp ../config/runtime/test.env.example ../config/runtime/test.env
# 编辑 test.env：设置独立密钥、账号密码、PostgreSQL 和最终 HTTPS 来源

# 2. 以后用固定 profile 启动或查询
pwsh ../scripts/start-platform-environment.ps1 -Target test -Action start
pwsh ../scripts/start-platform-environment.ps1 -Target test -Action status

# 3. 生产环境需要额外显式确认
pwsh ../scripts/start-platform-environment.ps1 `
  -Target production -Action start -ConfirmProduction
```

local、test、production 使用不同 `COMPOSE_PROJECT_NAME`、端口、数据库名和
Docker volume，可以在同一宿主机共存。浏览器始终通过各自 HTTPS 入口访问，
前端继续同源请求 `/api/v1`；不得把浏览器临时改为直连另一环境后端。

## 首次登录凭据

账号名和密码由部署人员在未跟踪的 `.env` 中设置。平台页面、仓库、日志和使用手册均不提供通用默认密码；首次登录后应立即在“系统管理”中改为个人密码。

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SECRET_KEY` | 无 | JWT 签名密钥，必填 |
| `ADMIN_PASSWORD` | 无 | 初始管理员密码，必填 |
| `TESTER_PASSWORD` | 无 | 初始测试账号密码，必填 |
| `POSTGRES_PASSWORD` | 无 | PostgreSQL 密码，必填 |
| `DATABASE_URL` | 无 | PostgreSQL URL，必填；密码须 URL 编码 |
| `COMPOSE_PROJECT_NAME` | 无 | 每个环境唯一，用于隔离容器、网络和 volume |
| `PLATFORM_FRONTEND_URL` | 无 | 用户固定访问的完整 HTTPS 来源 |
| `FRONTEND_PORT` | `80` | 前端访问端口 |
| `ALLOWED_ORIGINS` | 无 | 最终 HTTPS 入口的精确来源 |
| `ELK_BASE_URL` | (空) | Kibana 地址，用于 traceId 链路 |
| `ELK_INDEX` | `*` | ELK 索引 pattern |

## 常用命令

```bash
# 查看状态
docker compose --project-name cameltv-tp-test \
  --env-file ../config/runtime/test.env ps

# 查看日志
docker compose --project-name cameltv-tp-test \
  --env-file ../config/runtime/test.env logs -f backend

# 重启
docker compose --project-name cameltv-tp-test \
  --env-file ../config/runtime/test.env restart

# 停止
docker compose --project-name cameltv-tp-test \
  --env-file ../config/runtime/test.env down

# 停止并清除数据
docker compose --project-name cameltv-tp-test \
  --env-file ../config/runtime/test.env down -v
```

## 数据持久化

- PostgreSQL 数据存储在 Docker volume `pg-data` 中
- UI 自动化执行产物和蓝湖证据包存储在 Docker volume `tp-artifacts` 中，
  对应容器目录 `/app/storage`
- 蓝湖下载缓存使用 `/data/lanhu`，由 `tp-data` 持久化
- 使用 `docker compose down -v` 会**永久删除数据库和验收产物**

## Backend 执行器运行时

backend 镜像从仓库根目录构建，Dockerfile 因而可以同时复制：

- `test-platform-v2/backend/tests/playwright`：平台 UI Runner 的锁文件、配置和测试脚本；
- `lanhu-mcp/lanhu_mcp_server.py`：根仓固定子模块中的蓝湖 Provider 运行模块。

镜像包含 Node.js、npm、Chromium Playwright 运行时和 ffmpeg/ffprobe。
UI Runner 严格使用提交的 `package-lock.json` 执行 `npm ci`，不会以
`npm install` 绕过锁文件。构建时还会把 Python Playwright 对齐到 npm
锁定版本，使 UI Runner 和蓝湖截图共用 `/ms-playwright` 下的 Chromium。
Python 依赖安装在 `/opt/venv`，最终进程以固定 UID/GID `10001:10001`
的 `cameltv` 用户运行，不依赖或访问 `/root/.local`。镜像构建阶段会把
`/app`、`/data`、`/ms-playwright`、`/app/storage` 和运行用户缓存目录
设置为可读写。

这些依赖会显著增大 backend 镜像。未完成完整构建时应按“数百 MB 的浏览器
与系统库增量”评估，最终压缩/展开体积必须以实际 `docker image inspect`
结果回填，不能引用估算值作为交付证据。

### 静态构建检查

在仓库根目录执行：

```bash
docker build --check \
  -f test-platform-v2/backend/Dockerfile \
  .
```

或在本目录配置好未跟踪的 `.env` 后执行：

```bash
docker compose config --quiet
docker compose build --check backend
```

### 完整镜像构建后的运行时探针

```bash
docker compose run --rm --no-deps backend sh -c \
  'test "$(id -u)" = 10001 &&
   test -w /app &&
   test -w /data &&
   test -w /ms-playwright &&
   test -w /app/storage'

docker compose run --rm --no-deps backend sh -c \
  "node --version &&
   npm --version &&
   /app/tests/playwright/node_modules/.bin/playwright --version &&
   ffprobe -version | head -n 1"

docker compose run --rm --no-deps backend python -c \
  "import sys; sys.path.insert(0, '/app/lanhu-mcp'); import lanhu_mcp_server; print('lanhu-mcp import ok')"

docker compose run --rm --no-deps backend python -c \
  "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(headless=True); print(b.version); b.close(); p.stop()"
```

### 既有 volume 的权限迁移

新创建的 `tp-data` 和 `tp-artifacts` 会继承镜像目录的非 root 所有权。
Compose 在 backend 启动前运行一次 `volume-permissions` 服务，只对
`tp-data:/data` 与 `tp-artifacts:/app/storage` 执行
`chown -R 10001:10001`。它不会挂载或递归修改任意宿主机目录。

### 本镜像仍未解决的能力

- `LANHU_OCR_PROVIDER=local` 仍需要另行提供真实 OCR 命令/引擎；Chromium
  截图能力不等于 OCR 已可用。
- 镜像未安装 ADB，也没有获得 USB/网络设备授权。
- 镜像未安装或配置 SoloX；性能采集会明确返回 503，不会生成 Mock 设备
  或随机指标。生产启用前必须部署经鉴权的设备代理（或受限
  ADB-over-TCP + 固定 SoloX 运行时）并完成真机验收。
- 是否能访问蓝湖、外部站点、媒体流和设备仍取决于当前网络与授权配置。

## 升级

```bash
git pull
docker compose up -d --build
```

共享环境 profile 必须设置 `ENVIRONMENT=production`、`COOKIE_SECURE=true`；
Compose 固定 `AUTO_CREATE_TABLES=false`。必须由外层负载均衡器或反向代理终止 TLS；
直接通过明文 HTTP 打开容器端口只用于健康探测，Secure Cookie 登录不会工作。

## 排障

**端口被占用**：修改 `.env` 中 `FRONTEND_PORT` 为其他端口

**后端启动失败**：查看日志 `docker compose logs backend --tail 50`

**数据库错误**：删除 volume 重建 `docker compose down -v && docker compose up -d`

> `docker compose down -v` 会永久删除数据，只能在确认已有备份并明确需要重建时执行。
