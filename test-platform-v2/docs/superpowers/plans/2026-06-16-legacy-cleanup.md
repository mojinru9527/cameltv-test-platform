# Legacy Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the remaining low-priority technical debt items in the test platform except environment-specific ELK configuration.

**Architecture:** The frontend uses route-level code splitting plus Vite vendor chunks to reduce the initial JavaScript payload. Placeholder routes become real Ant Design work surfaces. The backend keeps developer-friendly auto table creation by default, while adding Alembic configuration and an opt-out switch for production migration control.

**Tech Stack:** React 18, Vite 5, Ant Design 5, FastAPI, SQLAlchemy 2, Alembic, SQLite.

---

### Task 1: Frontend Bundle Optimization

**Files:**
- Modify: `frontend/src/router/index.tsx`
- Modify: `frontend/vite.config.ts`

- [x] Wrap route elements with `React.lazy` and `Suspense`.
- [x] Add Vite `manualChunks` for React, Ant Design, Axios, and shared vendor modules.
- [ ] Run `npm run build` and compare chunk output.

### Task 2: Replace Placeholder Pages

**Files:**
- Create: `frontend/src/pages/requirement/index.tsx`
- Create: `frontend/src/pages/apitest/index.tsx`
- Modify: `frontend/src/router/index.tsx`

- [x] Build a requirement dashboard that lists local requirement assets and test coverage signals.
- [x] Build an API testing console that reuses auth/project headers and supports saved requests.
- [ ] Verify both routes load after login.

### Task 3: Alembic Migration Path

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/main.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/20260616_0001_initial_schema.py`
- Modify: `backend/.env.example`
- Modify: `backend/README.md`

- [ ] Add Alembic dependency and metadata wiring.
- [ ] Add `AUTO_CREATE_TABLES` switch so production can disable `create_all`.
- [ ] Document `alembic upgrade head` and ELK `.env` settings.

### Task 4: Verification and Service Startup

**Files:**
- No source files.

- [ ] Run frontend typecheck/build.
- [ ] Run backend import/migration smoke check.
- [ ] Start backend and frontend dev servers for user acceptance.
