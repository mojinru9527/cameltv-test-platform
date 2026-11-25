"""P2-3 部分覆盖：仓库与近期 git 历史中的高置信度凭据扫描（只读）。

只做**发现与分级**，不做自动修改；真实轮换仍需凭据系统/历史日志访问。
证据写入 `docs/aiqe/v1.6/evidence/credential-scan.json`，命中值全部脱敏。

范围
----
- 高置信度模式（私钥/AWS Key/LLM sk-）扫描全部 tracked 文件；
- 带密码 DSN / 赋值型口令只扫描配置类文件（.env、.yml/.yaml、deploy 下 .json），
  排除 docs/work-logs/tests/examples/fixtures 与 *.example*，避免把文档示例当泄漏。

分级
----
- ``placeholder``：占位符/示例，不构成泄漏；
- ``weak-default``：弱默认值或本地/服务别名 DSN，需确认是否仍生效；
- ``potential-secret``：形似真实凭据，必须人工复核并轮换。

用法
----
    python scripts/aiqe/scan_credentials.py
    python scripts/aiqe/scan_credentials.py --history-limit 300
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "docs/aiqe/v1.6/evidence/credential-scan.json"
MAX_FILE_BYTES = 2 * 1024 * 1024
PLACEHOLDERS = ("***", "${", "{{", "<", "your_", "your-", "example", "changeme", "redacted", "xxx")
WEAK_DEFAULTS = {"admin123", "password", "passwd", "123456", "admin", "root", "postgres", "test"}
WEAK_HOSTS = {"localhost", "127.0.0.1", "postgres", "mysql", "db", "database", "redis", "host"}
SKIP_PARTS = (
    "docs/",
    "work-logs/",
    "tests/",
    "__tests__/",
    ".test.",
    ".spec.",
    "examples/",
    "fixtures/",
    "node_modules/",
    ".example",
    "test-secret-scan",
    "scan-common-bugs",
    "playwright-walkthrough",
)
HIGH_CONFIDENCE = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA |PGP )?PRIVATE KEY-----")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("llm_api_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
)
DSN = re.compile(
    r"\b(?:postgres(?:ql)?|mysql|redis|mongodb)://[^:\s/@]+:[^@\s]{3,}@[^/\s\"'<>]+"
)
ASSIGNED = re.compile(
    r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key)\b\s*[:=]\s*[\"']([A-Za-z0-9_./+=\-]{8,128})[\"']"
)


def is_config_file(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    if name.startswith(".env"):
        return True
    if name.endswith((".yml", ".yaml")):
        return True
    return path.startswith("deploy/") and name.endswith(".json")


def skip_path(path: str) -> bool:
    return any(part in path for part in SKIP_PARTS)


def mask_value(value: str) -> str:
    if len(value) <= 4:
        return "***"
    return f"{value[:2]}***{value[-2:]}(len={len(value)})"


def _dsn_parts(value: str) -> tuple[str, str, str]:
    try:
        parts = urlsplit(value)
    except ValueError:
        return "", "", ""
    return unquote(parts.username or ""), unquote(parts.password or ""), (parts.hostname or "").lower()


def _is_doc_like(line: str) -> bool:
    return any(
        marker in line
        for marker in (
            "re.compile",
            "pattern",
            "redact",
            "canary",
            "示例",
            "模板",
            "[A-Z0-9",
            "…",
            "sk-[A-Za-z0-9]",
            "PRIVATE KEY-\\n",
        )
    )


def classify(kind: str, value: str, path: str, line: str) -> str:
    lowered = value.lower()
    if any(token in lowered for token in PLACEHOLDERS):
        return "placeholder"
    if _is_doc_like(line):
        return "placeholder"
    if kind == "dsn_with_password":
        user, password, host = _dsn_parts(value)
        if host in WEAK_HOSTS or not user or not password:
            return "weak-default"
        if password.lower() in WEAK_DEFAULTS:
            return "weak-default"
        return "potential-secret"
    if kind == "assigned_secret":
        if lowered in WEAK_DEFAULTS:
            return "weak-default"
        if path.endswith(".py"):
            if value[:1].isupper() and value.isalnum():
                return "placeholder"
        return "potential-secret"
    return "potential-secret"


def scan_text(text: str, *, path: str = "", config_only: bool = False) -> list[dict]:
    findings: list[dict] = []
    config = is_config_file(path)
    for lineno, line in enumerate(text.splitlines(), 1):
        if skip_path(path):
            continue
        if not config_only or config:
            for kind, pattern in HIGH_CONFIDENCE:
                for match in pattern.finditer(line):
                    findings.append(
                        _finding(path, lineno, kind, match.group(0), match.group(0), line)
                    )
            for match in DSN.finditer(line):
                findings.append(
                    _finding(path, lineno, "dsn_with_password", match.group(0), match.group(0), line)
                )
            for match in ASSIGNED.finditer(line):
                findings.append(
                    _finding(path, lineno, "assigned_secret", match.group(0), match.group(2), line)
                )
    return findings


def _finding(path: str, line: int, kind: str, raw: str, value: str, source: str) -> dict:
    return {
        "file": path,
        "line": line,
        "kind": kind,
        "masked": mask_value(raw),
        "classification": classify(kind, value, path, source),
    }


def _tracked_files() -> list[Path]:
    result = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True)
    if result.returncode != 0:
        return []
    names = [name for name in result.stdout.decode("utf-8", errors="replace").split("\0") if name]
    return [ROOT / name for name in names if (ROOT / name).is_file()]


def scan_worktree() -> tuple[list[dict], int]:
    findings: list[dict] = []
    scanned = 0
    for path in _tracked_files():
        rel = path.relative_to(ROOT).as_posix()
        if skip_path(rel):
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
            raw = path.read_bytes()
            if b"\x00" in raw[:4096]:
                continue
            text = raw.decode("utf-8", errors="replace")
        except OSError:
            continue
        scanned += 1
        findings.extend(scan_text(text, path=rel))
    return findings, scanned


def scan_history(limit: int) -> list[dict]:
    if limit <= 0:
        return []
    result = subprocess.run(
        ["git", "log", "-p", "--all", "-n", str(limit), "--format=commit %H", "--unified=0"],
        cwd=ROOT,
        capture_output=True,
    )
    if result.returncode != 0:
        return []
    findings: list[dict] = []
    commit = ""
    current_path = ""
    for line in result.stdout.decode("utf-8", errors="replace").splitlines():
        if line.startswith("commit "):
            commit = line.split(" ", 1)[1].strip()
            continue
        if line.startswith("+++ "):
            current_path = line[4:].strip()
            if current_path.startswith("b/"):
                current_path = current_path[2:]
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        body = line[1:]
        if _is_doc_like(body) or (current_path and skip_path(current_path)):
            continue
        for kind, pattern in HIGH_CONFIDENCE:
            for match in pattern.finditer(body):
                item = _finding("<history>", 0, kind, match.group(0), match.group(0), body)
                item["commit"] = commit
                findings.append(item)
    return [item for item in findings if item["classification"] == "potential-secret"]


def summarize(findings: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for item in findings:
        counts[item["classification"]] = counts.get(item["classification"], 0) + 1
    return {
        "placeholder": counts.get("placeholder", 0),
        "weak_default": counts.get("weak-default", 0),
        "potential_secret": counts.get("potential-secret", 0),
    }


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):  # pragma: no cover
            pass
    parser = argparse.ArgumentParser(description="仓库/历史高置信度凭据扫描")
    parser.add_argument("--history-limit", type=int, default=200)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    worktree, scanned = scan_worktree()
    history = scan_history(args.history_limit)
    summary = summarize(worktree)
    history_summary = summarize(history)
    status = "REVIEW" if summary["potential_secret"] or history_summary["potential_secret"] else "CLEAN"
    report = {
        "schema_version": "1.0",
        "artifact_kind": "credential-scan",
        "generated_at": datetime.now(UTC).isoformat(),
        "scope": {
            "tracked_files_scanned": scanned,
            "history_commits_limited": args.history_limit,
            "config_only_patterns": [DSN.pattern, ASSIGNED.pattern],
        },
        "status": status,
        "summary": summary,
        "history_summary": history_summary,
        "findings": [item for item in worktree if item["classification"] != "placeholder"][:200],
        "history_findings": history[:200],
        "note": (
            "只读扫描；命中值已脱敏。potential-secret 需人工复核并在凭据系统轮换；"
            "本文件不替代生产轮换证据。"
        ),
    }
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(
        json.dumps(
            {"status": status, "summary": summary, "history": history_summary}, ensure_ascii=False
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
