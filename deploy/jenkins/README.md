# CamelTv 体育平台 — Jenkins CI/CD 部署指南

## 架构

```
deploy/jenkins/
├── docker-compose.yml   # Jenkins Controller + Docker-in-Docker
├── Dockerfile           # Jenkins 预装 Python 3.12 + Node 18 + Docker CLI
├── casc.yaml            # Configuration as Code (自动配置)
└── README.md            # 本文

项目根 /
├── Jenkinsfile          # 主 Pipeline 定义 (11 阶段)
├── test-platform-v2/    # 测试平台 v2 (FastAPI + React)
├── test-platform/       # 测试平台 v1 (旧版)
└── lanhu-mcp/           # 蓝湖 MCP 服务
```

---

## 一键启动（本地开发）

### 前置要求

- **Docker 20.10+** 且 Docker Desktop 正在运行
- 端口 `8080` 未被占用

### 启动步骤

```bash
# 1. 进入 Jenkins 部署目录
cd F:\CamelTv\deploy\jenkins

# 2. 复制安全配置模板并填写两个独立强密码（真实 .env 禁止提交）
Copy-Item .env.example .env

# 3. 一键启动（首次需拉取镜像 + 构建，约 3~5 分钟）
docker compose up -d

# 4. 查看启动日志（等待出现 "Jenkins is fully up and running"）
docker compose logs -f jenkins
```

### 访问 Jenkins

| 项目 | 值 |
|------|-----|
| **地址** | `http://localhost:8080` |
| **用户名** | 本机 `.env` 中的 `JENKINS_ADMIN_USERNAME` |
| **密码** | 本机 `.env` 中的 `JENKINS_ADMIN_PASSWORD` |

> CasC 已自动完成安全配置——跳过安装向导、跳过插件安装、用户账号已就绪。

### 运行首次构建

1. 浏览器打开 `http://localhost:8080`，使用本机 `.env` 中的管理员账号登录
2. 点击 **CamelTv-Platform** → **Build Now**（或用 **Build with Parameters** 选择参数）
3. 点击构建编号进入详情，或点左侧 **Blue Ocean** 查看可视化进度
4. Pipeline 自动执行 11 个阶段：Checkout → Lint → Test → Build → Deploy → Smoke → Gate

---

## 一键启动（生产服务器）

### 前置要求

- **Docker 20.10+**
- Git 仓库可访问（本地 `file:///workspace` 改为远程 Git URL）
- 使用 Secret 管理提供管理员和开发账号密码

### 部署步骤

```bash
# 1. 克隆项目
git clone <your-repo-url> /opt/cameltv
cd /opt/cameltv/deploy/jenkins

# 2. 从模板创建未跟踪的密钥文件并填写强密码
cp .env.example .env

# 3. 启动
docker compose up -d

# 4. 确认运行
docker compose ps
curl http://localhost:8080/login
```

---

## 首次启动后：创建 Pipeline Job

Jenkins 启动后，创建一个 Pipeline Job 指向项目根的 `Jenkinsfile`：

1. 登录 `http://localhost:8080` → 点击 **New Item**（新建任务）
2. 输入名称 `CamelTv-Platform`，选择 **Pipeline**，点击 OK
3. 在 **Pipeline** 配置区域：
   - **Definition**: `Pipeline script from SCM`
   - **SCM**: `Git`
   - **Repository URL**: `file:///workspace`（通过 Docker volume 挂载）或填写 Git 仓库地址
   - **Branches to build**: `*/main`
   - **Script Path**: `Jenkinsfile`
4. 勾选 **Poll SCM**，Schedule 填 `H/15 * * * *`（每 15 分钟检查变更）
5. 点击 **Save**

### 可选：创建定时 Job

| Job 名 | 类型 | Pipeline Script | 触发 |
|--------|------|----------------|------|
| `CamelTv-API-Regression` | Pipeline | 见下方脚本 | Build Triggers → Build periodically: `H 2 * * *` |
| `CamelTv-Prod-Smoke` | Pipeline | 见下方脚本 | Build Triggers → Build periodically: `H 8 * * *` |

**CamelTv-API-Regression**（Pipeline script 直接贴入）：
```groovy
pipeline {
    agent any
    stages {
        stage('Test') {
            steps {
                dir('test-platform-v2/backend') {
                    sh 'python -m pytest tests/ -v --tb=short'
                }
            }
        }
    }
}
```

**CamelTv-Prod-Smoke**（Pipeline script 直接贴入）：
```groovy
pipeline {
    agent any
    stages {
        stage('Smoke') {
            steps {
                sh '''
                    curl -fsS http://localhost/health
                '''
            }
        }
    }
}
```

---

## Pipeline 11 阶段详解

```
Checkout ──→ Backend Lint ──→ Backend Test ──→ Frontend TypeCheck ──→ Frontend Test+Build
                                                                              │
     ┌────────────────────────────────────────────────────────────────────────┘
     ▼                  ▼                        ▼
  Docker Build     Docker Push(main)     Deploy Test(docker compose up)
                                               │
                                          Smoke Test(curl health + login)
                                               │
                                          Quality Gate
```

| # | 阶段 | 内容 | 产出 |
|---|------|------|------|
| 1 | Checkout | 拉取代码 | |
| 2 | Backend: Lint | venv + pip install + 编译检查 + 安全密钥校验 | |
| 3 | Backend: Test | pytest + HTML 报告 + JUnit XML | `test-report.html` `test-results.xml` |
| 4 | Frontend: TypeCheck | npm ci + tsc --noEmit | |
| 5 | Frontend: Test+Build | vitest + npm run build | `test-results.xml` `dist/` |
| 6 | Docker: Build | 构建 backend + frontend 镜像 | |
| 7 | Docker: Push | (仅 main 分支) 推送 Registry | |
| 8 | Deploy: Test | docker compose up -d | 测试环境就绪 |
| 9 | Smoke Test | curl health + 登录 API | |
| 10 | Quality Gate | 汇总测试结果 + 通过率 | |

---

## 常用管理命令

```bash
# 查看 Jenkins 日志
docker compose logs -f jenkins

# 查看运行状态
docker compose ps

# 重启 Jenkins（修改 casc.yaml 后）
docker compose restart jenkins

# 停止 Jenkins
docker compose down

# 停止并清除所有数据（重新开始）
docker compose down -v

# 进入 Jenkins 容器
docker compose exec jenkins bash

# 查看 Pipeline 工作区
docker compose exec jenkins ls /workspace
```

---

## SCM 配置（本地开发 → 生产 Git）

CasC 默认使用 `file:///workspace`（容器挂载本地项目目录）。改为远程 Git 仓库：

1. 编辑 `casc.yaml`
2. 找到 `remote { url('file:///workspace') }`
3. 改为你的 Git 仓库地址，如：
   ```groovy
   remote {
     url('https://github.com/your-org/cameltv.git')
     credentials('github-credential-id')
   }
   ```
4. 在 Jenkins → Manage Jenkins → Credentials 中添加 Git 凭据
5. 重启：`docker compose restart jenkins`

---

## 密码修改

编辑 `casc.yaml`：

```yaml
securityRealm:
  local:
    users:
      - id: "admin"
        password: "你的新密码"   # ← 改这里
```

重启生效：`docker compose restart jenkins`

---

## 排障

| 问题 | 原因 | 解决 |
|------|------|------|
| `docker: command not found` | 宿主机未安装 Docker | 安装 Docker Desktop 或 Docker Engine |
| Pipeline 报 `/workspace not found` | volume 挂载路径不对 | 检查 `docker-compose.yml` 中 `../../:/workspace` 是否正确指向项目根 |
| 插件安装失败 | 网络问题或缓存损坏 | `docker compose down -v && docker compose up -d` |
| 端口 8080 被占用 | 其他程序占用 | 改 `docker-compose.yml` 中 `ports: - "9090:8080"` |
| 首次启动超时 | 镜像拉取慢 | 等待或配置 Docker 镜像加速 |
| CasC 未生效 | YAML 语法错误 | `docker compose logs jenkins \| grep -i casc` 查看错误 |
| 容器启动即退出 | 内存不足 | Jenkins 建议 ≥ 2GB 内存 |
