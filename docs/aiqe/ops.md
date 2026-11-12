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
2. 打开 `/runs`，创建一次 Run（或用 API `POST /api/v1/aiqe/runs`）；
3. 确认 Run 详情返回 `status/outcome`；
4. `pytest tests/test_aiqe_run_api.py -q` 验证 API 契约。

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

## 6. 常见问题

| 现象 | 处理 |
|------|------|
| `alembic` 多 head | `python -m alembic heads` 应仅 1 个 |
| 前端 401 | 检查后端 `SECRET_KEY` 与 token |
| 证据 403 | 跨项目访问被拒；确认 `project_id` |
| MinIO 不可用 | `STORAGE_BACKEND=local` 回退 |
