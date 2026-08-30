# AITDE V3.4 Durable Runtime — 部署 Runbook（test 本地 / prod 云服务器）

> 目标：让「待基础设施」的 V3.4 项（Temporal Server、mTLS、Worker 主机、Policy/OPA）
> 可复现落地。**代码已在 PR #356 合入 main**；本目录只负责把真实环境跑起来并验收。
> 目标读者是你（运维，本地=test，生产=云服务器）。

## 0. 前置

- Docker + Docker Compose v2
- 仓库（含 `lanhu-mcp` 子模块）：`git submodule update --init`
- backend 运行环境（Python 3.12 + `requirements.txt`），用于启动 worker
- 本目录：`test-platform-v2/deploy/aitde-runtime`

```
aitde-runtime/
├── docker-compose.yml        Temporal Server（auto-setup + SQLite 持久化/visibility）
├── .env.example              配置样例（复制为 .env）
├── .gitignore                忽略 certs/、密钥、.env
├── config/                   （预留：如需覆盖 Temporal 配置）
├── scripts/
│   ├── gen-certs.sh          自签 CA + server + worker client 证书
│   ├── gen-certs.ps1         同上（Windows）
│   └── start-worker.sh       Worker 主机启动模板
└── policy/
    ├── driver_action_policy.json   自研 Policy 文档样例
    └── driver_action_policy.rego   OPA drop-in 样例
```

## 1. 本地 test 环境 —— 单机跑通

### 1.1 起 Temporal Server（Control Plane 推进器）

```bash
cd test-platform-v2/deploy/aitde-runtime
docker compose up -d
# gRPC 7233、Web UI http://localhost:8080
```

> `temporalio/auto-setup` 自动建 namespace(s) + SQLite 持久化 + SQLite visibility，
> 零配置可跑；生产再切 Postgres + Elasticsearch（见 §2）。

### 1.2 打开后端 Temporal 开关

在 backend `.env` 设置：

```bash
TEMPORAL_ENABLED=true
TEMPORAL_GRPC_ENDPOINT=127.0.0.1:7233
TEMPORAL_NAMESPACE=default
TEMPORAL_TASK_QUEUE=worker-test
```

### 1.3 启动执行 Worker（拉取 TaskQueue）

```bash
cd test-platform-v2/backend
python -m app.modules.aitde.workflow.gateway --task-queue worker-test
```

若 Worker 不在库侧，用 `scripts/start-worker.sh`（含注册/心跳到 Control Plane）：

```bash
# 先起 backend + 数据库，再:
bash test-platform-v2/deploy/aitde-runtime/scripts/start-worker.sh TEST HTTP,BROWSER
```

### 1.4 验证

- [ ] Web UI http://localhost:8080 有 namespace / workflow 列表
- [ ] Control Plane `GET /api/v2/workers` 能看到注册的 worker（ONLINE）
- [ ] 启动一个 ScenarioExecutionWorkflow，worker 拉取并执行，Run 状态推进

## 2. 生产云服务器 —— 复制到单机

流程同 §1，但把回调地址/镜像/持久化按生产调：

- `TEMPORAL_GRPC_ENDPOINT` 指向生产可访问的地址（内网/公网，按需 mTLS）
- `docker-compose.yml` 的 `TEMPORAL_GRPC_PORT`/`UI_PORT` 按需映射；生产默认可不暴露 UI
- 持久化/visibility：把 `DB` 从 sqlite 换成 Postgres，visibility 用 Elasticsearch
  （`temporalio/auto-setup` 支持 `DB=postgres12` + `VISIBILITY=elasticsearch`，
  docker-compose 需另起 postgres + elasticsearch 服务——见官方 temporal 仓库模板）
- **SECRET/ALWAYS 隔离**：不把数据库、证书、密钥写入镜像或仓库

## 3. mTLS（可选，默认关）

生成自签 CA + server + worker 客户端证书：

```bash
bash scripts/gen-certs.sh      # 或 pwsh scripts\gen-certs.ps1
```

把证书路径填入 `.env`（worker client 证书给 Control Plane/worker；server 证书给 Temporal）：

```bash
TEMPORAL_TLS_ENABLED=true
TEMPORAL_TLS_CA_PATH=/path/certs/ca.crt
TEMPORAL_TLS_CERT_PATH=/path/certs/worker.crt
TEMPORAL_TLS_KEY_PATH=/path/certs/worker.key
```

并在 `docker-compose.yml` 加 service 卷挂载（server 用 `temporal.crt/temporal.key`），
**certs/ 已 gitignore，密钥永不入库**。

> 说明：当前 worker 侧为「验证服务器证书」（one-way TLS）；双向 client-auth
> （V34-007）需 Temporal server 配置 `TLS_REQUIRE_CLIENT_AUTH=true` + 把
> `worker.crt` 加入 CA 信任，属可选加固。

## 4. Policy / OPA（可选）

- 默认自研 `PolicyGateway`（backend 内），无需额外服务。
- 若要 OPA：把 `policy/driver_action_policy.rego` 挂到 OPA server 端点，并在
  Policy Gateway 的 Provider Adapter 里调用（保持与自研规则一致，V34-010）。

## 5. 版本验收（V34-001 等「待基础设施」项）

代码合入 ≠ 版本验证完成。真实验收项（计划 §93）需真实环境执行：

- [ ] Temporal server 端到端部署（起服务 + TLS + persistence/visibility）✅ 见 §1
- [ ] 真实 worker 强杀 drill（kill worker → Run 恢复 + Fixture 无重复）——需两 worker
- [ ] 强杀 Control Plane，Workflow 可恢复查询
- [ ] 无效 mTLS Worker 无法注册（双向 client-auth 时）
- [ ] API/UI Shadow 结果一致率达门槛
- [ ] Worker drain 不收新任务

完成并记录 reviewer/环境/时间/Evidence 后，才能把 V3.4 标为 `VERIFIED`
（计划 §94 Release Gate），这就满足了 V3.5 的「上一版本依赖：V3.4 VERIFIED」。

## 6. 关联

- 实现：`backend/app/modules/aitde/workflow/`（gateway/service/router/policy/secret_resolver）
  + `backend/app/temporal/`（workflows/activities）
- 计划：`docs/aitde/versions/V3.4_Detailed_Development_Implementation_Plan.md`
- Worker 注册 API：`POST /api/v2/workers/heartbeat`
