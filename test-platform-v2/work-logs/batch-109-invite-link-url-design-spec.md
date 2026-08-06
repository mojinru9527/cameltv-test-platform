# Batch 109 — Design Spec（邀请链接正式域名 + 生产种子演示用户开关）

> **Design (🎨)** | Date: 2026-08-06 | Status: 就绪

## 0. 技术体系确认

后端 FastAPI + SQLAlchemy + pydantic-settings；前端本次无改动（已支持 `?invite=`，`frontend/src/pages/register/index.tsx:44,72`）。

## 1. 配置契约

| 配置项 | 环境变量 | 默认 | 用途 |
|--------|---------|------|------|
| `frontend_url` | `FRONTEND_URL` | `""` | 可分享链接（项目邀请）使用的正式前端地址；空=回退当前请求域名 |
| `seed_demo_users` | `SEED_DEMO_USERS` | `true` | 是否创建内置演示账号 tester/viewer 及其角色/成员关系 |

生产校验联动：`seed_demo_users=true` 时继续要求 `TESTER_PASSWORD`（config.py `validate_security`）；false 时豁免。

## 2. API 契约（无 schema 变更，仅 url 字段生成规则）

`POST /api/v1/projects/{project_id}/invites` → `ProjectInviteOut.url`：

```
base = settings.frontend_url 若为空 → str(req.base_url).rstrip("/")
url  = f"{base}/register?invite={token}"
```

锚点：`backend/app/api/v1/project.py:create_project_invite`。

## 3. Seed 行为状态表

| 场景 | admin | 默认项目 | tester/viewer | 角色/成员关系 |
|------|-------|---------|---------------|---------------|
| `SEED_DEMO_USERS=true`（默认） | 创建/幂等 | 创建/幂等 | 创建/幂等 | 创建/幂等 |
| `SEED_DEMO_USERS=false` | 创建/幂等 | 创建/幂等 | **不创建** | **不创建** |

锚点：`backend/app/seed.py:run_seed`。

## 4. 设计 QA 走查发现

- ⚪ P3-01 邀请链接协议：`req.base_url` 在反代后可能丢失 https → 由 `FRONTEND_URL` 显式配置解决；未配置时回退并保持兼容（`project.py`）。
- 前端零改动，无组件/布局/状态设计项。

## 5. 设计签核

结论：通过（后端配置契约 + 种子行为表，无 UI 项）。
