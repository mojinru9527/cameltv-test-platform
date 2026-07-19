---
title: "CamelTv 常见陷阱与已知问题"
owner: "qa-team"
last_reviewed: "2026-06-26"
status: "active"
expires: "2026-12-26"
tags: ["pitfalls", "troubleshooting", "known-issues", "debugging", "onboarding"]
related: ["CLAUDE.md", "test-platform-v2/CLAUDE.md", "lanhu-mcp/CLAUDE.md", "tests/CLAUDE.md"]
---

# CamelTv 常见陷阱与已知问题

> 本文档记录 CamelTv 项目开发/测试/部署中反复出现的陷阱和已知问题。目标：避免新人/AI 重复踩坑，加速问题排查。
>
> **维护规则**：遇到新陷阱时立即追加。代码审查时若发现某问题反复出现，评估是否应写入此处。每个条目包含问题描述、根因、解决方案和相关文件。

---

## 1. 后端陷阱

### 1.1 APScheduler 重复启动

**现象**：定时任务被重复触发多次，同一任务同时执行多份。

**根因**：开发模式使用 `uvicorn --reload` 或 Gunicorn 多 worker 模式时，uvicorn 会创建多个子进程，每个 worker 都会初始化 APScheduler 实例，导致同一个任务在多个 worker 中同时执行。

**解决方案**：
```python
# backend/app/main.py — 在 scheduler 初始化时加锁
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
if not scheduler.running:  # 或检查 scheduler.state == 0
    scheduler.start()
```

**更好的方案**：在生产环境通过环境变量控制只在主进程中启动 scheduler：
```python
import os
if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not os.environ.get("ENVIRONMENT"):
    scheduler.start()
```

**相关文件**：`test-platform-v2/backend/app/main.py`、`test-platform-v2/backend/app/api/v1/schedule.py`

---

### 1.2 SQLite 并发写入冲突

**现象**：高并发写入场景下出现 `database is locked` 错误。

**根因**：SQLite 即使在 WAL (Write-Ahead Logging) 模式下，写操作仍然是串行的。当多个请求同时尝试写入（如批量创建用例、并发执行记录提交），SQLite 的写锁会导致后续写入请求排队等待或超时。

**解决方案**：
1. 确保连接字符串启用了 WAL 模式：`sqlite:///./data.db?check_same_thread=False`（SQLAlchemy 默认会自动启用 WAL）
2. 在 Service 层对高频写入操作添加重试逻辑或写队列
3. 部署条件成熟后迁移到 PostgreSQL（Alembic 已准备好升级路径）

**预防措施**：
- 避免在代码中使用 SQLite 特有语法（如 `datetime('now')`），使用 SQLAlchemy 的标准函数（`func.now()`）
- 批量写入操作使用事务包裹，减少锁持有时间
- 监控 `SQLITE_BUSY` 错误率

**相关文件**：`test-platform-v2/backend/app/core/db.py`、`docs/adr/0002-sqlite-with-postgresql-upgrade-path.md`

---

### 1.3 Alembic 迁移冲突

**现象**：多人开发时出现迁移版本号冲突、auto-generation 生成的迁移脚本不正确。

**根因**：
- 两个开发者分别创建了相同版本号（revision ID）的迁移 → 版本树分叉
- `--autogenerate` 可能遗漏某些 schema 变更（如枚举类型修改、表重命名）
- 迁移脚本中手动修改后未更新 `down_revision`

**解决方案**：
1. **提交前必做**：
   ```bash
   cd test-platform-v2/backend
   alembic upgrade head      # 先同步到最新
   alembic revision --autogenerate -m "描述"  # 再生成新迁移
   ```
2. **检查生成的迁移脚本**：打开 `alembic/versions/` 下生成的文件，确认：
   - `upgrade()` 包含所有预期 table/column 变更
   - `downgrade()` 能正确回滚
   - `down_revision` 指向正确的上一个版本号
3. **合并冲突**：如果出现分叉，使用 `alembic merge` 创建合并迁移

**相关文件**：`test-platform-v2/backend/alembic/`、`test-platform-v2/backend/alembic/env.py`

---

### 1.4 AI/LLM 调用超时

**现象**：大需求文档（如完整 PRD）调用 DeepSeek LLM 生成用例时超时，前端长时间无响应。

**根因**：DeepSeek API 对长文本请求的处理时间可能超过 HTTP 客户端默认超时（通常 30-60s），大文档时尤甚。

**解决方案**：
1. 后端 `ai_service.py` 中设置合理的 timeout + retry：
   ```python
   import httpx
   client = httpx.AsyncClient(timeout=120.0)  # 2 分钟
   ```
2. 对于超大文档，先分片成多个小块再分别调用（chunk-based processing）
3. 前端增加 SSE (Server-Sent Events) 或轮询机制，避免长时间无反馈
4. 如果超时频繁，评估是否需要切换到支持更长上下文窗口的模型

**相关文件**：`test-platform-v2/backend/app/services/ai_service.py`、`test-platform-v2/backend/app/core/config.py`

---

### 1.5 CORS 配置遗漏

**现象**：前端请求被浏览器 CORS 策略拦截，报错 `Access-Control-Allow-Origin` 缺失。

**根因**：
- 本地开发时 `allow_origins=["*"]` 在 `main.py` 中配置，但新增部署源域名后未更新
- 生产环境 CORS 由 Nginx 处理，但后端的 CORS middleware 可能与之冲突（双重 CORS 头）
- 带 credentials (cookies/Authorization 头) 的请求不能使用 `*`，必须指定具体 origin

**解决方案**：
1. **本地开发**（test-platform-v2/backend/app/main.py）：
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:5173", "http://localhost:3000"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```
2. **生产环境**：CORS 由 Nginx 统一处理（`add_header Access-Control-Allow-Origin`），后端移除或设为允许 localhost 即可
3. **新增前端部署地址**时，同步更新 CORS 白名单

**相关文件**：`test-platform-v2/backend/app/main.py`、`test-platform-v2/deploy/nginx.conf`

---

### 1.6 .env 安全校验失败

**现象**：生产模式下启动后端报错 `SecurityError: SECRET_KEY must be changed from default`。

**根因**：`.env` 中的 `SECRET_KEY` 和 `JWT_SECRET` 使用默认值，生产模式下 `core/config.py:Settings.validate_security()` 会拒绝启动。

**解决方案**：
1. 为每个环境生成独立的强密钥：
   ```bash
   openssl rand -hex 32  # 生成 64 字符 hex 密钥
   ```
2. Jenkinsfile Deploy 阶段自动替换：
   ```groovy
   sed -i "s/please-change-me.*/$(openssl rand -hex 32)/" .env
   ```

**相关文件**：`test-platform-v2/backend/app/core/config.py`、`test-platform-v2/backend/.env.example`

---

## 2. 前端陷阱

### 2.1 Demo 状态模块（演示态）

**现象**：`/apitest`、`/uitest`、`/special` 三个模块数据不真实，刷新后数据变化。

**根因**：这三个模块的数据由前端纯 `Math.random()` 生成，不连接真实后端服务。它们是 v2 前端开发初期的演示占位模块。

**识别方法**：
- 页面数据刷新后随机变化
- 无对应的后端 API 调用（Network 面板无 `/api/v1/apitest` 等请求）
- v2 CLAUDE.md 模块成熟度表中标记为 🧪 演示态

**正确预期**：这三个模块不用于生产测试，不要误认为功能已完善。实际 API 测试使用 v1 的 `tp api` CLI，实际 UI 自动化使用 `tests/automation/ui/` 下的 Playwright 脚本。

**相关文件**：`test-platform-v2/CLAUDE.md`（功能模块成熟度表）

---

### 2.2 JWT 过期处理

**现象**：用户频繁被踢出登录，或登录后很快过期。

**根因**：
1. Axios 拦截器在收到 401 时自动清除 token 并跳转登录页
2. 如果后端改了 `ACCESS_TOKEN_EXPIRE_MINUTES`（默认值在 `.env` 中），前端不会感知
3. token 刷新逻辑可能未正确处理 refresh_token 过期的情况

**排查步骤**：
1. 检查后端 `.env` 中的 `ACCESS_TOKEN_EXPIRE_MINUTES` 和 `REFRESH_TOKEN_EXPIRE_DAYS`
2. 打开浏览器 DevTools → Application → Local Storage，确认 token 存储正常
3. 如果出现频繁 401，先用管理员分配的测试账号重新登录
4. 清除 localStorage 后重新登录：`localStorage.clear()`

**预防措施**：在前端 Axios 拦截器中增加 token 过期前的静默刷新逻辑。

**相关文件**：`test-platform-v2/frontend/src/api/`（Axios 配置和拦截器）、`test-platform-v2/frontend/src/stores/authStore.ts`

---

### 2.3 shadcn/ui 源码复制模式

**现象**：升级 shadcn/ui 后样式异常、组件行为改变。

**根因**：shadcn/ui 不是通过 npm 安装的依赖包，而是通过 `npx shadcn-ui@latest add` 将组件**源码复制**到 `src/components/ui/` 目录。这意味着：
- 版本变更时不存在 `npm update` 的自动升级路径
- 手动修改过的组件文件和 shadcn 上游不兼容
- 组件依赖的 Radix UI 和 Tailwind CSS 版本可能脱节

**解决方案**：
1. **不要手动修改 `src/components/ui/` 下的 shadcn 基础组件文件**。如需定制，在业务组件层做包装
2. 升级时：备份当前 ui 目录 → 重新执行 `npx shadcn-ui@latest add` → diff 比较差异 → 手动合并业务定制
3. 使用 shadcn 的 `components.json` 配置文件管理安装列表

**相关文件**：`test-platform-v2/frontend/components.json`、`test-platform-v2/frontend/src/components/ui/`

---

### 2.4 Zustand persist hydration 问题

**现象**：刷新页面后状态异常，或持久化数据与新代码不兼容。

**根因**：
1. authStore 使用 Zustand 的 `persist` middleware 将状态序列化到 localStorage
2. 如果 store 的 state 结构变更（新增/删除字段），localStorage 中的旧数据可能与新结构不兼容
3. 序列化/反序列化过程中，Date 对象、函数等特殊类型会丢失

**排查步骤**：
1. 打开浏览器 DevTools → Application → Local Storage，查看 `auth-storage`（或对应 store key）的值
2. 如果结构异常，执行 `localStorage.removeItem('auth-storage')` 并刷新页面
3. 开发时可在 Zustand persist 配置中设置 `version` 和 `migrate` 函数处理结构变更

**预防措施**：
```typescript
// 示例：为持久化添加版本号和迁移
persist(
  (set) => ({ ... }),
  {
    name: 'auth-storage',
    version: 1,
    migrate: (persistedState, version) => {
      // 处理跨版本数据结构变更
      return persistedState;
    },
  }
)
```

**相关文件**：`test-platform-v2/frontend/src/stores/authStore.ts`

---

### 2.5 Vite 代理未生效

**现象**：前端 `npm run dev` 启动后，API 请求返回 404 或 CORS 错误。

**根因**：Vite 开发服务器代理配置（`vite.config.ts`）只在开发模式生效。生产构建后的 Nginx 使用不同的代理规则。

**排查步骤**：
1. 确认 `vite.config.ts` 中的 proxy target 指向正确的后端地址：
   ```ts
   server: {
     proxy: {
       '/api': 'http://localhost:8000'
     }
   }
   ```
2. 如果后端在远程，修改 proxy target 为远程地址
3. 检查后端是否已启动：`curl http://localhost:8000/health`

**相关文件**：`test-platform-v2/frontend/vite.config.ts`

---

## 3. 蓝湖 MCP 陷阱

### 3.1 Cookie 过期

**现象**：MCP 服务器返回空数据或认证错误。

**根因**：蓝湖 Cookie 有有效期，过期后需要重新获取。Cookie 在 `lanhu-mcp/.env` 中配置。

**解决方案**：
1. 按照 `GET-COOKIE-TUTORIAL.md` 中的步骤重新获取 Cookie
2. 更新 `.env` 中的 Cookie 值
3. 重启 MCP 服务器

**预防措施**：定期检查 Cookie 有效性。如果频繁过期，检查蓝湖账号的登录策略。

**相关文件**：`lanhu-mcp/GET-COOKIE-TUTORIAL.md`、`lanhu-mcp/.env`

---

### 3.2 Edge 浏览器 CDP 端口冲突

**现象**：MCP 启动时报错 `Address already in use` 或浏览器自动化失败。

**根因**：MCP 使用 msedge.exe + CDP (Chrome DevTools Protocol) 远程调试端口 9222。该端口被以下情况占用：
- 另一个 MCP 实例正在运行
- 手动启动了 Edge 的远程调试模式
- 其他 DevTools 工具占用了该端口

**解决方案**：
1. 检查端口占用：`netstat -ano | findstr 9222`（Windows）/ `lsof -i :9222`（macOS/Linux）
2. 终止占用进程或重启
3. 如果确实需要修改端口，在启动命令中指定：`--cdp-port 9223`

**相关文件**：`lanhu-mcp/lanhu_mcp_server.py`、`lanhu-mcp/extract_cdp.py`

---

### 3.3 版本缓存问题

**现象**：蓝湖原型更新后，MCP 提取的内容未变更。

**根因**：MCP 基于蓝湖 `versionId` 做增量缓存。如果蓝湖创建了新版本但 `versionId` 未更新（某些编辑不产生新版本号），缓存可能不会失效。

**解决方案**：
1. 强制清除缓存：删除 `lanhu-mcp/` 下的 `cache/` 目录
2. Docker 部署时：`docker compose down -v && docker compose up -d`
3. 确认蓝湖项目页面的「更新日志」中版本号是否已变更

**相关文件**：`lanhu-mcp/lanhu_mcp_server.py`（缓存逻辑）

---

### 3.4 Playwright Chromium 版本不匹配

**现象**：MCP 启动后浏览器启动失败，报错 `BrowserType.launch: Executable doesn't exist`。

**根因**：Playwright 安装的 Chromium 与系统环境不匹配，或首次启动时未执行 `playwright install chromium`。

**解决方案**：
1. 重新安装：`python -m playwright install chromium`
2. 如果使用 Docker，确保 Dockerfile 中正确安装了 Playwright 及其浏览器依赖
3. 在 Windows 上确保没有杀毒软件拦截 Chromium 执行

**相关文件**：`lanhu-mcp/Dockerfile`、`lanhu-mcp/quickstart.bat`

---

## 4. 测试陷阱

### 4.1 P0 用例与 Playwright spec 的双向追溯

**现象**：修改功能用例后，对应的 Playwright 自动化脚本未同步更新，导致 CI 自动化与用例不一致。

**根因**：P0 级别的功能用例和 Playwright TypeScript 规格文件之间存在双向追溯关系。功能用例变更时，Playwright spec 需要相应更新，反之亦然。这个对应关系容易在多人协作中被忽略。

**解决规则**：
1. 修改功能用例（`tests/test-cases/functional/P0-*/`）→ 同步检查 `tests/automation/ui/` 下的 Playwright spec 是否需要更新
2. 修改 Playwright spec → 确认对应的用例标注是否需要调整
3. CI 自动化失败时，首先确认是用例过期还是代码 bug

**相关文件**：`tests/test-cases/functional/`、`tests/automation/ui/`

---

### 4.2 TypeScript 类型安全（API 契约同步）

**现象**：API 测试执行时报类型错误，或后端 API 变更后前端的类型定义未更新。

**根因**：
1. API 测试（`tests/api-testing/`）是 TypeScript 项目，必须先通过 `npx tsc --noEmit` 类型检查再执行
2. 前端类型通过 `openapi-typescript` 从后端 `/openapi.json` 自动生成，如果后端 API 变更后未重新生成，类型就不一致
3. 手写的接口请求代码没有类型守卫

**解决方案**：
1. API 测试开发迭代的标准流程：
   ```bash
   tp api pull --source "tests/api-testing/specs/cameltv-openapi.yaml"
   cd tests/api-testing/generated
   npm install
   npx tsc --noEmit  # 0 错误才算通过
   ```
2. 前端类型同步：
   ```bash
   cd test-platform-v2/frontend
   npx openapi-typescript http://localhost:8000/openapi.json -o src/api/schema.d.ts
   ```
3. **不要手动维护** `api.d.ts` 或类似的类型声明文件

**相关文件**：`tests/api-testing/`、`test-platform-v2/frontend/src/api/`

---

### 4.3 v1 和 v2 端口冲突

**现象**：启动第二个服务时报 `Address already in use`。

**根因**：v1 和 v2 都使用相同的默认端口：
- 后端：都是 8000
- 前端：都是 5173

同时启动 v1 和 v2 会导致端口冲突。

**解决方案**：
1. **不要同时启动 v1 和 v2**——优先使用 v2
2. 如果需要同时运行，在启动命令中指定不同端口：
   ```bash
   # v2 使用默认端口
   uvicorn app.main:app --port 8000
   # v1 使用备用端口
   uvicorn server.main:app --port 8001
   ```

**相关文件**：`COMMANDS.md`、`test-platform-v2/backend/app/main.py`、`test-platform/server/main.py`

---

### 4.4 测试数据污染

**现象**：测试执行后数据库中残留测试数据，影响下次测试结果。

**根因**：功能测试和自动化测试在共享数据库中创建/修改数据，但清理逻辑不完整。

**解决方案**：
1. 在 CI 环境中，使用独立于开发的测试数据库
2. 测试用例中使用明确的 setup/teardown 步骤
3. 自动化测试使用专门的测试数据前缀，便于批量清理

---

## 5. 部署陷阱

### 5.1 Docker 端口映射冲突

**现象**：`docker compose up` 报错 `port is already allocated`。

**根因**：
| 服务 | 端口 | 冲突源 |
|------|------|--------|
| Jenkins | 8080 | 本地其他服务（常见的 8080 端口服务很多） |
| v2 api-server | 8000 | v1 后端、蓝湖 MCP、本地运行的 uvicorn |
| v2 web-ui | 80 | 本地 IIS/nginx/Apache |

**解决方案**：
1. 启动前检查端口占用：
   ```bash
   docker ps --format "table {{.Names}}\t{{.Ports}}"
   netstat -ano | findstr "8080 8000 80"  # Windows
   lsof -i :8080 -i :8000 -i :80          # macOS/Linux
   ```
2. 在 docker-compose.yml 中修改端口映射（如 `8081:8080`）
3. 确保本地没有其他服务已经在使用这些端口

**相关文件**：`deploy/jenkins/docker-compose.yml`、`test-platform-v2/deploy/docker-compose.yml`

---

### 5.2 Jenkins Pipeline 并发构建问题

**现象**：多个构建同时执行时，测试/部署相互干扰。

**根因**：
1. Jenkins Pipeline 默认允许并发构建
2. 并发构建共享 Docker 镜像标签（`latest`），导致部署到不同版本
3. 测试数据库被并发构建同时操作

**解决方案**：
1. 在 Jenkinsfile 中添加：
   ```groovy
   options {
       disableConcurrentBuilds()
   }
   ```
2. 使用 build number 作为 Docker 镜像 tag（而非 `latest`）
3. 每个构建使用独立的测试数据库或 schema

**相关文件**：`Jenkinsfile`、`deploy/jenkins/casc.yaml`

---

### 5.3 Docker-in-Docker 权限问题

**现象**：Jenkins 容器内执行 Docker 命令失败，权限不足。

**根因**：Jenkins 容器使用 Docker-in-Docker (DinD) 模式，需要特权模式或正确的 volume 挂载。

**解决方案**：
1. 确认 `docker-compose.yml` 中配置了 `/var/run/docker.sock` 挂载或 `privileged: true`
2. 检查容器内 Docker CLI 版本与宿主机 Docker daemon 兼容性
3. 确认 Jenkins 用户在容器内的 docker 组中

**相关文件**：`deploy/jenkins/docker-compose.yml`、`deploy/jenkins/Dockerfile`

---

### 5.4 环境变量未正确注入

**现象**：部署后服务行为异常，使用默认配置而非预期配置。

**根因**：Docker Compose 的 `env_file` 和 `environment` 优先级容易混淆。多环境（test/staging/prod）切换时可能加载了错误的 `.env` 文件。

**排查步骤**：
1. 进入容器检查环境变量：`docker compose exec api-server env | sort`
2. 确认 `.env` 文件在正确位置并被正确引用
3. Docker Compose 的变量优先级：`environment` > `env_file` > image 默认值 > Dockerfile ENV

**相关文件**：`test-platform-v2/deploy/docker-compose.yml`、各模块 `.env.example`

---

## 6. 开发环境陷阱

### 6.1 Windows 路径和编码问题

**现象**：脚本在 Windows 上执行失败，路径分隔符或编码错误。

**根因**：
- Windows 使用反斜杠路径分隔符，Python 和 Node 脚本中混用可能导致解析错误
- 中文文件名/路径在 Git Bash 和 PowerShell 间编码不一致

**解决方案**：
1. 在代码中使用正斜杠或 `pathlib.Path` 处理路径
2. 确保 `.bat` 脚本（Windows）和 `.sh` 脚本（macOS/Linux）分别维护了平台特定逻辑
3. Python 文件操作始终指定 `encoding='utf-8'`

---

### 6.2 Python 虚拟环境激活失败

**现象**：PowerShell 执行 `Activate.ps1` 报错 `cannot be loaded because running scripts is disabled`。

**根因**：Windows PowerShell 默认的执行策略禁止运行脚本。

**解决方案**：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**或者**使用 cmd 版本的激活脚本：`.venv\Scripts\activate.bat`

---

### 6.3 Vite HMR (Hot Module Replacement) 失效

**现象**：修改前端代码后页面不自动刷新。

**根因**：
1. 文件系统监视器超出系统限制（Windows 常见）
2. Vite 配置中 `server.watch` 的路径不匹配
3. 通过 Docker 或 WSL 开发时，跨文件系统事件传播延迟

**解决方案**：
1. 在 `vite.config.ts` 中增加 watch 配置：
   ```ts
   server: {
     watch: {
       usePolling: true,  // Docker/WSL 环境
     }
   }
   ```
2. 手动刷新页面（Ctrl+R）作为快速恢复

**相关文件**：`test-platform-v2/frontend/vite.config.ts`

---

## 排查速查表

| 症状 | 可能原因 | 查阅章节 |
|------|---------|---------|
| 定时任务重复执行 | APScheduler 多 worker | 1.1 |
| `database is locked` | SQLite 写冲突 | 1.2 |
| 迁移失败/版本冲突 | Alembic 版本号冲突 | 1.3 |
| AI 用例生成超时 | LLM API 超时 | 1.4 |
| CORS 报错 | 源未加入白名单 | 1.5 |
| 页面数据每次刷新都变 | Demo 态模块 | 2.1 |
| 频繁被踢到登录页 | JWT 过期 | 2.2 |
| shadcn 组件样式异常 | 源码复制模式升级冲突 | 2.3 |
| 蓝湖提取无数据 | Cookie 过期 | 3.1 |
| MCP 启动端口被占 | CDP 9222 冲突 | 3.2 |
| 蓝湖内容未更新 | 版本缓存未失效 | 3.3 |
| TC 与 Playwright 不一致 | 双向追溯断裂 | 4.1 |
| TypeScript 类型报错 | API 契约未同步 | 4.2 |
| 端口被占用 | v1/v2 同端口 | 4.3 |
| docker compose 失败 | 端口映射冲突 | 5.1 |
| 并发构建互相干扰 | Jenkins 无并发限制 | 5.2 |

---

## 维护说明

- 每个新陷阱按现有章节结构归类，必要时新增章节
- 条目格式统一：**现象 → 根因 → 解决方案 → 相关文件**
- 已修复的问题不要删除，在条目末尾标注修复日期和版本
- 本文档与 Memory 系统中的 `common-pitfalls` 保持内容同步，本文档为更详细的仓库锚定版本
