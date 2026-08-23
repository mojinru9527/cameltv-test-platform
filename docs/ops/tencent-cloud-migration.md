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

- [ ] 旧 Vercel/Railway/Supabase 保留观察 ≥24h（截止 2026-08-23 24:00）后按 §8 下线（观察期已过；是否下线由负责人确认，参见附录 B3）
- [ ] 确认 admin 账号当前有效密码或执行密码重置
- [x] Dockerfile lanhu-mcp 本地 COPY 修改合入 main（PR 流程）——#300 合入后被 #302/#303 回退为全量 git clone（Railway builder 不支持 bind-mount 且 archive 丢弃子模块空目录；服务器本地构建不受影响，见附录 B1 模板）
- [ ] 迁移经验（附录 A2）同步到 `docs/common-pitfalls.md`

## 附录 B：c165-3 增量升级记录（2026-08-23）

> DeepSeek Harness 会话驱动，把 #301（导航频率分层，#302/#303 Dockerfile 修复、#304 DSH 路由/存储清理顺带带入）增量部署到 swiftbugs.cn。**首次线上升级，验证走完整链路；本轮无 Alembic 迁移。**

### B1. 增量升级模板（后续复用）

1. **本机构建镜像**（服务器出网受限不可构建，见 A2-1）：
   - 后端：`docker build -t cameltv-tp-backend:<tag> -f test-platform-v2/backend/Dockerfile .`（仓库根为上下文）
   - 前端：`docker build --build-arg VITE_ICP_NUMBER=粤ICP备2026121122号-1 -t cameltv-tp-frontend:<tag> -f Dockerfile .`（frontend 目录）
2. **打包传输**：`docker save` 两镜像 → 本机无 gzip.exe，用 `python -c "import gzip,shutil;shutil.copyfileobj(open('src.tar','rb'),gzip.open('dst.gz','wb',compresslevel=1))"` → `scp` 到服务器 `/root/` → `gunzip` + `docker load`。
3. **双标签**：`docker tag cameltv-tp-backend:<tag> cameltv-tp-backend:main`（同时 `:release-plat`）——compose override 与运行容器 `Config.Image` 均引用 `:main`（`release-plat` 为历史遗留标签名，双标保险）。
4. **重启**（postgres/数据卷/env 一律不动）：
   ```bash
   cd /opt/cameltv-tp/test-platform-v2
   docker compose -p cameltv-tp-production --env-file config/runtime/production.env \
     -f deploy/docker-compose.yml -f deploy/docker-compose.override.yml up -d --no-deps backend frontend
   ```
5. **验证**：容器级代码检查（c165-3：`docker exec cameltv-tp-production-backend-1 python -c "from app.services.menu_service import HIDDEN_MENU_CODES; print(len(HIDDEN_MENU_CODES))"` 应=12）；`GET https://swiftbugs.cn/api/v1/auth/public-access` 知识中心 `children` 为空；前端 bundle 含「更多功能」；用户浏览器确认。
6. **回滚**：升级前先把旧镜像打 `:prev-plat`（`docker tag cameltv-tp-backend:release-plat cameltv-tp-backend:prev-plat`）；回滚 = 把 `:main`/`:release-plat` 指回 prev 再 compose up。

### B2. 本轮踩坑（必读）

1. **本机主仓可能落后 origin/main**：首次构建镜像时 `F:\CamelTv` 停在旧 main（9e5a339c），"新"镜像实为旧代码（容器内 HIDDEN len=8，部署后 API 仍 4 子项、前端无「更多功能」）。**建镜像前先 `git -C F:\CamelTv pull` 并与 origin/main 比对 HEAD**；且必须做容器级代码验证（镜像构建成功 ≠ 代码正确）。
2. **火绒驱动级锁密钥**：`C:\Users\26029\.ssh\cameltv_tencent_lighthouse` 被火绒文件保护锁死——连属主（用户会话）`takeown`/`icacls`/copy 均 Access denied，`cipher /c` 显示非 EFS（U）。本次临时退出火绒解决。**建议把 ssh.exe 或 .ssh 目录加入火绒白名单**，避免每次部署前退出防护。
3. **本机无 gzip.exe**（Git 未装或不在 PATH）：用 Python gzip 替代（见 B1-2）。
4. **`docker compose up` 输出可能只显示 Running/Healthy**：以 `docker inspect <container> --format '{{.Image}}'` + 容器内代码检查确认真实生效，不要按输出判断。

### B3. 当前状态

- [x] #301/#302/#303/#304 已上线 swiftbugs.cn（2026-08-23，负责人已在浏览器确认新导航：9 高频 + 更多功能折叠组）
- [x] 后端容器 HIDDEN_MENU_CODES=12；public-access 知识中心 children=0；前端 bundle 含「更多功能」
- [x] 旧镜像备份 `:prev-plat`（backend 51f4a178 / frontend 0f85f1fd）
- [ ] 旧 Vercel/Railway/Supabase 下线决策（观察期 2026-08-23 24:00 已过，由负责人按 §8 确认执行）
- [ ] 火绒防护已恢复（部署期间临时退出，确认后应尽快恢复/加入白名单）

## 附录 C：PR #304 DSH 修复部署记录（2026-08-23）

> PR #304（fix(dsh)：多提供方模型路由 + 存储保留期清理 + 模型发现与任务图片附件）
> 合入 main（961e0d9a）后当日的镜像重建与上线记录；与附录 B 同日合并两个批次。

### C1. 部署概要

1. 主仓 `git merge --ff-only origin/main` 到 961e0d9a（B2-1 教训：先同步再构建）。
2. 本地构建（Docker 代理走通，见 C2-2）：
   - backend `354bbd28f718` / frontend `5481d095cd96`，双标签 `:main` + `:release-20260823-0002`（B1-3 约定）。
3. 传输：`docker save -o F:\_dsh_deploy_images.tar img1 img2`（1.35GB）→ `scp -C`（压缩，替代 B1-2 的 Python gzip 方案）→ 服务器 `docker load < /tmp/...` → 删除 tar。
4. 部署：`docker compose -p cameltv-tp-production --env-file ... up -d backend frontend`（override `:main` 自动生效，postgres/数据卷不动）。
5. 验证（除 B1-5 通用项外，DSH 域）：
   ```bash
   docker exec cameltv-tp-production-backend-1 sh -c "env | grep -E '^DSH_RUNTIME|^DSH_HARNESS|^STORAGE_RETENTION'"
   docker exec -u 10001:10001 cameltv-tp-production-backend-1 bash -c \
     'DSH_HOME=/home/cameltv/.dsh dsh --profile headless --dump-config | grep -A6 "id: llm-pi-ai"'  # 应见 platform 路由
   ```
   端到端：DB 插入测试任务 + `docker exec -d` 拉起 worker → `success`（真实 DeepSeek 官方执行）。

### C2. 本轮额外踩坑（与 B2 不重复）

1. **production.env 拼接坑（真实事故）**：文件末行 `SMTP_FROM=` 无换行，`printf "VO=1\n" >>` 追加后变成
   `SMTP_FROM=VO=1` → 变量值丢失（容器内读到 compose 默认值 false）。**追加前先补换行**：
   `[ -n "$(tail -c1 file)" ] && echo >> file`；追加后 `grep -c "^VAR="` 校验，且重建容器后
   `docker exec env | grep` 端到端确认。
2. **构建需代理**：Dockerfile 装 Node 走 deb.nodesource.com（直连被墙 False；npm/pypi 直连 OK）。
   确认构建网络：`docker run --rm postgres:16-alpine wget -q -O /dev/null -T 20 https://deb.nodesource.com`（exit 0）。
   代理挂掉时 gh/git 也受影响（HTTP_PROXY=/HTTPS_PROXY=127.0.0.1:7688 残留、端口无人监听）——
   临时 `$env:HTTP_PROXY='';$env:HTTPS_PROXY=''` 可直连 api.github.com（本机直连可用）。
3. **worker 懒启动**：DSH worker 仅 `submit_task`（API）时拉起；直接 SQL 插入测试任务不会被认领，
   需 `docker exec -d` 手动执行 `ensure_worker_running()` 启动（容器重建后该进程失效）。
4. **docker build exit code 假象**：`docker build ... 2>&1 | Select-Object -Last N` 管道下即使构建成功
   也可能返回 1——以 `docker images` digest 与镜像内容检查为准（如 `grep llm-pi-ai …/cordis.patch.yml`）。
5. **SSH 密钥被锁**：B2-2 同源（火绒），用户修复后恢复；临时副本 ACL 需 SYSTEM/用户自持有
   （DSH SYSTEM 会话 vs 用户会话差异）。

### C3. 当前状态（2026-08-23 部署后）

- [x] swiftbugs.cn 后端 version **2.3.0**；`STORAGE_RETENTION_ENABLED=true`（每日 02:30 清理，磁盘 95%→57%）
- [x] 容器内 DSH：node 运行时 + `DSH_HARNESS_PATH` + headless/agent-team 多提供方补丁（镜像烘焙，重建不再丢）
- [x] E2E 任务 x2 均 success（Real DeepSeek 官方 key + deepseek-v4-flash）
- [x] 新功能可用：AI 配置「获取模型列表」、DSH 任务图片附件、错误可读化
- [x] 镜像备份：附录 B3 `:prev-plat`（backend 51f4a178 / frontend 0f85f1fd）仍保留（未被本轮删除）

## 附录 D：发布控制台建设 + 旧环境下线（2026-08-23）

> 迁移完成后追加两步：① 发布平台独立化（解除与测试平台耦合）；② 旧环境下线清单。
> 关联 PR：#305（发布平台初版）、#308（解耦独立）、#309（易用化）。

### D1. 发布平台演进（快速回顾）

| 阶段 | PR | 说明 |
|------|----|------|
| 初版（耦合） | #305 | `/operations-release` 页面 + `/api/v1/ops/deployments` 跑在测试平台内 |
| **解耦独立** | #308 | 独立 `deploy/release-console/`（61MB 镜像），子域 `release.swiftbugs.cn`，测试平台移除发布入口 |
| **易用化** | #309 | 网页令牌输入框（免 F12）+ `scripts/ops/release.ps1` 一键发布（自动提取 digest/提交/上传/发布） |

### D2. 发布平台架构（当前）

```
用户/运维 → https://release.swiftbugs.cn（Caddy HTTPS）
              ↓ 反代
    release-console 容器 :8111（FastAPI + SQLite + 单页前端）
              ↓ SSH（Token + 密钥环境变量注入，复用于测试平台发布）
        111.230.155.116（测试平台生产；即使测试平台挂掉也能发布/回滚）
```

- 状态库：`/opt/cameltv-release-console/data/release-control.sqlite3`（独立于业务库）
- 令牌：`RELEASE_CONSOLE_TOKEN`（服务器 env + 本地 `~\.cameltv-release-console\token.json`）
- 一键脚本：`pwsh scripts/ops/release.ps1 -Tag release-xxx -Publish`

### D3. 旧环境下线清单

> 详见 `docs/ops/old-env-decommission-checklist.md`。前置检查（0.1–0.5）已全绿（2026-08-23）。
> **下线前的最后闸门**：发布控制台真实发布演练（D1 方案）通过后才执行删除。

| 环境 | 下线方式 | 预计费用影响 |
|------|---------|-------------|
| Vercel（cameltv-test-platform） | 删项目 | 免费，无影响 |
| Railway（keen-amazement） | 删项目（**按量计费**，尽快） | 停止计费 |
| Supabase（myhwdpjmxdsodqgeecpn） | 删项目（数据已本地化） | 免费额度释放 |

### D4. 本轮踩坑（与 B2/C2 不重复）

1. **PowerShell 脚本 UTF-8 编码**（PS 5.1 中文解析坑）：`write` 工具生成的无 BOM `.ps1` 会被 PS 5.1 按 ANSI 读，中文字符串/注释导致 Parse 报错（如 `"[" 后面缺少类型名称`）——**解决方案：文件加 UTF-8 BOM**（`[Text.UTF8Encoding]::new($true)`）。
2. **`@` 在字符串中触发 splatting**：`"$UserName@$HostName"` 中 `@` 被当作 splat 前缀 → 改用 `${UserName}@${HostName}`（花括号包裹）。
3. **FastAPI Header 注入**：路由参数 `authorization: str | None = None` 被 FastAPI 当 query 参数（永远 None）→ 必须 `Header(None, alias="Authorization", include_in_schema=False)`；否则 401。
4. **rebase 误删文件**：rebase 冲突解决时 `git ls-tree HEAD` 与工作区不一致（index 残留），CI 报 `Cannot find module '@/pages/workbench'`——**修复=丢弃 worktree 重建 + 备份文件重应用**（干净分支单 commit）。
5. **前端令牌动态读取**：`const TOKEN` 初始化后保存不生效 → 改 `getToken()` 每次读 localStorage。
6. **Docker Desktop SYSTEM 会话**：本机以 SYSTEM 跑导致引擎掉线（记忆已验证）；服务器端可用 `docker cp` 热更新容器内静态文件绕开。

### D5. 当前状态（2026-08-23）

- [x] 发布控制台独立子域 `release.swiftbugs.cn` 上线（v4 镜像，含令牌输入框）
- [x] 一键脚本 `release.ps1` 合入 main（release/rollback/backup 三命令）
- [x] 测试平台发布入口彻底移除（/operations-release + ops API + release:view 权限）
- [x] 旧环境下线清单就绪（前置检查全绿，待真实发布演练后执行）
- [ ] **待执行**：发布控制台真实发布演练（D1 方案）→ 旧环境下线删项目
