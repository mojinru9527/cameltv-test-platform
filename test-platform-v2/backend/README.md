---
title: "CamelTv 测试平台后端"
owner: "backend-team"
last_reviewed: "2026-06-26"
status: "active"
expires: "2026-12-26"
tags: ["backend", "fastapi", "sqlalchemy", "sqlite", "python"]
related: ["test-platform-v2/frontend/README.md", "test-platform-v2/backend/CLAUDE.md"]
---

# cameltv-test-backend

CamelTv test platform backend, built with FastAPI, SQLAlchemy, and SQLite by default.

## Local Startup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

- API docs: http://localhost:8000/docs
- OpenAPI: http://localhost:8000/openapi.json
- Login credentials are supplied by the administrator through environment variables; no reusable default password is published.

### Repeatable local acceptance credentials

首次创建本地数据库之前，请在已忽略跟踪的 `backend/.env` 中显式设置强
`ADMIN_PASSWORD`、`TESTER_PASSWORD` 和 `SECRET_KEY`，再启动 FastAPI。可使用
`python -c "import secrets; print(secrets.token_urlsafe(32))"` 分别生成独立随机值；
不要把生成结果写入仓库、测试报告或截图。

如果种子账号已经存在，`run_seed()` 会保留原密码哈希；重启不会生成或显示替代密码。
未配置密码时，开发模式只会在首次创建对应种子用户时生成并显示一次。遗失首次凭据后，
应通过授权的密码重置流程处理；仅限可丢弃的本地验收数据库可以重建。

## Database Migrations

Local development keeps `AUTO_CREATE_TABLES=true` so a fresh SQLite database starts without extra steps.

For production deployments:

```bash
set AUTO_CREATE_TABLES=false
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Create future migrations after model changes:

```bash
alembic revision --autogenerate -m "describe schema change"
alembic upgrade head
```

## ELK / Kibana Links

Kibana links are generated only when the deployment environment provides:

```bash
ELK_BASE_URL=https://kibana.example.com/app/kibana
ELK_INDEX=cameltv-*
```

Keep `ELK_BASE_URL` blank for local development.
