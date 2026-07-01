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
- Default account: `admin / admin123`

## Database Migrations

Local development keeps `AUTO_CREATE_TABLES=true` so a fresh SQLite database starts without extra steps.

For production or shared test environments:

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
