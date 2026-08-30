# AITDE V3.4 Durable Runtime — 部署 Runbook（test 本地 / prod 云服务器）

> 目标：让「待基础设施」的 V3.4 项（Temporal Server、mTLS、Worker 主机、Policy/OPA）
> 可复现落地。**代码已在 PR #357 合入 main**；本目录只负责把真实环境跑起来并验收。
> 目标读者是你（运维，本地=test，生产=云服务器）。
>
> **lab 实测结论（2026-08-30，local test）**：Temporal Server 已 `SERVING`、backend worker 跑通
> `ScenarioExecutionWorkflow` 全 9 步链、mTLS（双向 client-auth）invalid-cert-reject **PASS**
> （见 §5 与 `drill_mtls_reject.py`）。**SQLite 持久化不可用**：`temporalio/auto-setup` 的
> config_template 只支持 cassandra/mysql8/postgres12，故统一用 **PostgreSQL**（与主部署同构）。

## 0. 前置

- Docker + Docker Compose v2
- 仓库（含 `lanhu-mcp` 子模块）：`git submodule update --init`
- backend 运行环境（Python 3.12 + `requirements.txt`），用于启动 worker
- 本目录：`test-platform-v2/deploy/aitde-runtime`

```
aitde-runtime/
├── docker-compose.yml            Temporal Server + PostgreSQL（postgres12 持久化 + postgres visibility）
├── docker-compose.mtls-test.yml  可选互信 mTLS overlay（V34-007 加固测试，非默认）
├── .env.example                  配置样例（复制为 .env）
├── .gitignore                    忽略 certs/、密钥、.env
├── config/
│   ├── docker.yaml               Temporal server 配置（auto-setup 启动时据 env 重生成；此处供 setup 用）
│   ├── config_template.yaml      模板（编译时语义，保留）
│   └── dynamicconfig/docker.yaml
├── scripts/
│   ├── gen-certs.py              自签 CA + server + worker client 证书（跨平台，含 SAN；推荐）
│   ├── gen-certs.sh              同上前身（bash；其 -extfile SAN 注入在 Windows 无效，仅 Linux）
│   ├── gen-certs.ps1             同上（Windows）
│   ├── setup-temporal-schema.sh  postgres12 schema one-shot（temporal + temporal_visibility 两库）
│   ├── start-worker.sh           Worker 主机启动模板
│   └── drill_mtls_reject.py      mTLS invalid-cert-reject 验收 drill（§93-599 / V34-007）
└── policy/
    ├── driver_action_policy.json   自研 Policy 文档样例
    └── driver_action_policy.rego   OPA drop-in 样例
```

## 1. 本地 test 环境 —— 单机跑通

### 1.1 起 Temporal Server（Control Plane 推进器）

```bash
cd test-platform-v2/deploy/aitde-runtime
# Docker Desktop 占 8080 时，UI 改用 8081：
export TEMPORAL_UI_PORT=8081
docker compose up -d
# 等待：postgres healthy → setup 跑完 schema → temporal healthy → namespace default 就绪
docker compose ps
# gRPC 7233、Web UI http://localhost:8081
```

> `temporal-postgres`（postgres16-alpine）+ `temporal-setup`（一次性建 schema，主/visibility 两库）
> + `temporal`（`temporalio/auto-setup:1.25.2`，`command: start`）+ `temporal-namespace`（幂等建 default）。
> 持久化/visibility 均走 postgres12，**与生产同构**；生产可切 Elasticsearch visibility。

### 1.2 打开后端 Temporal 开关（backend `.env`）

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
bash test-platform-v2/deploy/aitde-runtime/scripts/start-worker.sh TEST HTTP,BROWSER
```

### 1.4 验证

- [x] Web UI（http://localhost:8081）有 namespace / workflow 列表
- [x] Control Plane `GET /api/v2/workers` 能看到注册的 worker（ONLINE）
- [x] 启动一个 ScenarioExecutionWorkflow，worker 拉取并执行，Run 状态推进

## 2. 生产云服务器 —— 复制到单机

流程同 §1，但把回调地址/镜像/持久化按生产调：

- `TEMPORAL_GRPC_ENDPOINT` 指向生产可访问的地址（内网/公网，按需 mTLS）
- `docker-compose.yml` 的 `TEMPORAL_GRPC_PORT`/`UI_PORT` 按需映射；生产默认可不暴露 UI
- 持久化/visibility：默认即 postgres12；如需 Elasticsearch visibility，改 `config/docker.yaml`
- **SECRET/ALWAYS 隔离**：不把数据库、证书、密钥写入镜像或仓库；certs/ 已 gitignore

## 3. mTLS（互信 client-auth，V34-007）

### 3.1 生成证书（跨平台，含正确 SAN）

```bash
# 推荐：跨平台、无 openssl 依赖、自动注入 SAN(localhost/temporal/aitde-temporal/127.0.0.1/172.20.0.3)
python scripts/gen-certs.py

# 或 Linux：
bash scripts/gen-certs.sh
# 或 Windows：
pwsh scripts\gen-certs.ps1
```

> 证书落在 `certs/`（git-ignored，密钥永不入库）：`ca.crt/key`、`temporal.crt/key`（server）、`worker.crt/key`（client）。

### 3.2 启用服务端互信 mTLS（Temporal `docker-compose`）

auto-setup 在启动时据 env 重生成 server 配置，因此用 **env** 而非手改 `config/docker.yaml`。
推荐用 `docker-compose.mtls-test.yml` overlay（含证书挂载 + 带证书的 healthcheck）：

```bash
export TEMPORAL_UI_PORT=8081
docker compose -f docker-compose.yml -f docker-compose.mtls-test.yml up -d temporal
```

等价的最小 env（`temporal` 服务）：
`TEMPORAL_TLS_REQUIRE_CLIENT_AUTH=true`、`TEMPORAL_TLS_SERVER_CERT/KEY`（internode）、
`TEMPORAL_TLS_FRONTEND_CERT/KEY`（frontend）、`TEMPORAL_TLS_CLIENT1_CA_CERT=ca.crt`、
`TEMPORAL_TLS_INTERNODE_SERVER_NAME=temporal`、`TEMPORAL_TLS_FRONTEND_SERVER_NAME=temporal`，
并挂载 `./certs:/etc/temporal/certs:ro`。

### 3.3 backend 侧启用 mTLS（worker/client）

backend `.env`：

```bash
TEMPORAL_TLS_ENABLED=true
TEMPORAL_TLS_CA_PATH=/path/certs/ca.crt
TEMPORAL_TLS_CERT_PATH=/path/certs/worker.crt
TEMPORAL_TLS_KEY_PATH=/path/certs/worker.key
```

> 网关 `_get_client` 用 `worker.crt/worker.key` 作为机器身份，`temporal.crt` 为 server 证书。

### 3.4 验收（§93-599 / V34-007）

```bash
python scripts/drill_mtls_reject.py
# RESULT: PASS —— valid worker cert 握手成功；
# 无 client cert 收 CertificateRequired、无关 CA 证书收 UnknownCA，均被拒（无效 Worker 无法注册）。
```

## 4. Policy / OPA（可选）

- 默认自研 `PolicyGateway`（backend 内），无需额外服务。
- 若要 OPA：把 `policy/driver_action_policy.rego` 挂到 OPA server 端点，并在
  Policy Gateway 的 Provider Adapter 里调用（保持与自研规则一致，V34-010）。

## 5. 版本验收（V34-001 等「待基础设施」项）

代码合入 ≠ 版本验证完成。真实验收项（计划 §93）需真实环境执行：

- [x] Temporal server 端到端部署（起服务 + persistence/visibility）✅ 见 §1（`SERVING`、`default` namespace）
- [x] 无效 mTLS Worker 无法注册（双向 client-auth）✅ `drill_mtls_reject.py` **PASS**
- [ ] 真实 worker 强杀 drill（kill worker → Run 恢复 + Fixture 无重复）——需两 worker
- [ ] 强杀 Control Plane，Workflow 可恢复查询
- [ ] API/UI Shadow 结果一致率达门槛
- [ ] Worker drain 不收新任务

完成并记录 reviewer/环境/时间/Evidence 后，才能把 V3.4 标为 `VERIFIED`
（计划 §94 Release Gate），这就满足了 V3.5 的「上一版本依赖：V3.4 VERIFIED」。

## 6. 关联

- 实现：`backend/app/modules/aitde/workflow/`（gateway/service/router/policy/secret_resolver）
  + `backend/app/temporal/`（workflows/activities）
- 计划：`docs/aitde/versions/V3.4_Detailed_Development_Implementation_Plan.md`
- Worker 注册 API：`POST /api/v2/workers/heartbeat`

## 7. 实测记录（Evidence）

| 项 | 结果 | 环境 | 时间(UTC) | 命令 |
|----|------|------|-----------|------|
| Temporal server 端到端 | SERVING / healthy | local test | 2026-08-30 05:46 | `docker compose up -d` + `temporal operator cluster health` |
| Gateway + 全 9 步 workflow | 通过 | local test | 2026-08-30 | backend `run_worker` 连 127.0.0.1:7233 |
| mTLS invalid-cert-reject | **PASS** | local test 互信 mTLS | 2026-08-30 05:46 | `python scripts/drill_mtls_reject.py` |
