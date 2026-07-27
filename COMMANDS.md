---
title: "CamelTv 测试平台命令速查手册"
owner: "qa-team"
last_reviewed: "2026-06-26"
status: "active"
expires: "2026-12-26"
tags: ["命令", "CLI", "参考", "速查"]
related: ["CamelTv-测试自动化平台-建设方案.md"]
---

# CamelTv 测试平台 — 命令速查手册

> 所有命令统一入口，按服务/场景分组。  
> 标注 `(win)` = Windows PowerShell，`(unix)` = macOS / Linux bash。

---

## 目录

- [1. 蓝湖 MCP 服务器](#1-蓝湖-mcp-服务器)
- [2. 测试平台 · 首次搭建](#2-测试平台--首次搭建)
- [3. 测试平台 · 后端 FastAPI](#3-测试平台--后端-fastapi)
- [4. 测试平台 · 前端 React](#4-测试平台--前端-react)
- [5. 测试平台 · CLI 工具 tp](#5-测试平台--cli-工具-tp)
  - [5.1 配置查看](#51-配置查看)
  - [5.2 环境探活](#52-环境探活)
  - [5.3 API 测试](#53-api-测试)
  - [5.4 流量抓取](#54-流量抓取)
  - [5.5 Mock Server](#55-mock-server)
  - [5.6 双环境对比](#56-双环境对比)
  - [5.7 数据工厂](#57-数据工厂)
  - [5.8 日志聚合](#58-日志聚合)
  - [5.9 报告看板](#59-报告看板)
  - [5.10 项目初始化](#510-项目初始化)
- [6. Docker 全套部署](#6-docker-全套部署)
- [7. 开发工作流](#7-开发工作流)

---

## 1. 蓝湖 MCP 服务器

> 将蓝湖原型/设计稿暴露为 MCP 工具，供 AI 编码助手（Cursor、Claude Code 等）调用。  
> 项目路径：`lanhu-mcp/`  
> 端口：`8000`（FastMCP HTTP）

### 1.1 一键快速启动（推荐首次使用）

```bash
# Windows (lanhu-mcp/ 目录下)
.\quickstart.bat

# macOS / Linux
bash quickstart.sh
```

> 脚本自动完成：创建 venv → 安装依赖 → 安装 Playwright Chromium → 引导填写 Cookie → 启动服务。  
> 服务地址：`http://localhost:8000/mcp`

### 1.2 手动启动（已搭好环境后）

```bash
# 激活 venv（Windows）
.\venv\Scripts\Activate.ps1

# 激活 venv（macOS / Linux）
source venv/bin/activate

# 启动 MCP 服务器
python lanhu_mcp_server.py
```

### 1.3 Docker 部署

```bash
# 引导式配置（生成 .env 后 docker compose up）
bash setup-env.sh        # macOS / Linux
setup-env.bat            # Windows

# 或手动
docker compose up -d
```

### 1.4 在 AI 工具中连接

MCP 配置示例（添加到 Cursor / Claude Code 的 MCP 配置）：

```json
{
  "mcpServers": {
    "lanhu": {
      "url": "http://localhost:8000/mcp?role=Developer&name=YourName"
    }
  }
}
```

| 参数 | 说明 |
|------|------|
| `role` | 调用者角色，如 `Developer`、`Tester` |
| `name` | 调用者名称（建议英文，部分工具不支持中文 URL） |

---

## 2. 测试平台 · 首次搭建

> 项目路径：`test-platform/`

### 2.1 一键搭建脚本

```bash
# Windows PowerShell (test-platform/ 目录下)
.\setup.ps1

# macOS / Linux
bash setup.sh
```

> 脚本自动完成：创建 `.venv` → 安装 Python 依赖 → `pip install -e .` 注册 `tp` 命令 → 安装 Playwright Chromium → 从 `.env.example` 生成 `.env`

### 2.2 手动搭建（分步执行）

```bash
# 1. 创建虚拟环境（Windows）
C:\Users\26029\AppData\Local\Programs\Python\Python312\python.exe -m venv .venv

# 1. 创建虚拟环境（macOS / Linux）
python3.12 -m venv .venv

# 2. 激活 venv（Windows）
.\.venv\Scripts\Activate.ps1

# 2. 激活 venv（macOS / Linux）
source .venv/bin/activate

# 3. 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 4. 注册 tp 命令行工具
pip install -e .

# 5. 安装 Playwright 浏览器（供 UI 自动化使用）
python -m playwright install chromium

# 6. 生成 .env 并填写凭据
copy .env.example .env
```

### 2.3 搭建后自检

```bash
# 确认 tp 命令可用
tp --version

# 查看合并后的运行配置
tp config show --env test
```

---

## 3. 测试平台 · 后端 FastAPI

> 源码：`server/main.py`  
> 端口：`8000`  
> API 前缀：`/api/*`

### 3.1 开发模式直接启动

```bash
# 激活 venv 后 (test-platform/ 目录下)
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

| 参数 | 说明 |
|------|------|
| `--reload` | 代码变更自动重载（开发用） |
| `--host 0.0.0.0` | 允许局域网访问 |
| `--port 8000` | 服务端口 |

### 3.2 验证后端是否正常

```bash
# 健康检查
curl http://localhost:8000/health

# 查看 API 文档（Swagger UI）
# 浏览器打开 → http://localhost:8000/docs

# 查看 API 文档（ReDoc）
# 浏览器打开 → http://localhost:8000/redoc

# 查看配置
curl http://localhost:8000/api/config/test
```

---

## 4. 测试平台 · 前端 React

> 源码：`web-ui/`  
> 框架：React 18 + TypeScript + Vite 5  
> 端口：`5173`（开发模式）  
> 代理：`/api` → `http://localhost:8000`

### 4.1 安装前端依赖（首次）

```bash
cd web-ui
npm install
```

### 4.2 开发模式启动

```bash
# web-ui/ 目录下
npm run dev
```

> 浏览器打开 → `http://localhost:5173`  
> 前端自动代理 `/api` 到后端 `localhost:8000`（配置在 `vite.config.ts`）

### 4.3 生产构建 + 预览

```bash
# 构建（输出到 web-ui/dist/）
npm run build

# 本地预览构建产物
npm run preview
```

### 4.4 仅前端（后端已用 Docker / 远程）

修改 `vite.config.ts` 中的 proxy target 指向实际后端地址：

```ts
proxy: {
  '/api': 'http://实际后端IP:8000'
}
```

---

> ⚠️ **prod 环境当前状态：** `vpn_required` 已临时设为 `false`，`proxy_strategy` 临时设为 `direct`。  
> 接入内网/VPN 后，将 `config/environments/prod.yaml` 中对应字段改回 `vpn_required: true` / `proxy_strategy: vpn07` / `proxy: "${UPSTREAM_PROXY}"`。

---

## 5. 测试平台 · CLI 工具 `tp`

> `tp` 是统一命令行入口，通过 `pip install -e .` 注册。  
> 所有需要 `--env` 的命令：`test` = 测试环境，`prod` = 正式环境。

### 5.1 配置查看

```bash
# v2 模式（推荐）— 查看合并后的完整运行上下文
tp config show --env test
tp config show --env prod

# 列出所有站点/项目及可用环境
tp config sites
```

### 5.2 环境探活

```bash
# 并发探活所有基础设施（DB/Redis/MQ/HTTP/版本），输出红绿灯
tp envcheck --env test
tp envcheck --env prod
```

> 探活项目由 `config/environments/<env>.yaml` 中的 `dbs`/`redis`/`mqs`/`https` 定义。  
> 全部通过 → 退出码 0；任一失败 → 退出码 1。

### 5.3 API 测试

> 基于 Playwright，swagger 优先 + UI 捕获补充。  
> 详见 `tools/api_tester/`

```bash
# ──── 拉取 Swagger 生成测试骨架 ────

# 从内网真实 Swagger URL 拉取（需在内网环境）
tp api pull --source "https://g3-test3.elelive.cn/v3/api-docs"

# 从本地 YAML/JSON spec 文件生成
tp api pull --source "tests/api-testing/specs/cameltv-openapi.yaml"

# 自定义输出目录
tp api pull --source "<url>" --out "tests/api-testing/my-tests"


# ──── 执行 API 测试 ────

# 对测试环境执行（使用配置中的 base_url）
tp api run --env test

# 对正式环境执行
tp api run --env prod

# 本地调试：覆盖 base_url（例如打本地后端 / Mock Server）
tp api run --env test --base-url "http://localhost:8000"

# 按名称过滤用例（支持正则）
tp api run --env test --filter "smoke"
tp api run --env test --filter "UGC"

# 指定 JUnit XML 报告输出路径
tp api run --env test --report "data/reports/my-report.xml"


# ──── 从 UI 自动化流量补充用例 ────

# 导入 UI 自动化 session 捕获的 API 流量（去重，swagger 优先）
tp api capture --session-id "<session_id>"
```

**API 测试完整流水线（首次生成后）：**

```bash
# 1. 生成测试 → 安装 TS 依赖 → 类型检查 → 执行
tp api pull --source "tests/api-testing/specs/cameltv-openapi.yaml"
cd tests/api-testing/generated
npm install
npx tsc --noEmit              # 0 错误才算通过
cd ../../../
tp api run --env test
```

### 5.4 流量抓取

> 基于 mitmproxy 录制真实请求

```bash
# 测试环境抓包（端口 8081）
tp capture --env test --port 8081

# 正式环境抓包，指定输出文件
tp capture --env prod --port 8081 --out "data/recordings/prod-capture.json"
```

> 启动后配置浏览器/设备代理到 `localhost:8081`，首次使用需安装 mitmproxy CA 证书（浏览器访问 `http://mitm.it`）。

### 5.5 Mock Server

> 基于 WireMock（Docker），用于模拟下游服务

```bash
# 启动 WireMock 容器（端口 8080）
tp mock up --port 8080

# 停止 WireMock 容器
tp mock down

# 将录制流量转换为 WireMock stub 映射
tp mock convert --recording "data/recordings/test-capture.json"

# 注入故障：指定接口返回 500
tp mock inject --path "/api/pay/order" --status 500

# 注入故障：模拟超时
tp mock inject --path "/api/user/profile" --scenario "timeout"
```

### 5.6 双环境对比

> 同一批请求打两个环境，JSON 逐字段比对

```bash
# 对比 prod（基线）与 test（目标）
tp apidiff --base prod --target test --cases "data/recordings/baseline.json"

# 指定输出报告
tp apidiff --base prod --target test --cases "cases.yaml" --report "data/reports/diff.html"
```

### 5.7 数据工厂

> 按规则批量生成测试数据并灌库

```bash
# 正常数据：生成 20 条并写入数据库
tp datafactory --env test --rule "rules/user.yaml" --count 20 --mode normal --output db

# 脏数据：生成 10 条边界值/非法值，导出为 SQL 文件
tp datafactory --env test --rule "rules/user.yaml" --count 10 --mode dirty --output sql

# 使用预置场景模板（vip_user / new_user / etc.）
tp datafactory --env test --template "vip_user" --count 5 --mode normal --output db

# 导出为 JSON（不进库）
tp datafactory --env test --rule "rules/user.yaml" --count 10 --output json
```

### 5.8 日志聚合

> 按 traceId 串联全链路日志，自动生成 ELK 查询链接

```bash
# 单条 traceId 查询，输出 HTML
tp logagg trace --env test --id "abc123-trace-id"

# 指定输出路径
tp logagg trace --env test --id "abc123" --out "data/reports/trace-abc123.html"

# 批量：解析测试报告 XML，对失败用例聚类相同根因
tp logagg batch --env test --report "data/reports/api-test-junit.xml"

# 不做聚类（仅生成 ELK 链接）
tp logagg batch --env test --report "data/reports/api-test-junit.xml" --no-cluster
```

### 5.9 报告看板

> 基于 Streamlit 的测试报告聚合与趋势看板

```bash
# 入库：解析多框架报告并存入 SQLite
tp report ingest --file "data/reports/junit.xml" --build "v1.2.3" --branch "main" --source "api"
tp report ingest --file "data/reports/functional.json" --build "v1.2.3" --source "functional"

# 启动趋势看板（Streamlit，端口 8090）
tp report serve --port 8090
```

> 看板地址：`http://localhost:8090`

### 5.10 项目初始化

```bash
# 交互式向导创建新测试项目骨架
tp init-project "my-new-service" --out "./my-test-project"
```

---

## 6. Docker 全套部署

> 前端 + 后端 + WireMock 一键容器化。

```bash
# ──── 完整栈（api-server + web-ui + wiremock）────
cd test-platform
docker compose up -d

# 启动并强制重建镜像（代码变更后）
docker compose up -d --build

# 带 PostgreSQL 的完整栈
docker compose --profile full up -d


# ──── 单独启动某个服务 ────
docker compose up -d api-server     # 仅后端 FastAPI
docker compose up -d web-ui         # 仅前端 Nginx
docker compose up -d wiremock       # 仅 Mock Server


# ──── 查看状态 / 日志 ────
docker compose ps                    # 所有服务状态
docker compose logs -f api-server    # 后端日志（实时）
docker compose logs -f web-ui        # 前端日志


# ──── 停止 / 清理 ────
docker compose down                  # 停止并移除容器
docker compose down -v               # 同时清除数据卷
```

**服务端口映射：**

| 服务 | 端口 | 说明 |
|------|------|------|
| `web-ui` | `80` | 前端静态页面（Nginx） |
| `api-server` | `8000` | FastAPI 后端 |
| `wiremock` | `8080` | Mock Server |

---

## 7. 开发工作流

### 7.1 日常开发（前后端联调）

```bash
# 终端 1：启动后端（test-platform/ 目录，venv 已激活）
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload

# 终端 2：启动前端（web-ui/ 目录）
npm run dev

# 浏览器 → http://localhost:5173
```

### 7.2 蓝湖 MCP 开发

```bash
# 终端 1：启动蓝湖 MCP（lanhu-mcp/ 目录）
python lanhu_mcp_server.py

# 在 Cursor / Claude Code 中配置 MCP 连接
# URL: http://localhost:8000/mcp?role=Developer&name=YourName
```

### 7.3 API 测试开发迭代

```bash
# ① 修改 swagger spec 或重新拉取
tp api pull --source "tests/api-testing/specs/cameltv-openapi.yaml"

# ② 安装依赖 + 类型检查
cd tests/api-testing/generated
npm install
npx tsc --noEmit
cd ../../../

# ③ 打本地后端验证
tp api run --env test --base-url "http://localhost:8000"

# ④ 打真实测试环境验证（需内网）
tp api run --env test
```

### 7.4 CI/CD 入口

```bash
# CI 脚本（Windows）
.\scripts\ci-entrypoint.ps1 -Command "tp envcheck --env test; tp api run --env test"
```

### 7.5 查看所有可用命令

```bash
# tp 主命令列表
tp --help

# 子命令帮助
tp api --help
tp mock --help
tp report --help
tp logagg --help
```

---

> **提示：** 所有需要凭据的操作（`tp envcheck`、`tp api run` 等）需要在 `test-platform/.env` 中填写真实的数据库/Redis/MQ/ELK 密码和 auth token。  
> 模板文件：`test-platform/.env.example`
