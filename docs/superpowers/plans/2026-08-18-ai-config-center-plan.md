# AI 模型配置中心 Implementation Plan（子项目 A）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立项目级 AI 提供方配置中心（多提供方池、Key 加密存储、无配置即禁用），全平台 8 处 AI 消费点从读全局 env 改为按项目解析。

**Architecture:** 新增 `ai_provider` 表（项目级）+ `ai_config_service`（Fernet 加密 / resolve / CRUD / 连通测试）；统一异常 `AIProviderUnconfiguredError`；8 处消费点改 `ai_config_service.resolve(project_id)` 取运行时配置；DSH runner 凭据由任务绑定的 provider 注入；前端新增「AI 配置」页（项目菜单区）+ DSH 页配置状态条。

**Tech Stack:** FastAPI / SQLAlchemy 2.0 / Alembic / cryptography(Fernet) / React 19 / shadcn-ui

**设计文档**：`docs/superpowers/plans/2026-08-18-dsh-test-entry-and-ai-config-design.md` §4

---

### Task 1: 依赖 + ai_provider 模型 + 迁移

**Files:**
- Modify: `test-platform-v2/backend/requirements.txt`
- Create: `test-platform-v2/backend/app/models/ai_provider.py`
- Create: `test-platform-v2/backend/alembic/versions/20260818_ai_provider.py`

- [ ] **Step 1: requirements.txt 显式声明 cryptography**

在 `test-platform-v2/backend/requirements.txt` 追加（lock 已含 cryptography==49.0.0，此处补直接依赖声明）：

```
cryptography>=42.0
```

- [ ] **Step 2: 创建模型**

```python
"""AI 提供方配置（项目级）—— Batch A（AI 模型配置中心）。"""
from __future__ import annotations

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin


class AiProvider(Base, TimestampMixin):
    __tablename__ = "ai_provider"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(String(100))          # 展示名（如 "DeepSeek 官方"）
    provider_type: Mapped[str] = mapped_column(String(30), default="openai_compatible")  # deepseek_official | openai_compatible
    api_base_url: Mapped[str] = mapped_column(String(500), default="")
    api_key_encrypted: Mapped[str] = mapped_column(Text, default="")  # Fernet 加密，绝不落明文
    models: Mapped[str] = mapped_column(Text, default="[]")  # JSON 数组（模型清单）
    default_model: Mapped[str] = mapped_column(String(100), default="")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)  # 每项目至多一个
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
```

（`Base`/`TimestampMixin` 从 `app.core.db` 导入；与 `models/dsh_task.py` 同款声明。若 `TimestampMixin` 位于其他模块，按仓库现有模型的实际导入路径为准。）

- [ ] **Step 3: 模型注册 + Alembic 迁移**

在 `app/models/__init__.py` 导出 `AiProvider`（若该文件集中注册模型则追加 import 行）。

创建迁移文件 `alembic/versions/20260818_ai_provider.py`（参考 `20260817_b191_dsh_team_mode.py` 格式，SQLite/PG 兼容）：

```python
"""ai_provider 表（项目级 AI 提供方配置）"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260818_ai_provider"
down_revision = "<当前 head revision 标识>"  # 执行时用 `alembic heads` 查实际值
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_provider",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("provider_type", sa.String(30), nullable=False, server_default="openai_compatible"),
        sa.Column("api_base_url", sa.String(500), nullable=False, server_default=""),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False, server_default=""),
        sa.Column("models", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("default_model", sa.String(100), nullable=False, server_default=""),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("ai_provider")
```

- [ ] **Step 4: 验证**

Run: `cd test-platform-v2/backend && python -c "from app.models.ai_provider import AiProvider; print(AiProvider.__tablename__)"`
Expected: `ai_provider`。本地 `AUTO_CREATE_TABLES=true` 自动建表；迁移文件 `alembic upgrade head` 校验（若本机有迁移链）。

### Task 2: ai_config_service（加密 / resolve / CRUD / 连通测试）

**Files:**
- Create: `test-platform-v2/backend/app/services/ai_config_service.py`
- Create: `test-platform-v2/backend/tests/test_ai_config_service.py`

- [ ] **Step 1: 写失败测试**

```python
"""ai_config_service 单元测试：加密、resolve、CRUD、掩码。"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.db import Base
from app.models.ai_provider import AiProvider
from app.services.ai_config_service import (
    AIProviderUnconfiguredError,
    ai_config_service,
    mask_api_key,
)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _add_provider(db, project_id=1, *, is_default=True, name="DeepSeek 官方",
                  key="sk-test-1234567890abcdef", model="deepseek-v4-pro"):
    row = AiProvider(
        project_id=project_id, name=name, provider_type="openai_compatible",
        api_base_url="https://api.deepseek.com",
        api_key_encrypted=ai_config_service._encrypt_key(key),
        models='["deepseek-v4-pro","deepseek-v4-flash"]', default_model=model,
        is_default=is_default, enabled=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_mask_api_key():
    assert mask_api_key("sk-test-1234567890abcdef") == "sk****cdef"
    assert mask_api_key("short") == "****"


def test_resolve_returns_default_provider(db_session):
    _add_provider(db_session)
    cfg = ai_config_service.resolve(db_session, 1)
    assert cfg.api_key == "sk-test-1234567890abcdef"
    assert cfg.model == "deepseek-v4-pro"
    assert cfg.api_base_url == "https://api.deepseek.com"


def test_resolve_raises_when_unconfigured(db_session):
    with pytest.raises(AIProviderUnconfiguredError):
        ai_config_service.resolve(db_session, 99)


def test_resolve_prefers_default(db_session):
    _add_provider(db_session, is_default=False, name="备选")
    _add_provider(db_session, is_default=True, name="默认")
    cfg = ai_config_service.resolve(db_session, 1)
    assert cfg.name == "默认"


def test_update_key_blank_keeps_existing(db_session):
    row = _add_provider(db_session)
    ai_config_service.update_provider(db_session, 1, row.id, {"name": "改名", "api_key": ""})
    cfg = ai_config_service.resolve(db_session, 1)
    assert cfg.name == "改名"
    assert cfg.api_key == "sk-test-1234567890abcdef"  # key 留空不变


def test_list_masks_key(db_session):
    _add_provider(db_session)
    items = ai_config_service.list_providers(db_session, 1)
    assert items[0]["api_key"] == "sk****cdef"
    assert "api_key_encrypted" not in items[0]
```

- [ ] **Step 2: 运行确认失败**

Run: `cd test-platform-v2/backend && pytest tests/test_ai_config_service.py -v --tb=short`
Expected: FAIL（模块不存在）。

- [ ] **Step 3: 实现服务**

```python
"""AI 提供方配置服务（项目级）—— Batch A。

所有 AI 消费点统一经 `resolve(project_id)` 获取运行时配置；项目无配置抛
`AIProviderUnconfiguredError`（前端据此引导配置，AI 功能按项目禁用）。
"""
from __future__ import annotations

import base64
import hashlib
import json

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import APIException
from app.models.ai_provider import AiProvider

_DEEPSEEK_OFFICIAL_URL = "https://api.deepseek.com"


class AIProviderUnconfiguredError(APIException):
    def __init__(self) -> None:
        super().__init__(
            code=400,
            msg="当前项目未配置 AI 提供方，请在「AI 配置」中添加提供方后重试",
            http_status=400,
        )


class EffectiveAiConfig:
    """一次 resolve 的结果：解密后的运行时 AI 配置。"""

    def __init__(self, row: AiProvider) -> None:
        self.provider_id = row.id
        self.provider_name = row.name
        self.provider_type = row.provider_type
        self.api_base_url = (row.api_base_url or _DEEPSEEK_OFFICIAL_URL).rstrip("/")
        self.api_key = _decrypt_key(row.api_key_encrypted)
        self.model = row.default_model or _first_model(row.models)


def mask_api_key(key: str) -> str:
    if not key or len(key) <= 8:
        return "****"
    return f"{key[:2]}****{key[-4:]}"


def _first_model(models_json: str) -> str:
    try:
        models = json.loads(models_json or "[]")
        return models[0] if isinstance(models, list) and models else ""
    except (json.JSONDecodeError, IndexError, TypeError):
        return ""


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _encrypt_key(plain: str) -> str:
    if not plain:
        return ""
    return _fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def _decrypt_key(stored: str) -> str:
    if not stored:
        return ""
    return _fernet().decrypt(stored.encode("utf-8")).decode("utf-8")


class AiConfigService:
    # ── 读取 ──

    def resolve(self, db: Session, project_id: int) -> EffectiveAiConfig:
        """返回项目默认（或首个启用）提供方；无配置抛 AIProviderUnconfiguredError。"""
        row = db.scalar(
            select(AiProvider)
            .where(AiProvider.project_id == project_id, AiProvider.enabled.is_(True))
            .order_by(AiProvider.is_default.desc(), AiProvider.id.asc())
        )
        if row is None:
            raise AIProviderUnconfiguredError()
        return EffectiveAiConfig(row)

    def list_providers(self, db: Session, project_id: int) -> list[dict]:
        rows = db.scalars(
            select(AiProvider).where(AiProvider.project_id == project_id).order_by(AiProvider.id.asc())
        ).all()
        return [
            {
                "id": r.id,
                "name": r.name,
                "provider_type": r.provider_type,
                "api_base_url": r.api_base_url,
                "api_key": mask_api_key(_decrypt_key(r.api_key_encrypted)),
                "models": _models_list(r.models),
                "default_model": r.default_model,
                "is_default": r.is_default,
                "enabled": r.enabled,
            }
            for r in rows
        ]

    def resolve_out(self, db: Session, project_id: int) -> dict:
        try:
            cfg = self.resolve(db, project_id)
        except AIProviderUnconfiguredError:
            return {"configured": False, "provider": None}
        return {"configured": True, "provider": {"id": cfg.provider_id, "name": cfg.provider_name, "model": cfg.model}}

    # ── 写 ──

    def create_provider(self, db: Session, project_id: int, data: dict) -> AiProvider:
        models = data.get("models") or []
        if not models:
            raise APIException(code=400, msg="至少填写一个模型", http_status=400)
        default_model = (data.get("default_model") or "").strip() or models[0]
        row = AiProvider(
            project_id=project_id,
            name=(data.get("name") or "").strip(),
            provider_type=data.get("provider_type") or "openai_compatible",
            api_base_url=(data.get("api_base_url") or "").strip(),
            api_key_encrypted=_encrypt_key(data.get("api_key") or ""),
            models=json.dumps(models, ensure_ascii=False),
            default_model=default_model,
            is_default=bool(data.get("is_default")),
            enabled=bool(data.get("enabled", True)),
        )
        db.add(row)
        db.flush()
        self._ensure_single_default(db, project_id, row.id)
        db.commit()
        db.refresh(row)
        return row

    def update_provider(self, db: Session, project_id: int, provider_id: int, data: dict) -> AiProvider:
        row = self._get(db, project_id, provider_id)
        if "name" in data:
            row.name = (data["name"] or "").strip()
        if "provider_type" in data:
            row.provider_type = data["provider_type"]
        if "api_base_url" in data:
            row.api_base_url = (data["api_base_url"] or "").strip()
        if "api_key" in data and data["api_key"]:  # key 留空 = 不变
            row.api_key_encrypted = _encrypt_key(data["api_key"])
        if "models" in data:
            row.models = json.dumps(data["models"] or [], ensure_ascii=False)
        if "default_model" in data:
            row.default_model = (data["default_model"] or "").strip()
        if "is_default" in data and data["is_default"]:
            row.is_default = True
            self._ensure_single_default(db, project_id, row.id)
        if "enabled" in data:
            row.enabled = bool(data["enabled"])
        db.commit()
        db.refresh(row)
        return row

    def delete_provider(self, db: Session, project_id: int, provider_id: int) -> None:
        row = self._get(db, project_id, provider_id)
        if row.is_default:
            raise APIException(code=400, msg="默认提供方不可删除，请先转移默认", http_status=400)
        db.delete(row)
        db.commit()

    def _get(self, db: Session, project_id: int, provider_id: int) -> AiProvider:
        row = db.get(AiProvider, provider_id)
        if row is None or row.project_id != project_id:
            raise APIException(code=404, msg="AI 提供方不存在", http_status=404)
        return row

    def _ensure_single_default(self, db: Session, project_id: int, keep_id: int) -> None:
        rows = db.scalars(
            select(AiProvider).where(AiProvider.project_id == project_id, AiProvider.is_default.is_(True))
        ).all()
        for r in rows:
            if r.id != keep_id:
                r.is_default = False

    # ── 连通测试 ──

    def test_connection(self, db: Session, project_id: int, provider_id: int) -> dict:
        row = self._get(db, project_id, provider_id)
        cfg = EffectiveAiConfig(row)
        import time

        import httpx

        t0 = time.perf_counter()
        try:
            resp = httpx.post(
                f"{cfg.api_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {cfg.api_key}", "Content-Type": "application/json"},
                json={
                    "model": cfg.model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            return {"ok": True, "latency_ms": round((time.perf_counter() - t0) * 1000, 1), "model": cfg.model}
        except Exception as exc:  # noqa: BLE001 - 连通性测试需吞掉具体异常转为可读信息
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def _models_list(models_json: str) -> list[str]:
    try:
        data = json.loads(models_json or "[]")
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


ai_config_service = AiConfigService()
```

（若 `app.core.exceptions.APIException` 的构造签名不同，按仓库实际签名对齐；`timestamp` 列由 `TimestampMixin` 提供，`create_provider` 里无需手工赋值。）

- [ ] **Step 4: 运行测试确认通过**

Run: `cd test-platform-v2/backend && pytest tests/test_ai_config_service.py -v --tb=short`
Expected: 6 个用例 PASS。

- [ ] **Step 5: 提交**

```bash
git add test-platform-v2/backend/requirements.txt test-platform-v2/backend/app/models/ai_provider.py test-platform-v2/backend/alembic/versions/20260818_ai_provider.py test-platform-v2/backend/app/services/ai_config_service.py test-platform-v2/backend/tests/test_ai_config_service.py
git commit -m "feat(batch): AI 提供方配置服务 — Fernet 加密 + resolve/CRUD/连通测试"
```

### Task 3: API 路由 + 权限点 + 菜单

**Files:**
- Create: `test-platform-v2/backend/app/api/v1/ai_config.py`
- Modify: `test-platform-v2/backend/app/api/v1/router.py`、`test-platform-v2/backend/app/seed.py`
- Create: `test-platform-v2/backend/tests/test_ai_config_api.py`

- [ ] **Step 1: 路由实现**

```python
"""AI 配置 API —— /api/v1/ai-config/*（项目级提供方池）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.common import R
from app.services.ai_config_service import ai_config_service

router = APIRouter(prefix="/ai-config", tags=["AI 配置"])


class ProviderIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    provider_type: str = "openai_compatible"
    api_base_url: str = ""
    api_key: str = ""
    models: list[str] = []
    default_model: str = ""
    is_default: bool = False
    enabled: bool = True


class ProviderUpdateIn(BaseModel):
    name: str | None = None
    provider_type: str | None = None
    api_base_url: str | None = None
    api_key: str | None = None
    models: list[str] | None = None
    default_model: str | None = None
    is_default: bool | None = None
    enabled: bool | None = None


@router.get("/providers", response_model=R[list], summary="项目 AI 提供方列表")
def list_providers(
    current: CurrentUser = Depends(require_permission("ai_config:view")),
    db: Session = Depends(get_db),
):
    return R.ok(ai_config_service.list_providers(db, current.project_id or 0))


@router.post("/providers", response_model=R[dict], summary="新建 AI 提供方")
def create_provider(
    body: ProviderIn,
    current: CurrentUser = Depends(require_permission("ai_config:manage")),
    db: Session = Depends(get_db),
):
    row = ai_config_service.create_provider(db, current.project_id or 0, body.model_dump())
    return R.ok({"id": row.id})


@router.put("/providers/{provider_id}", response_model=R[dict], summary="更新 AI 提供方")
def update_provider(
    provider_id: int,
    body: ProviderUpdateIn,
    current: CurrentUser = Depends(require_permission("ai_config:manage")),
    db: Session = Depends(get_db),
):
    row = ai_config_service.update_provider(db, current.project_id or 0, provider_id, body.model_dump(exclude_none=True))
    return R.ok({"id": row.id})


@router.delete("/providers/{provider_id}", response_model=R[dict], summary="删除 AI 提供方")
def delete_provider(
    provider_id: int,
    current: CurrentUser = Depends(require_permission("ai_config:manage")),
    db: Session = Depends(get_db),
):
    ai_config_service.delete_provider(db, current.project_id or 0, provider_id)
    return R.ok({"deleted": provider_id})


@router.post("/providers/{provider_id}/test-connection", response_model=R[dict], summary="测试提供方连通性")
def test_connection(
    provider_id: int,
    current: CurrentUser = Depends(require_permission("ai_config:manage")),
    db: Session = Depends(get_db),
):
    return R.ok(ai_config_service.test_connection(db, current.project_id or 0, provider_id))


@router.get("/resolve", response_model=R[dict], summary="当前项目生效 AI 配置")
def resolve_config(
    current: CurrentUser = Depends(require_permission("ai_config:view")),
    db: Session = Depends(get_db),
):
    return R.ok(ai_config_service.resolve_out(db, current.project_id or 0))
```

（`require_permission` 若校验 project 数据范围，按仓库既有方式使用；`CurrentUser` 类型同 dsh_tasks.py。）

- [ ] **Step 2: router.py 注册**

在 `test-platform-v2/backend/app/api/v1/router.py` 的 import 列表加 `ai_config`，并追加 `api_router.include_router(ai_config.router)`（对齐 dsh_tasks.router 的注册方式）。

- [ ] **Step 3: seed.py 权限点 + 菜单**

在 `app/seed.py` 菜单权限点区（`("menu:dsh_tasks", ...)` 附近）追加：

```python
("menu:ai_config", "AI 配置", "", "/ai-config", "SettingsOutlined", 23),
```

在操作权限点区追加：

```python
("ai_config:view", "查看 AI 配置", "button"),
("ai_config:manage", "管理 AI 配置", "button"),
```

在 tester 角色权限分配列表追加 `"ai_config:view"`（admin 走 star 全量，无需显式加）。

- [ ] **Step 4: API 测试**

```python
"""AI 配置 API 测试：权限 + CRUD 闭环。"""
import pytest

from app.services.ai_config_service import ai_config_service


def _auth_headers(client, username="admin", password="admin123"):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['data']['token']}"}


@pytest.fixture()
def project_headers(client):
    return _auth_headers(client)


def test_list_providers_empty(project_headers, client):
    resp = client.get("/api/v1/ai-config/providers", headers=project_headers)
    assert resp.status_code == 200
    assert resp.json()["data"] == []


def test_create_and_resolve(project_headers, client):
    resp = client.post("/api/v1/ai-config/providers", headers=project_headers, json={
        "name": "DeepSeek 官方", "provider_type": "openai_compatible",
        "api_base_url": "https://api.deepseek.com", "api_key": "sk-test-abc",
        "models": ["deepseek-v4-pro"], "default_model": "deepseek-v4-pro", "is_default": True,
    })
    assert resp.status_code == 200
    provider_id = resp.json()["data"]["id"]
    lst = client.get("/api/v1/ai-config/providers", headers=project_headers).json()["data"]
    assert lst[0]["api_key"] == "****"  # 掩码，不出明文
    resolved = client.get("/api/v1/ai-config/resolve", headers=project_headers).json()["data"]
    assert resolved["configured"] is True
    assert resolved["provider"]["name"] == "DeepSeek 官方"


def test_unconfigured_resolve(project_headers, client):
    # 新项目无配置 → configured=false（消费点据此禁用/报错）
    resp = client.post("/api/v1/projects", headers=project_headers, json={"name": "新项目"})
    assert resp.status_code == 200
    # 切换项目后 resolve
    resp = client.get("/api/v1/ai-config/resolve", headers={**project_headers, "X-Project-Id": str(resp.json()["data"]["id"])})
    assert resp.json()["data"]["configured"] is False


def test_delete_default_forbidden(project_headers, client):
    pid = client.post("/api/v1/ai-config/providers", headers=project_headers, json={
        "name": "A", "api_key": "k", "models": ["m"], "is_default": True,
    }).json()["data"]["id"]
    resp = client.delete(f"/api/v1/ai-config/providers/{pid}", headers=project_headers)
    assert resp.status_code == 400  # 默认提供方不可删除
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd test-platform-v2/backend && pytest tests/test_ai_config_api.py -v --tb=short`
Expected: PASS（若 fixtures 命名/登录字段与仓库既有测试不同，按 `tests/test_dsh_tasks.py` 的 `dsh_client` fixture 模式对齐）。

- [ ] **Step 6: 提交**

```bash
git add test-platform-v2/backend/app/api/v1/ai_config.py test-platform-v2/backend/app/api/v1/router.py test-platform-v2/backend/app/seed.py test-platform-v2/backend/tests/test_ai_config_api.py
git commit -m "feat(batch): AI 配置 API + 权限点 ai_config:view/manage + 菜单"
```

### Task 4: 消费点改造（统一模式）

> **统一改造模式**：每个消费点把 `settings.ai_api_key / ai_api_base_url / ai_model` 替换为
> `ai_config_service.resolve(project_id)` 的结果；入口函数签名加 `project_id: int`；
> 无配置时按消费点语义处理（直接调用抛 `AIProviderUnconfiguredError` 由路由层转业务错误；
> 内部辅助函数返回 error 字段而非抛错）。`temperature/超时/重试` 继续沿用 settings 部署级参数。
> 每个子任务：改代码 → 跑该模块既有测试 → 提交。

- [ ] **Task 4a: ai_service.py（用例生成主链路）**

Modify: `test-platform-v2/backend/app/services/ai_service.py`

1. `_call_ai_api(system_prompt, user_message, label="", max_tokens=None)` → 加 `project_id: int` 参数；第 734 行 `if not settings.ai_api_key:` 改为：

```python
    try:
        cfg = ai_config_service.resolve(project_id)
    except AIProviderUnconfiguredError as exc:
        return {"result": None, "raw": "", "finish_reason": "error", "truncated": False, "error": str(exc)}
```

并把 743-749 行的 `settings.ai_api_base_url / settings.ai_api_key / settings.ai_model` 替换为 `cfg.api_base_url / cfg.api_key / cfg.model`。

2. `_call_ai_api_with_harness(...)` → 加 `project_id: int`，透传给 `_run_harness_generation` 与 `_call_ai_api`。

3. `generate_test_cases(...)` → 加 `project_id: int` 参数；第 1295 行 `if not settings.ai_api_key: raise ValueError(...)` 改为：

```python
    try:
        cfg = ai_config_service.resolve(project_id)
    except AIProviderUnconfiguredError as exc:
        raise ValueError(str(exc)) from exc
```

函数体内所有 `_call_ai_api_with_harness(...)` 调用点补 `project_id=project_id`（先 `grep -n "_call_ai_api" app/services/ai_service.py` 找出全部调用点逐个补）。

4. 第 1080 行附近 `if not settings.ai_api_key:` 检查同样改为 try/resolve（按上下文语义处理）。

5. 调用方穿透：`grep -rn "generate_test_cases\|_call_ai_api_with_harness" app/api/v1/ app/services/` 找出调用点，路由层传 `current.project_id or 0`，服务层内部调用传参。已知调用方：`app/api/v1/requirement_ai_generate.py:148`、`app/api/v1/requirement_ai.py`（异步任务）等。

- [ ] **Task 4b: case_compiler_service.py**

Modify: `test-platform-v2/backend/app/services/case_compiler_service.py`

`_call_llm_for_code(system_prompt, user_message)` → 加 `project_id: int`；第 229 行 `if not settings.ai_api_key: raise RuntimeError(...)` 改为 try/resolve 抛 `AIProviderUnconfiguredError`；236-248 行替换为 cfg 字段。入口编译函数（`compile_case` 系列，先 `grep -n "^def \|^async def "` 定位）加 project_id 并穿透；路由调用方传 `current.project_id or 0`。

- [ ] **Task 4c: triage_service.py（缺陷分类）**

Modify: `test-platform-v2/backend/app/services/triage_service.py`

`triage_failed_cases(...)` 与 `generate_defect_draft(...)` 加 `project_id: int`；第 100 行 `if use_llm and settings.ai_enabled and settings.ai_api_key:` 改为：

```python
    if use_llm and settings.ai_enabled:
        try:
            ai_config_service.resolve(project_id)
        except AIProviderUnconfiguredError:
            use_llm = False
```

`_llm_deep_analyze(classified)` → 加 project_id，275-281 行替换 cfg 字段。调用方 `app/api/v1/test_plan_execution.py:308/338/351` 传 `current.project_id or 0`。

- [ ] **Task 4d: knowledge/llm_json_client.py（知识中心 RAG 主调用）**

Modify: `test-platform-v2/backend/app/services/knowledge/llm_json_client.py`

`call_json_model(*, system_prompt, user_payload, max_tokens=4096)` → 加必填 `project_id: int`；79-82 行检查改为 try/resolve 抛 `LLMUnavailableError(str(exc))`；85-98/107-110 行替换 cfg 字段。

调用方穿透（面最大）：`grep -rn "call_json_model" app/services/knowledge/ app/api/v1/knowledge*.py` 列出全部调用点，逐层加 project_id，最终由知识中心路由（有 `current.project_id`）传入。**若某调用链来自后台线程/定时任务，从任务行取 project_id（参考 dsh_task 队列模式）。**

- [ ] **Task 4e: knowledge/agent_orchestrator.py（Agent 工作台执行）**

Modify: `test-platform-v2/backend/app/services/knowledge/agent_orchestrator.py`

`_call_llm_sync(system_prompt, user_message, max_tokens=4096)` → 加 `project_id: int`；35 行检查改为 try/resolve（返回 `{"result": None, "raw": "", "error": str(exc)}`）；40-46 行替换 cfg 字段。调用方（agent_run_service 流水线）穿透 project_id；`grep -rn "_call_llm_sync" app/services/knowledge/` 定位。

- [ ] **Task 4f: knowledge/skill_service.py（Skills 可用性）**

Modify: `test-platform-v2/backend/app/services/knowledge/skill_service.py`

`_skill_unavailable_reason()` → 加 `project_id: int`；145 行 `if not settings.ai_api_key:` 改为 `try: ai_config_service.resolve(project_id); except AIProviderUnconfiguredError: return "当前项目未配置 AI 提供方"`。`list_skills()` 加 project_id 并穿透；调用方（skills 相关路由）传 `current.project_id or 0`。

- [ ] **Task 4g: api_generalization_service.py（接口用例泛化）**

Modify: `test-platform-v2/backend/app/services/api_generalization_service.py`

`_enhance_with_ai(result)` → 加 `project_id: int`；304 行 `if not settings.ai_api_key:` 改为 try/resolve（失败降级 `result["mode"]="rule"`）；内部 `_call_ai_api` 调用补 `project_id=project_id`。入口 `generate_cases_from_endpoint(...)` 加 project_id 并穿透；调用方 `app/api/v1/apitest_cases.py:79/130`、`apitest_assets.py:164` 传 project_id。

- [ ] **Task 4h: dsh_runner.py + dsh_task_service.py（DSH 执行凭据）**

Modify: `test-platform-v2/backend/app/services/dsh/dsh_runner.py`、`test-platform-v2/backend/app/services/dsh/dsh_task_service.py`

1. `run_dsh_task(...)` 加参数 `provider=None`（`EffectiveAiConfig | None`）；141 行 `resolved_model = model or settings.dsh_model or settings.ai_model` 改为 `resolved_model = model or (provider.model if provider else None) or settings.dsh_model or settings.ai_model`；197-199/295-297 行 env 注入改为：

```python
    if provider is not None:
        env["DEEPSEEK_API_KEY"] = provider.api_key
        if provider.api_base_url:
            env["DEEPSEEK_BASE_URL"] = provider.api_base_url
    else:
        env["DEEPSEEK_API_KEY"] = settings.dsh_api_key_effective
        if settings.dsh_base_url_effective:
            env["DEEPSEEK_BASE_URL"] = settings.dsh_base_url_effective
```

2. `dsh_task_service.submit_task(...)`：提交时 `try: cfg = ai_config_service.resolve(db, project_id) except AIProviderUnconfiguredError: 返回 400 业务错误`；`params["provider_id"] = cfg.provider_id` 快照（**只存 provider_id，不存明文 key**）。

3. worker `execute_task`：从 params 取 provider_id → `db.get(AiProvider, provider_id)`（同项目校验）→ 构造 `EffectiveAiConfig` 传给 `run_dsh_task(provider=...)`；provider 缺失/被删 → 任务失败并提示"AI 提供方已被删除，请重新配置"。

4. `run_dsh_task` 的 `provider` 与 `model` 参数同时传入时 model 优先（任务指定模型覆盖提供方默认）。

**消费点改造完成后的回归验证**：`cd test-platform-v2/backend && pytest tests/ -x -q`（或先跑 `test_dsh_tasks.py test_ai_config_* test_requirement_ai* test_knowledge*` 子集），修正受影响的旧断言（原断言 `settings.ai_api_key` 注入行为的用例需更新为 provider 语义）。

### Task 5: 前端 AI 配置页

**Files:**
- Create: `test-platform-v2/frontend/src/api/aiConfig.ts`
- Create: `test-platform-v2/frontend/src/pages/ai-config/index.tsx`
- Modify: `test-platform-v2/frontend/src/router/index.tsx`

- [ ] **Step 1: API 客户端**

```ts
import api from './client'

export interface AiProviderItem {
  id: number
  name: string
  provider_type: string
  api_base_url: string
  api_key: string        // 掩码
  models: string[]
  default_model: string
  is_default: boolean
  enabled: boolean
}

export interface AiResolveResult {
  configured: boolean
  provider: { id: number; name: string; model: string } | null
}

export async function fetchAiProviders(signal?: AbortSignal): Promise<AiProviderItem[]> {
  return api.get('/ai-config/providers', { signal })
}

export async function createAiProvider(body: Record<string, unknown>): Promise<{ id: number }> {
  return api.post('/ai-config/providers', body)
}

export async function updateAiProvider(id: number, body: Record<string, unknown>): Promise<{ id: number }> {
  return api.put(`/ai-config/providers/${id}`, body)
}

export async function deleteAiProvider(id: number): Promise<{ deleted: number }> {
  return api.delete(`/ai-config/providers/${id}`)
}

export async function testAiProviderConnection(id: number): Promise<{ ok: boolean; latency_ms?: number; model?: string; error?: string }> {
  return api.post(`/ai-config/providers/${id}/test-connection`)
}

export async function fetchAiResolve(signal?: AbortSignal): Promise<AiResolveResult> {
  return api.get('/ai-config/resolve', { signal })
}
```

- [ ] **Step 2: 页面组件（列表 + 表单 Dialog + 测试连接）**

`pages/ai-config/index.tsx` 结构（复用 `@/components/ui/*` 与 `@/ui` 既有组件，模式对齐 `pages/system/index.tsx`）：

- 列表：Card + Table（名称/类型/地址/掩码 key/模型清单/默认模型/默认标记/启用/操作）
- 新建/编辑：Dialog + 表单字段（名称、类型 Select：deepseek_official|openai_compatible、地址、Key Password 输入、模型 tags 输入（逗号分隔→数组）、默认模型、设为默认 Switch、启用 Switch）
- 「测试连接」按钮：调 `testAiProviderConnection`，成功 toast `连通正常 (xxms)`，失败展示 error
- 删除：ConfirmActionDialog（默认项后端拒绝，前端先置灰）
- 未配置空态：EmptyState 引导文案
- 权限：`useAuthStore.hasPerm('ai_config:manage')` 控制写按钮显示

页面核心逻辑（节选）：

```tsx
const load = useCallback((signal?: AbortSignal) => {
  fetchAiProviders(signal)
    .then((items) => { if (!signal?.aborted) setProviders(items) })
    .catch(() => { if (!signal?.aborted) toast.error('加载 AI 配置失败') })
}, [])
```

表单提交/更新/删除/测试连接 handler 与 `pages/dsh-tasks/index.tsx` 的既有模式一致（loading 态、toast、成功后 load()）。

- [ ] **Step 3: 路由注册**

`router/index.tsx` 加：

```tsx
const AiConfigPage = lazy(() => import('@/pages/ai-config'))
// 路由表（对齐 dsh-tasks 行）：
{ path: 'ai-config', element: <PageLoader><AiConfigPage /></PageLoader> },
```

（菜单项由后端 `menu:ai_config` 权限点下发，前端路由按 path `/ai-config` 对齐。）

- [ ] **Step 4: 前端验证**

Run: `cd test-platform-v2/frontend && npm run typecheck && npm run build`
Expected: 0 错误，构建成功。

### Task 6: DSH 任务页配置状态条 + 关键入口未配置引导

**Files:**
- Modify: `test-platform-v2/frontend/src/pages/dsh-tasks/index.tsx`
- Modify: `test-platform-v2/frontend/src/pages/requirement/ReviewPage.tsx`（或需求生成入口所在页，按实际定位）
- Modify: `test-platform-v2/frontend/src/pages/apitest/components/ImportDialog.tsx`（接口批量生成入口）

- [ ] **Step 1: DSH 页状态条**

`dsh-tasks/index.tsx` 顶部状态区（现有 DSH 可用 Badge 旁）加 AI 配置状态：`useAbortableEffect` 里加 `fetchAiResolve(signal)`，`configured=false` 时显示：

```tsx
<div className="flex items-center gap-2 text-xs text-status-warning bg-status-warning-muted border border-status-warning-border rounded-md px-3 py-1.5">
  <AlertCircle className="size-4" />
  当前项目未配置 AI 提供方，<Link to="/ai-config" className="underline">去配置</Link>
</div>
```

`configured=true` 时显示 `AI: {provider.name} / {provider.model}` Badge。同时「新建任务」按钮在 `!aiConfigured` 时 disabled（避免提交后被后端拒绝）。

- [ ] **Step 2: 生成入口 disabled 引导（关键 3 处）**

对需求生成、接口批量生成、用例生成入口：页面加载时查 `fetchAiResolve`，未配置则生成按钮 disabled 并加 title/文案"当前项目未配置 AI 提供方，去 AI 配置页设置"。后端 `AIProviderUnconfiguredError` 400 提示作为兜底（未接入的入口不会静默失败）。

- [ ] **Step 3: 前端验证**

Run: `cd test-platform-v2/frontend && npm run typecheck && npm run build`
Expected: 0 错误，构建成功。

### Task 7: 文档与配置保鲜

- [ ] **Step 1: `.env.example`**：移除/注释 `AI_API_KEY / AI_API_BASE_URL / AI_MODEL / DSH_API_KEY / DSH_BASE_URL / DSH_MODEL / DSH_MODEL_POOL`（注明"已迁移至平台内 AI 配置，按项目管理"）；保留 DSH 部署基础设施项并注明含义。
- [ ] **Step 2: `test-platform-v2/CLAUDE.md` + `backend/CLAUDE.md`**：AI 配置章节改为「项目级 AI 配置（ai_provider + ai_config_service），消费点统一 resolve；无配置即禁用」；更新「关键模块速查」表加 ai_config。
- [ ] **Step 3: 提交**

```bash
git add test-platform-v2/.env.example test-platform-v2/CLAUDE.md test-platform-v2/backend/CLAUDE.md
git commit -m "docs(batch): AI 配置中心 env 退役说明 + CLAUDE.md 同步"
```

### Task 8: 全量回归

- [ ] **Step 1: 后端**

Run: `cd test-platform-v2/backend && ruff check app/ --select F821`
Expected: 0 错误。

Run: `cd test-platform-v2/backend && pytest tests/ -q`
Expected: 全量通过或记录基线失败集（不得新增失败）。

- [ ] **Step 2: 前端**

Run: `cd test-platform-v2/frontend && npm run typecheck && npm run build && npx vitest run`
Expected: 通过或记录基线失败集。

- [ ] **Step 3: 手工冒烟**

本地起前后端：新建项目 → AI 配置页创建 provider（掩码/测试连接）→ 无配置项目生成用例提示 → DSH 页状态条切换项目变化 → 有配置项目 DSH 任务成功执行（runner 注入项目 key）。

---

**Self-review 记录**：spec §4（A 子项目）覆盖——模型+加密（T1/T2）、解析层+8 消费点（T2/T4a-h）、CRUD+test-connection+resolve API（T3）、权限 ai_config:manage/view（T3）、前端配置页+引导（T5/T6）、env 退役+文档（T7）、迁移与回归（T1/T8）。测试用统一 `project_id` 参数命名，`ai_config_service` 单例名与 Task 2 一致；`EffectiveAiConfig` 字段（api_key/api_base_url/model）在 T4 各处引用一致。已知需执行时核对的仓库差异：`APIException` 构造签名、`TimestampMixin` 导入路径、`dsh_client` 测试 fixture 模式、`alembic heads` 实际值——已在对应步骤注明核对方式。
