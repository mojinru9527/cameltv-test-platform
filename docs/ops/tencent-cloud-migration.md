---
title: "腾讯云广州生产迁移手册（swiftbugs.cn）"
owner: "devops"
created: "2026-08-13"
status: "draft"
tags: ["tencent-cloud", "production", "migration", "icp", "swiftbugs.cn"]
related: ["../test-platform-v2/config/runtime/production.env.example", "../test-platform-v2/scripts/migrate-tencent-production.sh", "railway-storage.md"]
---

# 腾讯云广州生产迁移手册（swiftbugs.cn）

> 目标：把测试平台生产环境从 **Vercel（前端）+ Railway（后端）+ Supabase（PostgreSQL）**
> 迁移到 **腾讯云广州轻量服务器单机部署**（Docker Compose：Nginx 前端 + FastAPI 后端 + PostgreSQL）。
> 域名：`swiftbugs.cn`（个人备案中）。

## 1. 目标架构

```
用户 → https://swiftbugs.cn
        │
        ▼
  Caddy（宿主机 :443，自动 HTTPS）        ← TLS 由外层反代终止（容器只监听 80）
        │
        ▼
  前端容器 nginx:80（静态站点 + /api 反代 → backend:8000）
        │
        ▼
  backend 容器（FastAPI :8000，uvicorn）
        ├── postgres 容器（:5432，Docker volume pg-data）    ← 生产数据库（不再用 Supabase）
        └── /app/storage 持久卷（蓝湖证据截图/导出/Cookie）   ← 从 Railway 卷搬迁
```

## 2. 前置资源清单（只能本人在腾讯云控制台操作）

| # | 资源 | 要求 | 状态 |
|---|------|------|------|
| 1 | 账号实名 | 个人实名（人脸核验），新用户新实名才有优惠价 | ☐ |
| 2 | 域名 `swiftbugs.cn` | 腾讯云购买 + **域名实名认证**，所有者=备案主体（本人姓名） | ☐ |
| 3 | 服务器 | 广州轻量 2核4G 起（推荐 4核4G 38元/年秒杀，**年付**；备案要求订阅≥3个月） | ☐ |
| 4 | ICP 备案 | 域名实名满 3 个自然日后提交；腾讯云初审 1-2 工作日 + 管局终审 ≤20 工作日 | ☐ |
| 5 | 安全组 | 备案通过前**只放行 22**；通过后放行 80/443 | ☐ |

> ⚠️ 备案等待期纪律：备案通过前**不得用公网 80/443 对外提供服务**。等待期只做镜像构建、环境配置、本地数据演练。

## 3. 阶段 1：服务器初始化

```bash
# 以 root 或 sudo 用户执行（示例 Ubuntu 22.04/Debian 12；腾讯云轻量默认镜像可选 Ubuntu）
sudo apt-get update && sudo apt-get install -y git ca-certificates curl

# 安装 Docker + Compose 插件（官方脚本）
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER" && exec newgrp docker
docker compose version   # 期望 Compose v2

# 拉取代码（注意初始化 lanhu-mcp 子模块）
git clone https://github.com/mojinru9527/cameltv-test-platform.git
cd cameltv-test-platform
git submodule update --init --recursive lanhu-mcp
```

## 4. 阶段 2：配置 production.env

```bash
cd test-platform-v2
cp config/runtime/production.env.example config/runtime/production.env
# 编辑 config/runtime/production.env，替换所有 change-me / example 值
```

必填/关键项：

| 变量 | 填写说明 |
|------|---------|
| `SECRET_KEY` | `openssl rand -hex 32` 生成 |
| `ADMIN_PASSWORD` / `TESTER_PASSWORD` | 独立强随机串 |
| `POSTGRES_PASSWORD` / `DATABASE_URL` | 独立强随机密码；`DATABASE_URL` 中密码需 **URL 编码**（如 `@` → `%40`） |
| `ALLOWED_ORIGINS` / `CSRF_ALLOWED_ORIGINS` | `https://swiftbugs.cn`（备案通过后的正式入口） |
| `FRONTEND_URL` | `https://swiftbugs.cn`（项目邀请等可分享链接） |
| `COOKIE_SECURE` | 保持 `true`（必须 HTTPS） |
| `SEED_DEMO_USERS` | 生产外放建议 `false` |
| `VITE_ICP_NUMBER` | 备案通过后回填，如 `粤ICP备XXXXXXXX号-1`；构建前端时注入（见 §7） |

> `AUTO_CREATE_TABLES=false` 固定不变，建表必须走 Alembic 迁移（见 §5）。

## 5. 阶段 3：数据库迁移（Supabase → 本地 PostgreSQL）

前置：postgres 容器已启动、镜像已构建（见 §6 启动方式），并已用 production.env 完成初始化。

推荐直接运行迁移脚本（dump → restore → alembic → 校验）：

```bash
cd test-platform-v2/scripts
SUPABASE_DATABASE_URL="postgresql://postgres.<ref>:<password>@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres" \
./migrate-tencent-production.sh --env-file ../config/runtime/production.env
```

脚本等价的手动步骤（不跑脚本时按此执行）：

```bash
cd test-platform-v2
export COMPOSE_PROJECT_NAME=cameltv-tp-production
# 1) 备份 Supabase 全库（在任意有 docker 的机器/服务器执行）
mkdir -p /tmp/cameltv-pg && cd /tmp/cameltv-pg
docker run --rm -v "$PWD:/dump" postgres:16-alpine \
  pg_dump "$SUPABASE_DATABASE_URL" -Fc -f /dump/cameltv-prod-$(date +%F).dump

# 2) 恢复进本地 postgres 容器（先确认容器名：docker compose ps）
PG_CONTAINER=$(docker compose --project-name cameltv-tp-production --env-file config/runtime/production.env ps -q postgres)
docker cp /tmp/cameltv-pg/cameltv-prod-*.dump "$PG_CONTAINER":/tmp/cameltv-prod.dump
docker compose --project-name cameltv-tp-production --env-file config/runtime/production.env \
  exec postgres pg_restore -U cameltv -d cameltv_production --clean --if-exists /tmp/cameltv-prod.dump

# 3) 应用/校验迁移（AUTO_CREATE_TABLES=false，必须走 Alembic）
docker compose --project-name cameltv-tp-production --env-file config/runtime/production.env \
  run --rm --no-deps backend python -m alembic upgrade head
docker compose --project-name cameltv-tp-production --env-file config/runtime/production.env \
  run --rm --no-deps backend python -m alembic current   # 期望单头
```

校验：`alembic current` 单头；抽查核心表行数（projects / users / cases / test_plans 等）与 Supabase 迁移前一致。

> ⚠️ 恢复用 `--clean --if-exists` 只对**空的新库**执行；若目标库已有数据，先备份目标库再操作。

## 6. 阶段 4：文件迁移（/app/storage 蓝湖证据与 Cookie）

Railway 后端持久卷 `/app/storage` 含：`lanhu-evidence/`（证据截图、Word/JSON 导出）、`lanhu-data/`（蓝湖 Cookie 与采集缓存）。必须迁到腾讯云服务器的持久卷，否则历史截图"资产文件缺失 404"。

```bash
# 从 Railway 导出（Railway CLI 或控制台下载卷内容）
railway link && railway volume list
# 参考 docs/ops/railway-storage.md 中的挂载点，把 /app/storage 整体下载到本地后上传服务器

# 上传到服务器后，落到 compose 卷对应目录
# 卷由 docker-compose 管理（tp-artifacts:/app/storage、tp-data:/data），
# 迁移期可用 bind mount 直挂目录，例如：
#   /srv/cameltv-storage -> /app/storage
# 用 docker compose run 一次性拷贝进卷：
docker compose --project-name cameltv-tp-production --env-file config/runtime/production.env \
  run --rm --no-deps -v /srv/cameltv-storage:/from:ro backend \
  sh -c 'cp -a /from/. /app/storage/ && chown -R 10001:10001 /app/storage'
```

> 拷贝后验证：启动 backend 后 `[storage] Lanhu evidence storage base` 日志指向持久卷；旧任务"查看截图"能打开。

## 7. 阶段 5：HTTPS + 域名解析 + 备案号（备案通过后执行）

### 7.1 DNS
腾讯云 DNS：`swiftbugs.cn` 添加 A 记录 → 服务器公网 IP（备案通过后才能对外解析访问）。

### 7.2 Caddy 反向代理（自动 HTTPS，推荐）
```bash
sudo apt-get install -y caddy
# /etc/caddy/Caddyfile
swiftbugs.cn {
    reverse_proxy 127.0.0.1:80
    encode gzip
}
sudo systemctl enable --now caddy
```
> 前端容器 `FRONTEND_PORT` 默认映射宿主 80；Caddy 以 443 终止 TLS 后转发到容器 80。`COOKIE_SECURE=true` 依赖 HTTPS，明文 80 只用于健康探测。

### 7.3 备案号 footer
构建前端镜像时传入 `VITE_ICP_NUMBER`（非空时页面底部展示备案号并链接工信部）：

```bash
# 方式一：写在 production.env（compose build 自动读取）
VITE_ICP_NUMBER=粤ICP备XXXXXXXX号-1
docker compose --project-name cameltv-tp-production --env-file config/runtime/production.env build frontend
docker compose --project-name cameltv-tp-production --env-file config/runtime/production.env up -d frontend

# 方式二：手动构建镜像时用 --build-arg
docker build -f test-platform-v2/frontend/Dockerfile \
  --build-arg VITE_ICP_NUMBER=粤ICP备XXXXXXXX号-1 -t cameltv-tp-frontend:latest test-platform-v2/frontend
```

## 8. 阶段 6：启动 + 冒烟 + 切换

### 启动
```bash
cd test-platform-v2
pwsh scripts/start-platform-environment.ps1 -Target production -Action start -ConfirmProduction
# 或等价：
docker compose --project-name cameltv-tp-production --env-file config/runtime/production.env up -d --build
```

### 冒烟（备案通过、安全组放行 80/443 后）
| # | 检查 | 期望 |
|---|------|------|
| 1 | `curl -s https://swiftbugs.cn/api/v1/open/health` | 200 `status=ok` |
| 2 | 浏览器登录（admin） | 200，工作台可进，organizations 返回 |
| 3 | 注册（若开放） | 注册成功并自动登录 |
| 4 | 用例 → 计划 → 执行 → 报告 | 全链路无 5xx |
| 5 | 蓝湖采集任务"查看截图" | 历史/新截图可打开（卷已就位） |
| 6 | 页面底部备案号 | 展示 `粤ICP备XXXXXXXX号-1` 且可点击到 beian.miit.gov.cn |

### 切换与回滚
- **切换**：确认冒烟全过后，将用户入口指向 `https://swiftbugs.cn`；旧 Vercel/Railway/Supabase **保留观察 ≥24h** 再下线。
- **回滚**：
  - 代码：git revert 后重新部署；数据库迁移为增量建表，不破坏存量。
  - 数据：迁移前保留 Supabase 与本地 dump（`cameltv-prod-<date>.dump`），必要时整库重导。
  - 前端：Caddy 可一键回退到旧 Vercel 域名（改 Caddyfile 反代目标）。

## 9. 广东个人备案注意事项

- 网站名称**必须包含本人真实姓氏**，推荐"姓名+的个人+主题"格式；**不得**含"中国/中华/中央"等字头、地域词（"广东XX网"）、行业/经营性词（金融、商城、公司等）。
- 个人备案 = **非经营性**；若将来对外收费运营需转企业备案。
- 备案通过后**主页底部必须展示备案号并链接 beian.miit.gov.cn**（§7.3 footer 已支持）。
- 域名所有者实名信息、备案主体、账号实名必须三者一致。
- 备案省份按**身份证所在省**管局审核（腾讯云建议选个人证件上的省），服务器在广东不影响。

## 10. 常见问题

| 症状 | 处理 |
|------|------|
| 登录后跳回 / 或 401 | `COOKIE_SECURE=true` 但用了 http / 非正式域名访问；确认 ALLOWED_ORIGINS/CSRF 与 Caddy 域名一致 |
| `/api` 502 | backend 未启动：`docker compose logs backend --tail 50` |
| 截图"资产文件缺失" | /app/storage 卷未挂或未迁移：确认 §6 与 `[storage]` 日志 |
| alembic 多头/失败 | `python -m alembic heads` 检查；恢复后先 `alembic current` 再 `upgrade head` |
| 磁盘不足 | 轻量 40G SSD 偏紧（镜像含 Chromium 数个 GB）：加购云硬盘挂到 /var/lib/docker 或卷目录，定期 `docker system prune` |
| 备案未通过前被访问 | 安全组只放行 22；不要提前解析正式域名到大陆服务器 |

## 11. 关联

- 运行时 profile：`test-platform-v2/config/runtime/production.env(.example)`
- 迁移脚本：`test-platform-v2/scripts/migrate-tencent-production.sh`
- 单机 Compose：`test-platform-v2/deploy/docker-compose.yml`
- 蓝湖证据卷：`docs/ops/railway-storage.md`
- 灰度/发布节奏：`docs/灰度放量SOP.md`、`docs/agent-team/release-cadence.md`
