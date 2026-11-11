"""M3 / TA-018：Keploy Record/Replay Adapter PoC（13 号 §19 TA-018）。

- record：调用 Keploy 录制，要求至少捕获 1 条上下游依赖；
- replay：默认连跑两次，passed/failed 不一致 → `KeployReplayUnstable`；
- 脱敏：request/response 中 authorization/cookie/token 等字段一律 `***`；
- eBPF 权限审计：Linux + (root 或 CAP_BPF) 才允许真实 record/replay；
- PoC 通过 argv 调用（shell=False），测试用脚本模拟 Keploy 报告。
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "proxy-authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "api-key",
        "password",
        "passwd",
        "token",
        "secret",
        "access_token",
        "refresh_token",
    }
)
REDACTED = "***"
CAP_BPF_BIT = 39
CAP_SYS_ADMIN_BIT = 21


class KeployError(RuntimeError):
    pass


class KeployPermissionError(KeployError):
    pass


class KeployDependencyMissing(KeployError):
    pass


class KeployReplayUnstable(KeployError):
    pass


@dataclass(frozen=True)
class EbpfAudit:
    system: str
    euid: int
    is_root: bool
    cap_bpf: bool
    cap_sys_admin: bool
    ready: bool
    notes: str = ""


def _read_capeff() -> int:
    try:
        for line in Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
            if line.startswith("CapEff:"):
                return int(line.split(":", 1)[1].strip(), 16)
    except (OSError, ValueError):
        return 0
    return 0


def audit_ebpf() -> EbpfAudit:
    system = platform.system()
    euid = os.geteuid() if hasattr(os, "geteuid") else -1
    capeff = _read_capeff()
    cap_bpf = bool(capeff & (1 << CAP_BPF_BIT))
    cap_sys_admin = bool(capeff & (1 << CAP_SYS_ADMIN_BIT))
    is_root = euid == 0
    ready = system == "Linux" and (is_root or cap_bpf)
    notes = "" if ready else "需要 Linux + root 或 CAP_BPF 才能运行 Keploy eBPF"
    return EbpfAudit(
        system=system,
        euid=euid,
        is_root=is_root,
        cap_bpf=cap_bpf,
        cap_sys_admin=cap_sys_admin,
        ready=ready,
        notes=notes,
    )


def assert_ebpf_ready(audit: EbpfAudit) -> None:
    if not audit.ready:
        raise KeployPermissionError(audit.notes or "eBPF 权限不足")


def redact_payload(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if str(key).lower() in SENSITIVE_KEYS:
                out[key] = REDACTED
            else:
                out[key] = redact_payload(item)
        return out
    if isinstance(value, list):
        return [redact_payload(item) for item in value]
    return value


@dataclass
class KeployResult:
    action: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    report: dict[str, Any] = field(default_factory=dict)
    dependencies: list[Any] = field(default_factory=list)
    tests: dict[str, Any] = field(default_factory=dict)


class KeployDriver:
    def __init__(
        self,
        keploy_bin: str = "keploy",
        *,
        cwd: str | Path | None = None,
        report_path: str = "keploy-report.json",
        timeout_s: float = 300,
        env: dict[str, str] | None = None,
        require_ebpf: bool = False,
    ) -> None:
        self.keploy_bin = keploy_bin
        self.cwd = Path(cwd) if cwd else None
        self.report_path = report_path
        self.timeout_s = max(1.0, float(timeout_s))
        self.env = dict(env or {})
        self.require_ebpf = require_ebpf

    def _guard(self) -> None:
        if self.require_ebpf:
            assert_ebpf_ready(audit_ebpf())

    def _run(self, argv: list[str], action: str) -> KeployResult:
        started = time.monotonic()
        proc = subprocess.run(
            argv,
            cwd=str(self.cwd) if self.cwd else None,
            env={**os.environ, **self.env},
            capture_output=True,
            text=True,
            timeout=self.timeout_s,
            shell=False,
        )
        duration = int((time.monotonic() - started) * 1000)
        report = self._load_report()
        return KeployResult(
            action=action,
            exit_code=proc.returncode,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            duration_ms=duration,
            report=redact_payload(report),
        )

    def _load_report(self) -> dict[str, Any]:
        base = self.cwd or Path.cwd()
        path = Path(self.report_path)
        if not path.is_absolute():
            path = base / path
        if not path.is_file():
            raise KeployError(f"未找到 Keploy 报告: {path}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise KeployError(f"Keploy 报告不是合法 JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise KeployError("Keploy 报告必须是对象")
        return data

    def record(self, command: list[str], *, test_set: str = "default") -> KeployResult:
        self._guard()
        if not command:
            raise KeployError("record 必须提供被测命令")
        result = self._run(
            [self.keploy_bin, "record", "--test-set", test_set, *command], "record"
        )
        dependencies = result.report.get("dependencies") or []
        if not isinstance(dependencies, list) or len(dependencies) < 1:
            raise KeployDependencyMissing("录制未捕获到上下游依赖（至少需要 1 条）")
        result.dependencies = [redact_payload(item) for item in dependencies]
        return result

    def replay(self, *, test_set: str = "default", times: int = 2) -> KeployResult:
        self._guard()
        attempts: list[KeployResult] = []
        for _ in range(max(1, int(times))):
            result = self._run(
                [self.keploy_bin, "replay", "--test-set", test_set], "replay"
            )
            attempts.append(result)
        first = attempts[0]
        first_tests = first.report.get("tests") or {}
        for other in attempts[1:]:
            other_tests = other.report.get("tests") or {}
            if (
                other_tests.get("passed") != first_tests.get("passed")
                or other_tests.get("failed") != first_tests.get("failed")
            ):
                raise KeployReplayUnstable(
                    f"回放不稳定: {first_tests} vs {other_tests}"
                )
        first.tests = redact_payload(first_tests)
        return first
