"""M3 / TA-017：TesterArmy Adapter 单测（本地 python 脚本模拟）。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from app.aiqe.drivers.external_e2e_driver import (
    E2EAdapterError,
    E2EReplayMismatch,
    TesterArmyAdapter,
)


def make_script(tmp_path: Path, body: str) -> Path:
    script = tmp_path / "testerarmy_case.py"
    script.write_text(body, encoding="utf-8")
    return script


def pass_script(tmp_path: Path) -> Path:
    return make_script(
        tmp_path,
        """
import sys, pathlib
out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
(out / "trace.zip").write_bytes(b"trace")
(out / "report.json").write_text("{}")
(out / "screenshot.png").write_bytes(b"png")
print("ok")
sys.exit(0)
""",
    )


def adapter(script: Path, artifacts: Path, **kwargs) -> TesterArmyAdapter:
    return TesterArmyAdapter(
        [sys.executable, str(script), str(artifacts)],
        version=kwargs.pop("version", "1.2.3"),
        artifacts_dir=artifacts,
        **kwargs,
    )


def test_pass_with_artifact_conversion(tmp_path):
    script = pass_script(tmp_path)
    artifacts = tmp_path / "evidence"
    result = adapter(script, artifacts).run()
    assert result.exit_code == 0
    assert result.status == "PASS"
    assert result.replay_exit_code is None
    types = {a.name: a.artifact_type for a in result.artifacts}
    assert types["trace.zip"] == "trace"
    assert types["report.json"] == "report"
    assert types["screenshot.png"] == "screenshot"
    assert all(a.size_bytes > 0 and len(a.sha256) == 64 for a in result.artifacts)


def test_fail_exit_code(tmp_path):
    script = make_script(tmp_path, "import sys; sys.exit(1)")
    result = adapter(script, tmp_path / "ev").run()
    assert result.status == "FAIL"


def test_other_exit_code_is_error(tmp_path):
    script = make_script(tmp_path, "import sys; sys.exit(3)")
    result = adapter(script, tmp_path / "ev").run()
    assert result.status == "ERROR"


def test_version_is_injected(tmp_path):
    script = make_script(
        tmp_path,
        "import os; print(os.environ['TESTERARMY_VERSION']); print(os.environ.get('EXTRA',''))",
    )
    result = adapter(script, tmp_path / "ev", env={"EXTRA": "x"}).run()
    assert "1.2.3" in result.stdout
    assert "x" in result.stdout


def test_replay_match(tmp_path):
    script = make_script(tmp_path, "import sys; sys.exit(0)")
    result = adapter(script, tmp_path / "ev").run(replay=True)
    assert result.status == "PASS"
    assert result.replay_exit_code == 0


def test_replay_mismatch_raises(tmp_path):
    script = make_script(
        tmp_path,
        """
import sys, pathlib
counter = pathlib.Path(sys.argv[1]) / "count"
counter.parent.mkdir(parents=True, exist_ok=True)
n = int(counter.read_text()) + 1 if counter.exists() else 1
counter.write_text(str(n))
sys.exit(0 if n == 1 else 1)
""",
    )
    with pytest.raises(E2EReplayMismatch):
        adapter(script, tmp_path / "ev").run(replay=True)


def test_timeout_maps_to_error(tmp_path):
    script = make_script(tmp_path, "import time; time.sleep(5)")
    result = adapter(script, tmp_path / "ev", timeout_s=1).run()
    assert result.exit_code == -9
    assert result.status == "ERROR"
    assert "TIMEOUT" in result.stderr


def test_invalid_arguments():
    with pytest.raises(E2EAdapterError):
        TesterArmyAdapter("not-an-argv", version="1.0")
    with pytest.raises(E2EAdapterError):
        TesterArmyAdapter([sys.executable, "-c", "pass"], version="")
