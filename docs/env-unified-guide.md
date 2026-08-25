  CamelTv 测试平台 — 环境变量统一入口指南（C152-1）

> Batch 154（2026-08-11）新增。目标：一份文档说清所有 env 文件与唯一入口，避免分散配置。

   1. 统一入口（唯一事实源）

**本地开发一律通过 launcher 启动，它统一读取/生成运行时配置：**

```powershell
pwsh test-platform-v2/scripts/start-platform-environment.ps1 -Target local -Action start -InstallDeps -InitializeLocal
```

- 运行时 profile：`test-platform-v2/config/runtime/local.env`（生成 + 读取的唯一配置入口，已 gitignore）
- 首次用 `-InitializeLocal` 自动生成；`ADMIN_PASSWORD` 等密钥只存在该文件
- 生产/测试目标：`config/runtime/{target}.env`（由部署流程注入）

   2. env 文件清单（5 份）

| 文件 | 用途 | 是否入库 | 备注 |
|------|------|---------|------|
| `test-platform-v2/backend/.env` | 后端运行时（数据库/密钥） | 否（gitignore） | 本地由 launcher/手动创建 |
| `test-platform-v2/backend/.env.example` | 后端变量模板 | 是 | 改后端配置时同步 |
| `test-platform-v2/frontend/.env.local` | 前端 Vite 端口/代理 | 否（gitignore） | worktree 隔离时由任务脚本生成 |
| `test-platform-v2/frontend/.env.example` | 前端变量模板 | 是 | |
| `test-platform-v2/deploy/.env.example` | 部署/容器变量模板 | 是 | 生产用，密钥由 CI/CD Secret 注入 |

> 说明：仓库已无「7 份 env」中的其余重复文件；本清单为当前全部。统一入口为 launcher + `config/runtime/`。

   3. 校验

```powershell
pwsh scripts/env-inventory.ps1
```

输出：各 env 文件是否存在、关键变量是否缺失（只读，不修改任何文件）。

   4. 约定

1. 新增环境变量：先改 `.env.example`，再同步 `scripts/env-inventory.ps1` 的必填清单。
2. 密钥（DB 密码/Token/AI Key）禁止写入 git；一律放运行时 profile 或 CI Secret。
3. worktree 隔离：每个任务 worktree 使用独立 `.env.local`（`VITE_DEV_PORT`/`VITE_PROXY_TARGET`）与独立 SQLite，端口见 `.ai-worktree.json`。
