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
    assert cfg.provider_name == "默认"


def test_update_key_blank_keeps_existing(db_session):
    row = _add_provider(db_session)
    ai_config_service.update_provider(db_session, 1, row.id, {"name": "改名", "api_key": ""})
    cfg = ai_config_service.resolve(db_session, 1)
    assert cfg.provider_name == "改名"
    assert cfg.api_key == "sk-test-1234567890abcdef"  # key 留空不变


def test_list_masks_key(db_session):
    _add_provider(db_session)
    items = ai_config_service.list_providers(db_session, 1)
    assert items[0]["api_key"] == "sk****cdef"
    assert "api_key_encrypted" not in items[0]


def test_project_isolation(db_session):
    """多项目模型隔离验证：项目 A 的配置不泄漏给项目 B."""
    _add_provider(db_session, project_id=1, name="项目A提供方")
    cfg_a = ai_config_service.resolve_out(db_session, 1)
    assert cfg_a["configured"] is True
    assert cfg_a["provider"]["id"] > 0
    # 未配置任何提供方的项目 B：不得解析到项目 A 的配置。
    cfg_b = ai_config_service.resolve_out(db_session, 2)
    assert cfg_b["configured"] is False
    assert cfg_b["provider"] is None
    # 项目 B 显式配置后只解析到自己的提供方。
    _add_provider(db_session, project_id=2, name="项目B提供方")
    cfg_b2 = ai_config_service.resolve_out(db_session, 2)
    assert cfg_b2["configured"] is True
    assert cfg_b2["provider"]["name"] == "项目B提供方"


def test_discover_models_dedup(monkeypatch):
    """模型发现结果去重：/models 重复返回同 id 时只保留一个."""
    import httpx

    class _Resp:
        status_code = 200
        @staticmethod
        def raise_for_status():
            return None
        @staticmethod
        def json():
            return {"data": [
                {"id": "deepseek-v4-pro"},
                {"id": "deepseek-v4-flash"},
                {"id": "deepseek-v4-pro"},  # 重复
                {"id": None},              # 无 id 过滤
            ]}

    monkeypatch.setattr(httpx, "get", lambda *a, **k: _Resp())
    res = ai_config_service.discover_models("https://api.deepseek.com", "sk-xxx")
    assert res["ok"] is True
    assert res["models"] == ["deepseek-v4-pro", "deepseek-v4-flash"]
    assert res["count"] == 2
