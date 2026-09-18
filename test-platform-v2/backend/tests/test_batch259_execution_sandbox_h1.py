"""Batch 259 / B2-1 — 本地执行沙箱 H1 的可执行校验（关闭 C258-2 的节点侧凭据隔离）。

H1 的四条要求落到本仓可执行的形态：
  1. **无平台 SECRET / DB 口令**：子进程环境只保留白名单（真实子进程验证，不是看代码）；
  2. **无内网 egress（白名单=被测系统 + 平台 API）**：白名单值作为唯一事实源下发给子进程；
  3. **危险 API 静态拦截**：读 `.env` / 连内网 / 写持久卷三类代码在执行前被拒（B2-2 已实现）；
  4. **非 root** 与内核级网络/文件隔离属**部署层**（容器 / 网络命名空间），
     本模块 docstring 明确声明边界，不假装已具备（与 B2-3「dry-run 不是沙箱」同一原则）。
"""
from __future__ import annotations

import subprocess
import sys

import pytest

from app.core import execution_sandbox, spec_guard
from app.core.config import settings


class TestChildEnvCarriesNoPlatformSecrets:
    _SECRETS = {
        "SECRET_KEY": "super-secret-value",
        "DATABASE_URL": "postgresql://user:pass@db.internal:5432/platform",
        "PINGCODE_API_TOKEN": "pc-token",
        "CONFLUENCE_API_TOKEN": "cf-token",
        "AI_API_KEY": "sk-ai",
        "ADMIN_PASSWORD": "admin-pass",
    }

    def test_allowlist_strips_every_secret(self, monkeypatch):
        for key, value in self._SECRETS.items():
            monkeypatch.setenv(key, value)
        env = execution_sandbox.sandbox_environment()
        leaked = sorted(key for key in self._SECRETS if key in env)
        assert leaked == [], f"子进程环境泄露了平台凭据: {leaked}"

    def test_real_subprocess_cannot_read_secrets(self, monkeypatch):
        """真起一个子进程读环境变量——证明"无凭据"不只是看代码得出的结论。"""
        for key, value in self._SECRETS.items():
            monkeypatch.setenv(key, value)
        env = execution_sandbox.sandbox_environment()
        probe = (
            "import os,json;"
            f"print(json.dumps({{k: os.environ.get(k) for k in {list(self._SECRETS)!r}}}))"
        )
        result = subprocess.run(
            [sys.executable, "-c", probe],
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, result.stderr[-400:]
        import json

        seen = json.loads(result.stdout.strip() or "{}")
        assert all(value is None for value in seen.values()), f"子进程读到了凭据: {seen}"

    def test_platform_contract_vars_are_still_passed(self, monkeypatch):
        """E2E 契约变量 CAMELTV_* 必须保留，否则体育用例会因缺变量而失败。"""
        monkeypatch.setenv("CAMELTV_BASE_URL", "https://sut.example.com")
        env = execution_sandbox.sandbox_environment()
        assert env.get("CAMELTV_BASE_URL") == "https://sut.example.com"


class TestEgressAllowlistIsSingleSourceOfTruth:
    def test_configured_allowlist_is_exported_to_children(self, monkeypatch):
        monkeypatch.setattr(
            settings, "execution_egress_allowlist", "sut.example.com,api.swiftbugs.cn"
        )
        env = execution_sandbox.sandbox_environment()
        assert env.get("CAMELTV_EGRESS_ALLOWLIST") == "sut.example.com,api.swiftbugs.cn"

    def test_unset_allowlist_is_not_invented(self, monkeypatch):
        monkeypatch.setattr(settings, "execution_egress_allowlist", "")
        env = execution_sandbox.sandbox_environment()
        assert "CAMELTV_EGRESS_ALLOWLIST" not in env


class TestGeneratedCodeCannotReachSecretsEgressOrDisk:
    """DoD 三类动作：读 `.env` / 连内网 / 写持久卷，必须在执行前被拒。"""

    def test_reading_dotenv_file_is_refused(self):
        code = "const fs = require('fs');\nconst t = fs.readFileSync('.env', 'utf8');"
        findings = spec_guard.assert_spec_safe(code)
        assert findings, "读 .env 的代码没有被拦截"

    def test_connecting_to_internal_host_is_refused(self):
        code = "const net = require('net');\nnet.connect(80, '169.254.169.254');"
        findings = spec_guard.assert_spec_safe(code)
        assert findings, "连内网的代码没有被拦截"

    def test_writing_persistent_volume_is_refused(self):
        code = "const fs = require('fs');\nfs.writeFileSync('/app/storage/evidence.txt', 'x');"
        findings = spec_guard.assert_spec_safe(code)
        assert findings, "写持久卷的代码没有被拦截"


class TestBoundaryIsStatedNotImplied:
    def test_module_documents_what_is_not_enforced_in_process(self):
        """边界必须写清楚：进程内做不到内核级隔离，docstring 要明说而不是让人误以为已有沙箱。"""
        doc = (execution_sandbox.__doc__ or "").lower()
        assert "容器" in doc or "命名空间" in doc or "namespace" in doc, (
            "沙箱模块必须声明哪一层不属于进程内职责（部署层）"
        )
        assert "部署" in doc or "deployment" in doc
