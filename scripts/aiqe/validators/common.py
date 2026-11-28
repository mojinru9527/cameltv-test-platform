"""validators 共享工具：时间、SHA、hash、路径安全解析。"""
from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def is_sha(value: object) -> bool:
    return bool(SHA_RE.match(str(value or "").strip().lower()))


def is_digest(value: object) -> bool:
    return bool(DIGEST_RE.match(str(value or "").strip().lower()))


def is_sha256(value: object) -> bool:
    return bool(SHA256_RE.match(str(value or "").strip().lower()))


def parse_time(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def duration_ms(started: object, finished: object) -> int | None:
    start = parse_time(started)
    end = parse_time(finished)
    if start is None or end is None or end < start:
        return None
    return int((end - start).total_seconds() * 1000)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_repo_path(root: Path, raw: object) -> Path | None:
    """只允许仓库内相对路径；拒绝绝对路径、``..`` 逃逸。"""
    text = str(raw or "").replace("\\", "/").strip()
    if not text:
        return None
    candidate_path = Path(text)
    if candidate_path.is_absolute():
        return None
    root_resolved = root.resolve()
    candidate = (root_resolved / text).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError:
        return None
    return candidate


__all__ = [
    "DIGEST_RE",
    "SHA256_RE",
    "SHA_RE",
    "duration_ms",
    "is_digest",
    "is_sha",
    "is_sha256",
    "parse_time",
    "resolve_repo_path",
    "sha256_file",
]
