# CamelTv 测试平台 — 空白机本地搭建引导

> **适用范围**：全新 Windows / macOS 机器从零搭建 test-platform-v2（前端 + 后端 + 本地 SQLite）。
> **维护**：Batch 152（2026-08-11）新增；随启动方式变化同步更新。

## 1. 前置要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | 3.10-3.12 | 后端（FastAPI/SQLAlchemy） |
| Node.js | >=22.22 | 前端（Vite 7） |
| npm | >=10 | 前端包管理（仓库使用 package-lock.json，勿用 pnpm） |
| Git | 任意 | 拉取仓库与子模块（lanhu-mcp 需初始化） |

## 2. 拉取代码

```bash
git clone --recurse-submodules https://github.com/mojinru9527/cameltv-test-platform.git
cd cameltv-test-platform
# 若未带子模块克隆：
git submodule update --init --recursive
```

> ⚠️ **国内网络**：云服务器/受限网络直连 `github.com` 可能超时（2026-08-22 腾讯云迁移实测：
> GitHub TLS 中断、PyPI ~17KB/s、npm 镜像 <15KB/s）。替代方案：
> ① 在可联网机器 `git clone`（含子模块）后打 tar 上传：`tar czf cameltv-platform.tar.gz --exclude=.git cameltv-test-platform`；
> ② 用 GitHub 加速代理/镜像站替换 URL 前缀；
> ③ 服务器本地构建镜像时 lanhu-mcp 走 `test-platform-v2/backend/Dockerfile.local`（COPY 子模块，不走 git clone）；
> ④ 生产部署完整 SOP 见 `docs/ops/tencent-cloud-migration.md`。

## 3. 一键启动（推荐）

Windows PowerShell / macOS Terminal：

```powershell
pwsh test-platform-v2/scripts/start-platform-environment.ps1 `
  -Target local -Action start -InstallDeps -InitializeLocal
```

- `-InstallDeps`：安装后端 `pip install -r requirements.txt` 与前端 `npm ci`（首次必带）。
- `-InitializeLocal`：首次生成忽略的本地运行时 profile（`config/runtime/local.env`），并打印初始 ADMIN_PASSWORD（请保存）。
- 启动后：前端 http://localhost:5173，后端 http://localhost:8000/docs，数据库 SQLite（backend/data/）。

## 4. 手动启动（不依赖 launcher）

```bash
# 后端
cd test-platform-v2/backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 前端（另开终端）
cd test-platform-v2/frontend
npm ci
npm run dev   # http://localhost:5173（/api 代理到 127.0.0.1:8000）
```

## 5. 首次登录

1. 打开前端，用 `admin` + 启动日志中的初始 `ADMIN_PASSWORD` 登录。
2. 首次登录会强制修改密码。
3. 在「系统管理」创建其他用户并分配角色；按项目隔离数据。

## 6. 常见问题

| 问题 | 处理 |
|------|------|
| 前端 5173 起不来（端口占用） | 检查是否有旧 Vite 进程；或用 `.env.local` 的 `VITE_DEV_PORT` 换端口并同步 `VITE_PROXY_TARGET` |
| 后端 8000 被占用 | 修改 `config/runtime/local.env` 的 `BACKEND_PORT`，并保证 `FRONTEND_PORT` 与 Vite 端口一致 |
| 迁移/表结构异常 | `cd test-platform-v2/backend && python -m alembic upgrade head` |
| 登录提示无权限 | 确认 `X-Project-Id` 对应项目存在；管理员账号默认 `admin` |
| 需要 PostgreSQL | 见 `test-platform-v2/docs/PostgreSQL迁移指南.md`（本地默认 SQLite） |

## 7. 每日开发循环

```bash
git pull --rebase
pwsh test-platform-v2/scripts/start-platform-environment.ps1 -Target local -Action start
```

停止：Ctrl+C，或对 local 执行 `-Action status` 查看监听进程后手动结束。
