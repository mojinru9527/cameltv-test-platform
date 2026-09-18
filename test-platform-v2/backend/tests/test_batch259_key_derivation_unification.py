"""Batch 259 / B2-5 — 密钥派生统一到 cipher.py + 启动 fail-fast（关闭审计基线 S5）。

原状：`cipher.py` 用 `effective_secret_key`（dev 下每次会话随机），
`ai_config_service._fernet()` 用 `secret_key`（dev 下是空串 → `sha256("")` 是**公开常量密钥**）。
两条路各加密各的，换 SECRET_KEY 后存量密文静默解不开。

本文件同时包含一条**可执行校验**：全仓不得再出现第二处 `sha256(...secret_key...)` 派生
（bug-guard 规则 4：文档承诺 = 可执行校验）。
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

import app
from app.core import cipher
from app.core.config import settings
from app.models.ai_provider import AiProvider
from app.services import ai_config_service


class TestSingleDerivationImplementation:
    def test_only_cipher_py_builds_a_fernet_key(self):
        """Fernet 密钥构造（sha256 摘要 → urlsafe_b64）只能出现在 cipher.py。

        DoD 原文给的 `rg "sha256\\(.*secret_key"` 现为 **0 命中**（实现把密钥先绑定到
        局部变量再哈希），比"只命中 cipher.py"更强。但 0 命中会让该检查失去防回归能力，
        所以这里改用**派生特征**兜底：任何新的密钥派生都必须写成 urlsafe_b64encode，
        一旦出现在别处即失败。
        """
        app_root = Path(app.__file__).parent
        offenders = [
            str(path.relative_to(app_root))
            for path in app_root.rglob("*.py")
            if "urlsafe_b64encode" in path.read_text(encoding="utf-8", errors="replace")
            and path.name != "cipher.py"
        ]
        assert offenders == [], f"存在第二处 Fernet 密钥构造: {offenders}"

    def test_only_cipher_py_derives_key_from_secret(self):
        """除 cipher.py 外，任何文件都不得自己 sha256(secret_key) 派生密钥。"""
        app_root = Path(app.__file__).parent
        pattern = re.compile(r"sha256\([^)]*secret_key", re.IGNORECASE)
        offenders = [
            str(path.relative_to(app_root))
            for path in app_root.rglob("*.py")
            if pattern.search(path.read_text(encoding="utf-8", errors="replace"))
            and path.name != "cipher.py"
        ]
        assert offenders == [], f"存在第二套密钥派生实现: {offenders}"

    def test_ai_config_encrypts_with_cipher_key(self, monkeypatch):
        """互认证明：ai_config_service 产出的密文必须能被 cipher.py 解开（同一密钥）。"""
        monkeypatch.setattr(settings, "secret_key", "unit-test-secret")
        token = ai_config_service._encrypt_key("sk-abc")
        assert cipher.decrypt_value(token) == "sk-abc"

    def test_ai_config_decrypts_cipher_output(self, monkeypatch):
        monkeypatch.setattr(settings, "secret_key", "unit-test-secret")
        token = cipher.encrypt_value("sk-xyz")
        assert ai_config_service._decrypt_key(token) == "sk-xyz"

    def test_rotated_key_surfaces_as_business_error_not_raw_500(self, monkeypatch):
        """密钥轮换后存量密文解不开：必须是可读业务错误，不能是裸 500。

        这是既有契约（避免前端只看到"服务器错误"），本批只改变密钥来源，不改该行为。
        """
        monkeypatch.setattr(settings, "secret_key", "unit-test-secret")
        with pytest.raises(ai_config_service.AIProviderUnconfiguredError) as exc:
            ai_config_service._decrypt_key("not-a-fernet-token")
        assert "重新输入" in str(exc.value)


class TestStartupFailFast:
    def test_no_key_with_existing_ciphertext_fails_fast(self, db_session, monkeypatch):
        monkeypatch.setattr(settings, "secret_key", "")
        db_session.add(
            AiProvider(project_id=1, name="p", api_key_encrypted="gAAAAA-ciphertext")
        )
        db_session.commit()

        with pytest.raises(RuntimeError) as exc:
            cipher.assert_key_for_existing_ciphertext(db_session)
        assert "SECRET_KEY" in str(exc.value)
        assert "ai_provider" in str(exc.value)

    def test_no_key_and_no_ciphertext_is_allowed(self, db_session, monkeypatch):
        monkeypatch.setattr(settings, "secret_key", "")
        cipher.assert_key_for_existing_ciphertext(db_session)  # 不抛即可

    def test_configured_key_skips_the_check(self, db_session, monkeypatch):
        monkeypatch.setattr(settings, "secret_key", "configured")
        db_session.add(
            AiProvider(project_id=1, name="p", api_key_encrypted="gAAAAA-ciphertext")
        )
        db_session.commit()
        cipher.assert_key_for_existing_ciphertext(db_session)

    def test_empty_string_ciphertext_is_not_counted(self, db_session, monkeypatch):
        monkeypatch.setattr(settings, "secret_key", "")
        db_session.add(AiProvider(project_id=1, name="p", api_key_encrypted=""))
        db_session.commit()
        cipher.assert_key_for_existing_ciphertext(db_session)
