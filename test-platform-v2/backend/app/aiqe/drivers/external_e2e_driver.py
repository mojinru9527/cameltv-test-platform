"""M3 / TA-017：TesterArmy e2e Adapter PoC（13 号 §19 TA-017）。

- 固定版本执行：必须显式 pin `version`，注入 `TESTERARMY_VERSION`；
- 二次重放：`run(replay=True)` 连跑两次，退出码不一致 → `E2EReplayMismatch`；
- 证据转换：artifacts 目录按后缀映射为 CamelTv artifact_type + sha256/size；
- 退出码 → assertion：0=PASS、1=FAIL、其它/超时=ERROR；
- 仅接受 argv 数组（禁止 shell 字符串），带超时。
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

EXIT_STATUS = {0: "PASS", 1: "FAIL"}
ARTIFACT_TYPES = {
    ".zip": "trace",
    ".png": "screenshot",
    ".jpg": "screenshot",
    ".jpeg": "screenshot",
    ".webm": "video",
    ".mp4": "video",
    ".json": "report",
    ".har": "har",
    ".html": "dom",
    ".log": "log",
    ".txt": "log",
}


class E2EAdapterError(RuntimeError):
    pass


class E2EReplayMismatch(E2EAdapterError):
    pass


@dataclass(frozen=True)
class E2EArtifact:
    name: str
    artifact_type: str
    path: str
    size_bytes: int
    sha256: str


@dataclass
class E2EResult:
    exit_code: int
    status: str
    stdout: str
    stderr: str
    duration_ms: int
    artifacts: list[E2EArtifact] = field(default_factory=list)
    replay_exit_code: int | None = None


class TesterArmyAdapter:
    def __init__(
        self,
        command: list[str],
        *,
        version: str,
        cwd: str | Path | None = None,
        env: dict[str, str] | None = None,
        timeout_s: float = 300,
        artifacts_dir: str | Path | None = None,
    ) -> None:
        if not isinstance(command, list) or not command:
            raise E2EAdapterError("command 必须是非空 argv 数组（禁止 shell 字符串）")
        if not isinstance(version, str) or not version.strip():
            raise E2EAdapterError("必须固定 TesterArmy 版本（version）")
        self.command = [str(part) for part in command]
        self.version = version.strip()
        self.cwd = str(cwd) if cwd else None
        self.env = dict(env or {})
        self.timeout_s = max(1.0, float(timeout_s))
        self.artifacts_dir = Path(artifacts_dir) if artifacts_dir else None

    def _execute(self) -> tuple[int, str, str, int]:
        child_env = {**os.environ, **self.env, "TESTERARMY_VERSION": self.version}
        started = time.monotonic()
        try:
            proc = subprocess.run(
                self.command,
                cwd=self.cwd,
                env=child_env,
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
                shell=False,
            )
            return (
                proc.returncode,
                proc.stdout or "",
                proc.stderr or "",
                int((time.monotonic() - started) * 1000),
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            return -9, stdout, (stderr + "\nTIMEOUT").strip(), int(
                (time.monotonic() - started) * 1000
            )

    @staticmethod
    def _status(exit_code: int) -> str:
        return EXIT_STATUS.get(exit_code, "ERROR")

    def _collect(self) -> list[E2EArtifact]:
        if self.artifacts_dir is None or not self.artifacts_dir.is_dir():
            return []
        artifacts: list[E2EArtifact] = []
        for path in sorted(self.artifacts_dir.rglob("*")):
            if not path.is_file():
                continue
            data = path.read_bytes()
            artifacts.append(
                E2EArtifact(
                    name=path.name,
                    artifact_type=ARTIFACT_TYPES.get(path.suffix.lower(), "other"),
                    path=str(path),
                    size_bytes=len(data),
                    sha256=hashlib.sha256(data).hexdigest(),
                )
            )
        return artifacts

    def run(self, *, replay: bool = False) -> E2EResult:
        exit_code, stdout, stderr, duration_ms = self._execute()
        result = E2EResult(
            exit_code=exit_code,
            status=self._status(exit_code),
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
        )
        if replay:
            replay_code, _replay_out, _replay_err, _replay_duration = self._execute()
            result.replay_exit_code = replay_code
            if replay_code != exit_code:
                raise E2EReplayMismatch(
                    f"二次重放退出码不一致: first={exit_code}, replay={replay_code}"
                )
        result.artifacts = self._collect()
        return result


def run_testerarmy(command: list[str], *, version: str, **kwargs: Any) -> E2EResult:
    """便捷入口（供调度器/worker 调用）。"""
    return TesterArmyAdapter(command, version=version, **kwargs).run()
