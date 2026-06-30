# CamelTv 测试平台 — 启动命令 & 平台地址

## 一、后端启动

```powershell
cd test-platform

# 激活虚拟环境
.\.venv\Scripts\Activate.ps1

# 启动 FastAPI 服务器 (端口 8000)
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

| 地址 | 说明 |
|------|------|
| `http://localhost:8000` | API 服务根路径 |
| `http://localhost:8000/health` | 健康检查 |
| `http://localhost:8000/docs` | Swagger API 文档 (可在线调试) |
| `http://localhost:8000/redoc` | ReDoc API 文档 |

### 后端路由一览

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/api/config` | 项目配置 + 环境列表 |
| GET | `/api/config/{env}` | 单个环境完整配置 |
| POST | `/api/envcheck` | 环境健康检查 |
| POST | `/api/api-test/run` | 运行 API 测试 |
| POST | `/api/api-test/pull-swagger` | 拉取 Swagger 生成测试 |
| POST | `/api/ui-auto/run` | 运行 UI 自动化 |
| POST | `/api/datafactory/generate` | 生成测试数据 |
| GET | `/api/reports` | 报告列表 |
| GET | `/api/reports/{run_id}/summary` | 报告详情 |
| GET | `/api/task-history` | 任务执行历史 |
| GET | `/api/workspace/stats` | 工作台聚合统计 |
| GET | `/api/test-cases` | 用例列表（支持筛选） |
| GET | `/api/test-cases/modules` | 用例模块列表 |
| POST | `/api/test-cases` | 新建用例 |
| PUT | `/api/test-cases/{id}` | 编辑用例 |
| DELETE | `/api/test-cases/{id}` | 删除用例 |
| POST | `/api/test-cases/import` | 批量导入用例 |
| GET | `/api/test-plans` | 计划列表 |
| POST | `/api/test-plans` | 新建计划 |
| GET | `/api/test-plans/{id}` | 计划详情（含用例+执行记录） |
| PUT | `/api/test-plans/{id}` | 编辑计划 |
| DELETE | `/api/test-plans/{id}` | 删除计划 |
| POST | `/api/test-plans/{id}/run` | 执行计划 |

---

## 二、前端启动

```powershell
cd test-platform/web-ui

# 安装依赖（首次）
npm install

# 启动 Vite 开发服务器 (端口 5173)
npm run dev
```

| 地址 | 说明 |
|------|------|
| **`http://localhost:5173`** | ⭐ **平台入口**（前端页面） |

Vite 已配置代理：所有 `/api` 请求自动转发到 `http://localhost:8000`。

### 前端路由（页面）

| 路由 | 页面 | 功能 |
|------|------|------|
| `/` | 工作台 | 统计卡片 + 通过率趋势 + 快捷入口 |
| `/test-cases` | 测试用例 | 用例 CRUD + 搜索筛选 + 批量导入 |
| `/test-plans` | 测试计划 | 计划管理 + 用例关联 + 一键执行 |
| `/test-plans/:id` | 计划详情 | 用例清单 + 执行状态 + 运行历史 |
| `/api-testing` | 接口测试 | Swagger 拉取 + Playwright 运行 |
| `/reports` | 报告中心 | 统计图表 + 报告历史 |
| `/profile` | 个人中心 | 版本信息 + Token 管理 |

---

## 三、Docker 一键部署

```powershell
cd test-platform
docker-compose up -d
```

| 服务 | 端口 | 地址 |
|------|------|------|
| web-ui (nginx) | 80 | `http://localhost` |
| api-server | 8000 | `http://localhost:8000` |
| wiremock | 8080 | `http://localhost:8080` |

---

## 四、平台地址速查

```
开发模式:
  前端入口:  http://localhost:5173
  API 文档:  http://localhost:8000/docs
  健康检查:  http://localhost:8000/health

Docker 部署:
  前端入口:  http://localhost
  API 文档:  http://localhost:8000/docs
```
