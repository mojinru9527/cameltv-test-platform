"""Seed credential lifecycle regression tests."""
from __future__ import annotations

import logging
import secrets
from importlib import reload
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
import app.seed as seed
from app.core import db as db_module
from app.core.config import Settings
from app.core.db import Base
from app.core.security import verify_password
from app.models.project import Project, ProjectMember
from app.models.rbac import Permission, Role, RolePermission
from app.models.user import User


@pytest.fixture
def seed_session_factory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    patched_run_seed = seed.run_seed
    reload(seed)
    database_path = tmp_path / "seed-credentials.db"
    engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    monkeypatch.setattr(db_module, "SessionLocal", session_factory)
    yield session_factory
    engine.dispose()
    seed.run_seed = patched_run_seed


def _development_settings(**overrides: str) -> Settings:
    values = {
        "environment": "development",
        "secret_key": secrets.token_urlsafe(32),
        "admin_username": "batch55_admin",
        "admin_password": "",
        "tester_username": "batch55_tester",
        "tester_password": "",
        "viewer_username": "batch55_viewer",
        "viewer_password": "",
        "ai_enabled": False,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def _user_password_hash(session_factory, username: str) -> str:
    with session_factory() as db:
        user = db.scalar(select(User).where(User.username == username))
        assert user is not None
        return user.password


def _assert_tester_has_default_project(
    session_factory,
    username: str,
) -> None:
    with session_factory() as db:
        user = db.scalar(select(User).where(User.username == username))
        project = db.scalar(select(Project).where(Project.code == "cameltv"))
        assert user is not None
        assert project is not None
        membership = db.scalar(
            select(ProjectMember).where(
                ProjectMember.user_id == user.id,
                ProjectMember.project_id == project.id,
            )
        )
        assert membership is not None


def test_configured_seed_credentials_are_hashed_only_for_initial_creation(
    seed_session_factory,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    admin_password = f"test-admin-{secrets.token_urlsafe(16)}"
    tester_password = f"test-tester-{secrets.token_urlsafe(16)}"
    viewer_password = f"test-viewer-{secrets.token_urlsafe(16)}"
    local_settings = _development_settings(
        admin_password=admin_password,
        tester_password=tester_password,
        viewer_password=viewer_password,
    )
    monkeypatch.setattr(seed, "settings", local_settings)

    original_hash_password = seed.hash_password
    hashed_plaintexts: list[str] = []

    def tracking_hash_password(plaintext: str) -> str:
        hashed_plaintexts.append(plaintext)
        return original_hash_password(plaintext)

    monkeypatch.setattr(seed, "hash_password", tracking_hash_password)

    seed.run_seed()
    capsys.readouterr()

    admin_hash = _user_password_hash(
        seed_session_factory, local_settings.admin_username
    )
    tester_hash = _user_password_hash(
        seed_session_factory, local_settings.tester_username
    )
    viewer_hash = _user_password_hash(
        seed_session_factory, local_settings.viewer_username
    )
    assert verify_password(admin_password, admin_hash)
    assert verify_password(tester_password, tester_hash)
    assert verify_password(viewer_password, viewer_hash)
    _assert_tester_has_default_project(
        seed_session_factory,
        local_settings.tester_username,
    )
    assert hashed_plaintexts == [admin_password, tester_password, viewer_password]

    hashed_plaintexts.clear()
    seed.run_seed()
    second_output = capsys.readouterr()

    assert hashed_plaintexts == []
    assert second_output.out == ""
    assert second_output.err == ""
    assert (
        _user_password_hash(seed_session_factory, local_settings.admin_username)
        == admin_hash
    )
    assert (
        _user_password_hash(seed_session_factory, local_settings.tester_username)
        == tester_hash
    )
    assert (
        _user_password_hash(seed_session_factory, local_settings.viewer_username)
        == viewer_hash
    )


def test_generated_seed_credentials_are_created_and_shown_only_once(
    seed_session_factory,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    local_settings = _development_settings()
    monkeypatch.setattr(seed, "settings", local_settings)

    generated_passwords = iter(
        [
            f"test-generated-admin-{secrets.token_urlsafe(12)}",
            f"test-generated-tester-{secrets.token_urlsafe(12)}",
            f"test-generated-viewer-{secrets.token_urlsafe(12)}",
        ]
    )
    generated_calls: list[str] = []

    def generate_test_password(_length: int = 32) -> str:
        value = next(generated_passwords)
        generated_calls.append(value)
        return value

    monkeypatch.setattr(secrets, "token_urlsafe", generate_test_password)

    with caplog.at_level(logging.WARNING, logger="uvicorn"):
        seed.run_seed()
    first_output = capsys.readouterr()
    assert len(generated_calls) == 3
    assert generated_calls[0] in caplog.text
    assert generated_calls[1] in first_output.out

    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="uvicorn"):
        seed.run_seed()
    second_output = capsys.readouterr()

    assert len(generated_calls) == 3
    assert second_output.out == ""
    assert second_output.err == ""
    assert caplog.records == []


def test_production_rejects_empty_seed_credentials() -> None:
    production_settings = Settings(
        _env_file=None,
        environment="production",
        secret_key=secrets.token_urlsafe(32),
        admin_password="",
        tester_password="",
        ai_enabled=False,
        cookie_secure=True,
    )

    issues = production_settings.validate_security()

    assert any("ADMIN_PASSWORD" in issue for issue in issues)
    assert any("TESTER_PASSWORD" in issue for issue in issues)


def test_production_without_demo_users_does_not_require_tester_password() -> None:
    production_settings = Settings(
        _env_file=None,
        environment="production",
        secret_key=secrets.token_urlsafe(32),
        admin_password=secrets.token_urlsafe(16),
        seed_demo_users=False,
        ai_enabled=False,
        cookie_secure=True,
    )

    issues = production_settings.validate_security()

    assert not any("TESTER_PASSWORD" in issue for issue in issues)


def test_seed_demo_users_disabled_skips_tester_and_viewer(
    seed_session_factory,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    local_settings = _development_settings(seed_demo_users=False)
    monkeypatch.setattr(seed, "settings", local_settings)

    seed.run_seed()
    capsys.readouterr()

    with seed_session_factory() as db:
        assert (
            db.scalar(select(User).where(User.username == local_settings.admin_username))
            is not None
        )
        assert (
            db.scalar(select(User).where(User.username == local_settings.tester_username))
            is None
        )
        assert (
            db.scalar(select(User).where(User.username == local_settings.viewer_username))
            is None
        )
        project = db.scalar(select(Project).where(Project.code == "cameltv"))
        assert project is not None


def test_tester_role_can_list_visible_schedule_module(
    seed_session_factory,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(seed, "settings", _development_settings())
    seed.run_seed()
    capsys.readouterr()

    with seed_session_factory() as db:
        tester_role = db.scalar(select(Role).where(Role.code == "tester"))
        schedule_list = db.scalar(
            select(Permission).where(Permission.code == "schedule:list")
        )
        assert tester_role is not None
        assert schedule_list is not None
        assignment = db.scalar(
            select(RolePermission).where(
                RolePermission.role_id == tester_role.id,
                RolePermission.permission_id == schedule_list.id,
            )
        )
        assert assignment is not None




def test_local_docs_require_credentials_before_initial_database_creation() -> None:
    backend_root = Path(__file__).parents[1]
    readme = (backend_root / "README.md").read_text(encoding="utf-8")
    env_example = (backend_root / ".env.example").read_text(encoding="utf-8")

    assert "首次创建本地数据库之前" in readme
    assert "重启不会生成或显示替代密码" in readme
    assert "ADMIN_PASSWORD" in readme
    assert "TESTER_PASSWORD" in readme
    assert "SECRET_KEY" in readme
    assert "仅在首次创建种子用户时自动生成" in env_example
