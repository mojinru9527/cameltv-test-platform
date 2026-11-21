"""V16-021 验收：Dogfood 脚本无弱默认口令、凭据仅来自环境/Secret 文件。"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aiqe" / "evidence_local_20.py"


def test_no_hardcoded_password_or_password_cli_option():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "admin123" not in text
    assert 'add_argument("--password"' not in text
    assert "AIQE_EVIDENCE_PASSWORD" in text
    assert "AIQE_EVIDENCE_PASSWORD_FILE" in text


def test_missing_credentials_exits_nonzero_without_secret(tmp_path: Path):
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("AIQE_EVIDENCE_PASSWORD")
    }
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    env.setdefault("DATABASE_URL", "sqlite:///./data/v16-021-unused.db")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--runs", "1", "--output", str(tmp_path / "out.json")],
        cwd=str(Path(__file__).resolve().parents[1]),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode != 0
    output = (result.stdout or "") + (result.stderr or "")
    assert "AIQE_EVIDENCE_PASSWORD" in output
    assert "admin123" not in output
    assert "Traceback" not in output


def test_secret_file_provider_is_supported(tmp_path: Path):
    secret = tmp_path / "pwd.txt"
    secret.write_text("S3cret-From-File", encoding="utf-8")
    import importlib.util

    spec = importlib.util.spec_from_file_location("evidence_local_20", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    old_env = dict(os.environ)
    try:
        os.environ.pop("AIQE_EVIDENCE_PASSWORD", None)
        os.environ["AIQE_EVIDENCE_PASSWORD_FILE"] = str(secret)
        assert module.load_password() == "S3cret-From-File"
        os.environ["AIQE_EVIDENCE_PASSWORD"] = "Env-Wins"
        assert module.load_password() == "Env-Wins"
    finally:
        os.environ.clear()
        os.environ.update(old_env)
