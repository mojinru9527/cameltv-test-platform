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
