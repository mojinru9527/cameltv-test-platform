---
title: "DevOps 基础设施操作手册（C58-06 / OPS1 / G2~G6）"
owner: "devops"
created: "2026-08-02"
status: "active"
tags: ["devops", "railway", "github-packages", "runner", "postgres", "secrets"]
related:
  - "../test-platform-v2/backend/Dockerfile"
  - "../test-platform-v2/frontend/vercel.json"
  - "外部阻塞项手动填写清单.md"
---

# DevOps 基础设施操作手册

> 目标：把 G2~G6 与 C58-06（后端托管）变成您按步骤可执行的清单。
> 原则：**需要您本人在 GitHub/Railway 网页上点击的步骤**已明确标注「您操作」；
> 其余配置由我写入仓库。

## 0. 前置说明

- 现有 GitHub 账号 `mojinru9527` 即可，无需新注册任何"DevOps 账号"。
- lanhu-mcp 子模块 remote：`https://github.com/mojinru9527/lanhu-mcp.git`
  （若为私有仓库，云构建拉取时需要公开或提供 PAT，见 §1.4）。

## 1. Railway 后端部署（C58-06 / F5）

### 1.1 新建项目

1. **您操作**：登录 [railway.app](https://railway.app)（GitHub 登录）→ `New Project` → `Deploy from GitHub repo`。
2. 选择 `mojinru9527/cameltv-test-platform`，Railway 会创建服务。

### 1.2 关键设置（build failed 的修复点）

| 设置项 | 值 | 说明 |
|---|---|---|
| Root Directory | **留空（仓库根 `/`）** | Dockerfile 里的 COPY 路径是 `test-platform-v2/backend/...`，必须以仓库根为构建上下文 |
| Build | **Dockerfile** | 自动发现 `test-platform-v2/backend/Dockerfile`；若显示 Nixpacks 请切换为 Dockerfile |
| Start | 由 Dockerfile `CMD` 决定 | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |

> 之前 build failed 的最可能原因：Railway 不拉 Git 子模块，`COPY lanhu-mcp/...` 找不到目录。
> 我已修复 `test-platform-v2/backend/Dockerfile`：构建期直接从子模块 remote `git clone`。

### 1.3 环境变量（Project → Variables）

至少先填两组即可启动：

```dotenv
ENVIRONMENT=production
DATABASE_URL=postgresql://postgres.<ref>:<密码>@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres
SECRET_KEY=<独立强随机值>
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<独立强随机值>
TESTER_USERNAME=tester
TESTER_PASSWORD=<独立强随机值>
ALLOWED_ORIGINS=https://cameltv-test-platform1.vercel.app
COOKIE_SECURE=true
```

> 密码中的 `@ : / # %` 需 URL 编码。`DATABASE_URL` 从 Supabase Dashboard →
> Project Settings → Database → Connection string (Pooler) 复制。
>
> ⚠️ **面板连接串里的密码是占位符 `[YOUR-PASSWORD]`，不会显示真实密码**：
> 复制后必须用创建项目时设置的数据库密码替换该占位符。若忘记密码，
> 到 `Project Settings → Database → Reset database password` 重置后再填。
> 新版面板入口可能在项目页右上角蓝色 **Connect** 按钮（弹窗 → ORMs/App
> frameworks → PostgreSQL → Connection string），效果相同。

### 1.4 常见失败排查

| 现象 | 原因 | 处理 |
|---|---|---|
| build failed（1 分钟内） | 子模块缺失（已修）或 lanhu-mcp 私有 | 重试部署；若 clone 鉴权失败，将 lanhu-mcp 仓库设为 public，或配置 PAT 后把 URL 改为 `https://<token>@github.com/...`（PAT 只放构建 secret） |
| 启动即退出 | `DATABASE_URL`/`SECRET_KEY` 缺失 | 按 §1.3 补齐 Variables 后 redeploy |
| `/api` 502/500 | Vercel 反代未指向本服务 | 后端地址已写死在 `test-platform-v2/frontend/vercel.json` 的 `/api` rewrite 中；Railway 服务域名变更时同步更新该文件并重新部署 |

### 1.5 验证

部署完成后访问 `https://<service>.up.railway.app/api/v1/open/health`（或 `/health`），
HTTP 200 即成功，把 URL 发回。

## 2. G2：镜像 registry（GitHub Packages / ghcr.io）

1. 无需新账号：GitHub 账号自带 `ghcr.io` 容器仓库。
2. **我负责**：在仓库添加 workflow（push 到 main 时构建后端镜像并推送
   `ghcr.io/mojinru9527/cameltv-test-platform/backend:<sha>`），使用内置
   `GITHUB_TOKEN`，无需您生成密钥。
3. **您操作（可选）**：GitHub → Settings → Packages → 将 `cameltv-test-platform`
   包可见性设为仓库内可用（或 public）。
4. 若需要跨仓库拉取：GitHub → Settings → Developer settings → Personal access
   tokens → 生成（勾选 `read:packages`/`write:packages`）→ 存入仓库 Secret `GH_PAT`。

## 3. G3：GitHub 自托管 runner（跑内网 Test5 必需）

1. **您操作**：仓库页面 → `Settings` → `Actions` → `Runners` → `New self-hosted runner`。
2. 选择操作系统（Windows x64），页面会给出两条命令（下载 + config），
   在**能访问内网/OpenVPN 的 Windows 机器**上依次执行。
3. 执行完 runner 出现在 Runners 列表 → 把 runner 名称/标签发我。
4. 我负责：把 Test5 相关 workflow 的 `runs-on: [self-hosted, 内网]` 标签写对。

> ⚠️ runner 必须能连通 `*.elelive.cn`（OpenVPN 网络），否则 Test5 任务仍会失败。

## 4. G4：PostgreSQL 16 + 备份

1. 若用 Supabase 托管库：备份用 Supabase Dashboard → Database → Backups（自带）。
2. 若自建 PG16（服务器或 Docker）：

```bash
docker run -d --name cameltv-pg16 \
  -e POSTGRES_USER=cameltv -e POSTGRES_PASSWORD=<密码> -e POSTGRES_DB=cameltv \
  -v cameltv-pgdata:/var/lib/postgresql/data \
  -p 5432:5432 postgres:16-alpine
```

3. 每日备份（cron，保留 30 天）：

```bash
0 2 * * * pg_dump -h 127.0.0.1 -U cameltv -Fc cameltv > /backup/cameltv-$(date +\%F).dump && find /backup -name 'cameltv-*.dump' -mtime +30 -delete
```

4. **您操作**：确认备份目录位置与保留期，发我登记（写入清单 G4）。

## 5. G5：秘密管理

1. CI 秘密：GitHub 仓库 → `Settings` → `Secrets and variables` → `Actions` →
   `New repository secret`，按需新增：

   **业务平台自动刷新 token（必需）**
   - `CAMELTV_TEST_USERNAME` / `CAMELTV_TEST_PASSWORD`：测试5 业务账号账密
   - `CAMELTV_PROD_USERNAME` / `CAMELTV_PROD_PASSWORD`：生产业务账号账密
   - `VPN_TUN_ADDR`：vpn07 tun 地址（prod-smoke 用）

   **可选（v1 配置当前为注释态）**
   - `CAMELTV_TEST_DB_USER` / `CAMELTV_TEST_DB_PWD`、`CAMELTV_TEST_REDIS_PWD`、
     `CAMELTV_TEST_MQ_USER` / `CAMELTV_TEST_MQ_PWD`、`ELASTIC_API_KEY` / `ELK_PASSWORD`

   > 说明：自 Batch 63 起，定时任务在每次运行前用账密现场登录业务站并刷新
   > `auth_token`（脚本 `tests/automation/ui/utils/fetch-auth-token.cjs`，HTTP 直连
   > `POST .../account-service/ee/client/demo/login`，form-data：
   > `countryCode=86&mobile=<手机号>&password=<密码>`），
   > **不再需要手动维护** `CAMELTV_TEST_AUTH_TOKEN` / `CAMELTV_PROD_AUTH_TOKEN`。
   > 账号为手机号时国家码默认 `+86`（`CAMELTV_COUNTRY_CODE`），
   > `CAMELTV_*_USERNAME` 填手机号本地号（不带 +86）；
   > `CAMELTV_LOGIN_URL` 测试5=`https://camel-test5.elelive.cn/account-service/ee/client/demo/login`，
   > 生产=`https://api.cameltv.live/account-service/ee/client/demo/login`。
2. 本地运行秘密：只写 gitignored 的 `test-platform-v2/backend/.env`（已完成同步）。
3. 生产运行秘密：只写 gitignored 的 `test-platform-v2/config/runtime/production.env`。

## 6. G6：首次执行窗口

**您操作**：确定第一次 test release 演练窗口（日期/时段），发我登记；
窗口内不得有生产发布或大批量回归任务。

## 7. 完成标准

- [x] Railway 服务部署成功且 health 200 → C58-06 关闭；`/api` 反代目标已写死在 `vercel.json`（`https://test-platform.up.railway.app`）
- [ ] ghcr.io workflow 推送成功 → G2 关闭
- [ ] 自托管 runner 上线 → G3 关闭
- [ ] PG16 备份验证一次恢复 → G4 关闭
- [ ] 仓库 Secrets 就绪 → G5 关闭
- [ ] 执行窗口登记 → G6 关闭
