# AIQE Ops — 空环境启动与最小 E2E

> 适用：本地/测试环境从零起 AIQE（不含生产密钥）。生产操作见 `rollback.md`。

## 1. 前置

| 组件 | 版本 |
|------|------|
| Python | 3.12+ |
| Node.js | 20+ |
| PostgreSQL | 16（生产）；SQLite（本地默认） |
| MinIO（可选） | 任意近期版本（证据存储） |

## 2. 后端

```bash
cd test-platform-v2/backend
python -m venv .venv && . .venv/Scripts/activate   # Windows
pip install -r requirements.txt
cp .env.example .env                                # 按需改 DATABASE_URL/SECRET_KEY
python -m alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

健康检查：`GET http://127.0.0.1:8000/api/v1/open/health` → 200。

## 3. 前端

```bash
cd test-platform-v2/frontend
npm ci
npm run dev -- --port 5173
```

## 4. 最小 E2E（空库）

1. 登录后创建项目；
2. 注册能力节点（`node_capability_manifests` 需 `available=true` 且有 `last_evidence_ref`）；
3. 创建并审批 Workflow（`approval_status=approved`，checksum 冻结）；
4. `POST /api/v1/aiqe/runs`（v1.4 起支持真实 launch；生产默认关闭）：

```bash
curl -X POST "$BASE/api/v1/aiqe/runs" \
  -H "Authorization: Bearer $TOKEN" -H "X-Project-Id: 1" \
  -H "Content-Type: application/json" \
  -d '{"workflow_definition_id":"<uuid>","launch_key":"demo-1","build_ref":"local"}'
```

5. 确认返回 `run.status=RUNNING`、`preflight.ok=true`，并生成 NodeRun/ExecutionJob；
6. 启动进程内执行器（仅 http/db）：

```bash
AIQE_INPROCESS_EXECUTOR_ENABLED=true uvicorn app.main:app --port 8000
```

7. 外部浏览器/设备节点用：

```bash
python scripts/qa/aiqe_local_runner.py --base-url http://127.0.0.1:8000 \
  --project-id 1 --node-id local-device-runner --username ... --password ...
```

8. Run 详情：`GET /api/v1/aiqe/runs/{id}/nodes` 查看 Attempt/Assertion/Artifact；
9. `pytest tests/test_aiqe_execution_pipeline.py tests/test_aiqe_run_api_v14.py -q` 验证执行链契约。

## 4.1 状态对账（必须定时）

```bash
python scripts/qa/aiqe_reconcile.py --stale-seconds 900
```

建议每 1–5 分钟 cron 一次；收敛过期租约、丢失 Job、永久 RUNNING，并保证 `COMPLETED` 有 outcome。

## 4.2 v1.4 安全开关

| 环境变量 | 默认 | 说明 |
|---|---|---|
| `AIQE_PROD_RUN_CREATE_ENABLED` | `false` | 生产 Run 创建总开关；打开需独立审批 |
| `AIQE_HTTP_ENFORCE_SSRF` | `true` | 拒绝 localhost/私网/云元数据 |
| `AIQE_HTTP_ALLOW_PRIVATE` | `false` | 仅 Test 环境显式打开 |
| `AIQE_HTTP_ALLOWED_HOSTS` | 空 | 逗号分隔的域名 allowlist（支持 `*.example.com`） |
| `AIQE_DB_READONLY_URL` | 空 | DB-RO Driver 连接；未配置时 DB 节点 BLOCKED |
| `AIQE_DB_QUERY_REGISTRY_JSON` | 空 | 只读 query key 模板注册表 |
| `AIQE_SECRET_<KEY>` / `AIQE_SECRETS_JSON` | — | Runner 运行时注入 secret；不落库 |
| `AIQE_INPROCESS_EXECUTOR_ENABLED` | `false` | 仅 http/db；浏览器/设备仍由外部 Runner 执行 |

## 5. AIQE 关键迁移

| 迁移 | 内容 |
|------|------|
| 20261113 | run_artifacts |
| 20261115 | node_capability_manifests |
| 20261116 | agent_executions |
| 20261117 | execution_profiles |
| 20261118 | triage_experiments |
| 20261119 | defect AIQE 字段 |
| 20261120 | defect_regressions |
| 20261121 | noise_rules |
| 20261122 | learning_candidates / bug_patterns |
| 20261123 | mutation_ledger |
| 20261124 | v1.4 执行字段 + `aiqe_quality_gate_snapshots`（单 head） |

迁移演练（SQLite 本地）：

```bash
DATABASE_URL=sqlite:///./data/aiqe-v14.db python -m alembic upgrade head
DATABASE_URL=sqlite:///./data/aiqe-v14.db python -m alembic downgrade -1
DATABASE_URL=sqlite:///./data/aiqe-v14.db python -m alembic upgrade head
```

> SQLite 的初始迁移使用 `Base.metadata.create_all()`，UNIQUE 约束属于表定义，`DROP COLUMN` 不可用；v1.4 downgrade 在 SQLite 保留追加列，PostgreSQL 走真实回滚。

## 6. 常见问题

| 现象 | 处理 |
|------|------|
| `alembic` 多 head | `python -m alembic heads` 应仅 1 个 |
| 前端 401 | 检查后端 `SECRET_KEY` 与 token |
| 证据 403 | 跨项目访问被拒；确认 `project_id` |
| MinIO 不可用 | `STORAGE_BACKEND=local` 回退 |
