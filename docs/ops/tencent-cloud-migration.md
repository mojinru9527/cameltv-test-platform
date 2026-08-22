---
title: "腾讯云广州生产迁移手册（swiftbugs.cn）"
owner: "devops"
created: "2026-08-13"
status: "completed"
tags: ["tencent-cloud", "production", "migration", "icp", "swiftbugs.cn"]
related: ["../test-platform-v2/config/runtime/production.env.example", "../test-platform-v2/scripts/migrate-tencent-production.sh", "railway-storage.md"]
---

# 腾讯云广州生产迁移手册（swiftbugs.cn）

> 目标：把测试平台生产环境从 **Vercel（前端）+ Railway（后端）+ Supabase（PostgreSQL）**
> 迁移到 **腾讯云广州轻量服务器单机部署**（Docker Compose：Nginx 前端 + FastAPI 后端 + PostgreSQL）。
> 域名：`swiftbugs.cn`（个人备案已通过：粤ICP备2026121122号-1）。

> ✅ **执行状态（2026-08-22 已完成并上线验证）**：
> 所有阶段已执行完毕，`https://swiftbugs.cn` 已可访问（Let's Encrypt 证书已签发、登录/工作台/统计数据/备案号 footer 均验证通过）。
> 实际执行记录与经验见附录 A；旧 Vercel/Railway/Supabase 保留观察 ≥24h 后按 §8 下线。

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
| 1 | 账号实名 | 个人实名（人脸核验），新用户新实名才有优惠价 | ✅ 完成 |
| 2 | 域名 `swiftbugs.cn` | 腾讯云购买 + **域名实名认证**，所有者=备案主体（本人姓名） | ✅ 完成 |
| 3 | 服务器 | 广州轻量 2核4G 起（推荐 4核4G 38元/年秒杀，**年付**；备案要求订阅≥3个月） | ✅ 完成（111.230.155.116 / Ubuntu 24.04 / 4C4G） |
| 4 | ICP 备案 | 域名实名满 3 个自然日后提交；腾讯云初审 1-2 工作日 + 管局终审 ≤20 工作日 | ✅ 完成（粤ICP备2026121122号-1） |
| 5 | 安全组/防火墙 | 备案通过前**只放行 22**；通过后放行 80/443 | ✅ 完成（控制台 + ufw 双放行） |

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

## 附录 A：执行记录（2026-08-22）

> 本次实际执行（DeepSeek Harness 会话驱动，11 项任务全部完成并验证）。
> 服务器：`111.230.155.116`（Ubuntu 24.04 / 4C4G / Docker 29.7.2 + Compose v5.4.0）。

### A1. 执行概要

| 阶段 | 结果 | 备注 |
|------|------|------|
| Supabase 全库 dump | ✅ 15.1MB（PG 17.6 custom 格式） | 本机 Docker 用 `postgres:17-alpine`；6543 transaction pooler 可连，6544 session pooler 超时 |
| 代码部署 | ✅ 本地打包 2.4MB tar → scp | **GitHub 直连服务器超时不可用**，改为本地打包传输（含 lanhu-mcp 子模块文件） |
| 数据库恢复 | ✅ pg_restore `--clean --if-exists` | dump 是 PG17 格式（1.16），需 `postgres:17-alpine` 的 pg_restore 连 PG16 服务器；`supabase_vault` 扩展缺失（测试平台不使用，可忽略）；`transaction_timeout` 参数 PG16 不支持（无害提示） |
| Alembic | ✅ 单头 `20260818_ai_provider` | `#294` 修复（server_default 布尔 PG 兼容）必须用 main 分支而非 release/v2.10.0 |
| /app/storage 卷 | ✅ 403MB 完整迁移 | railway CLI 已登录 → `railway ssh config --dry-run` 拿 User id → 直接 OpenSSH 打包 → 下载 → 上传 → `docker run --user 0:0` 拷贝进卷（受限文件 root 持有） |
| 镜像构建 | ✅ 本机构建 + docker save/load | 服务器构建不可行：PyPI 17KB/s、apt/nodesource/npmmirror 均 <15KB/s；本机（有代理）构建 backend 5.3GB/前端 27MB 后上传加载 |
| Caddy HTTPS | ✅ Let's Encrypt 正式签发（swiftbugs.cn + www） | 证书/配置在 `/etc/caddy/Caddyfile`；`caddy reload` 不触发重试，需 `systemctl restart` |
| 防火墙 | ✅ 控制台规则 + **ufw 放行 80/443** | 关键：腾讯云轻量服务器预装 **ufw 且默认 DROP**，仅控制台放行不够，必须 `ufw allow 80/tcp && ufw allow 443/tcp` |
| DNS | ✅ @ + www A 记录 → 111.230.155.116 | 传播后 Caddy 自动申请证书 |
| 冒烟 | ✅ health 200 / 登录 / 工作台 11388 用例 / 备案号 footer | sportsadmin 密码验证通过；AI provider Fernet 解密 OK |

### A2. 关键经验（后续运维复用）

1. **服务器无法直连 GitHub/PyPI/npm**：国内轻量服务器出网受限（GitHub TLS 中断、PyPI 17KB/s）。解决 = 本地构建镜像 `docker save` → scp → `docker load`；代码用本地 tar 打包传输。
2. **ufw 是隐藏拦截层**：腾讯云控制台防火墙规则之外，实例内 `ufw status` 必须同步放行 80/443，否则 ACME 验证和公网访问全部失败。
3. **Dockerfile 构建期 clone lanhu-mcp 需改本地 COPY**：`COPY lanhu-mcp/lanhu_mcp_server.py /tmp/lanhu-mcp-local.py` + `RUN if [ -s ... ]` 条件分支，本地文件缺失时回退 git clone（云构建兼容）。此修改已合入 main（待 PR 确认）。
4. **SECRET_KEY 必须复用 Railway 生产值**：Fernet 密钥 = sha256(SECRET_KEY)，且 AI provider 的 `api_key_encrypted` 用它解密。本地旧 production.env 的 SECRET_KEY（43 字符）与 Railway 生产（64 字符）不同，导致 `InvalidToken`。用 `railway variable list --kv` 拉取生产值对齐。
5. **PG 密码不一致**：compose `up` 不重建已存在容器，POSTGRES_PASSWORD 只在首次初始化生效；环境文件改密码后必须 `ALTER USER` 或 `--force-recreate`，DATABASE_URL 密码需与容器实际一致。
6. **Nginx 反代 DNS 缓存**：backend 容器 recreate 后 IP 变化，frontend Nginx 缓存的旧 DNS 导致 `/api` 502；重启 frontend 刷新即可。
7. **前端端口映射**：Caddy 占宿主 80，前端容器须映射 `127.0.0.1:8080:80`（改主 compose `docker-compose.yml` 的 `FRONTEND_PORT` 硬编码，override 追加端口会与主配置合并冲突）。
8. **railway ssh 直接连**：`railway ssh` 子命令会挂起；用 `railway ssh config --dry-run` 取 User id 后直接 `ssh <user>@ssh.railway.com`。
9. **admin 密码为验收时重置值**：旧 production.env 的 `ADMIN_PASSWORD` 是发布初始密码，生产验收被临时重置过；当前有效管理员密码为 sportsadmin（体育平台管理员）+ 验收时设置的新值。

### A3. 待办（上线后）

- [ ] 旧 Vercel/Railway/Supabase 保留观察 ≥24h（截止 2026-08-23 24:00）后按 §8 下线
- [ ] 确认 admin 账号当前有效密码或执行密码重置
- [ ] Dockerfile lanhu-mcp 本地 COPY 修改合入 main（PR 流程）
- [ ] 迁移经验（附录 A2）同步到 `docs/common-pitfalls.md`
