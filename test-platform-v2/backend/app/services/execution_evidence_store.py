"""执行证据落盘（Batch 258 / B1 最小口径）。

范围声明（与 B4-1 的边界，避免两边各做一半）：
  - 本模块做：按 (job, attempt) 落盘 + 每个文件 sha256 manifest + 路径收敛下载；
  - B4-1 再做：证据包定型、完整性门禁、篡改显红、放行结论绑定 bundle 哈希。

路径收敛写法与 `app/api/v1/lanhu_evidence_assets.py` 的 `is_relative_to` 保持一致
（cameltv-bug-guard：文件路径拼接必须收敛，禁止只做字符串前缀判断）。
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import settings

MANIFEST_NAME = "manifest.json"
MAX_EVIDENCE_FILE_BYTES = 20 * 1024 * 1024
DEFAULT_ROOT_RELATIVE = "storage/execution-evidence"
_SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")


class EvidenceStoreError(ValueError):
    """证据文件名非法、超限或路径越权。"""


def evidence_root() -> Path:
    configured = (settings.execution_evidence_storage_dir or "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    # app/services/execution_evidence_store.py -> backend/
    backend_root = Path(__file__).resolve().parents[2]
    return (backend_root / DEFAULT_ROOT_RELATIVE).resolve()


def safe_file_name(name: str) -> str:
    """校验证据文件名：**拒绝**任何路径成分，而不是悄悄剥掉它们。

    `Path(name).name` 看似安全，但在 POSIX 上不把 `\\` 当分隔符，于是
    `..\\evil.txt` 会被原样接受；而 Windows 上它又是目录穿越。两种平台行为不一致，
    且"剥掉目录"会让平台清单与节点本地清单对不上（上传对账失败却看不出原因）。
    因此这里显式拒绝：含 `/`、`\\`、`..` 或非白名单字符一律报错。
    """
    candidate = (name or "").strip()
    if not candidate or candidate in {".", ".."}:
        raise EvidenceStoreError(f"非法证据文件名: {name!r}")
    if "/" in candidate or "\\" in candidate or Path(candidate).name != candidate:
        raise EvidenceStoreError(f"证据文件名不得包含路径分隔符: {name!r}")
    if not _SAFE_NAME.match(candidate):
        raise EvidenceStoreError(f"非法证据文件名: {name!r}")
    return candidate


def bundle_dir(job_id: int, attempt: int) -> Path:
    return evidence_root() / f"job-{int(job_id)}" / f"attempt-{int(attempt)}"


def _contained(path: Path, base: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(base.resolve()):
        raise EvidenceStoreError("证据路径越权")
    return resolved


def save_bundle(*, job_id: int, attempt: int, files: list[tuple[str, bytes]]) -> dict:
    """写入一次尝试的全部证据文件 + manifest（每文件 sha256）。"""
    directory = bundle_dir(job_id, attempt)
    directory.mkdir(parents=True, exist_ok=True)
    entries: list[dict] = []
    seen: set[str] = set()
    for raw_name, data in files:
        name = safe_file_name(raw_name)
        if name == MANIFEST_NAME:
            raise EvidenceStoreError("证据文件名不得占用 manifest.json")
        if name in seen:
            raise EvidenceStoreError(f"同一次尝试内证据文件名重复: {name}")
        if len(data) > MAX_EVIDENCE_FILE_BYTES:
            raise EvidenceStoreError(f"证据文件超过上限（{MAX_EVIDENCE_FILE_BYTES} 字节）: {name}")
        seen.add(name)
        target = _contained(directory / name, directory)
        target.write_bytes(data)
        entries.append(
            {"name": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        )

    manifest = {
        "job_id": int(job_id),
        "attempt": int(attempt),
        "created_at": datetime.now(UTC).isoformat(),
        "file_count": len(entries),
        "total_bytes": sum(entry["size"] for entry in entries),
        "files": sorted(entries, key=lambda entry: entry["name"]),
        "schema_version": 1,
        "completeness": "minimal",  # B4-1 升级为对账执行结果后的完整性判定
    }
    (directory / MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def load_manifest(job_id: int, attempt: int) -> dict | None:
    path = bundle_dir(job_id, attempt) / MANIFEST_NAME
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def list_bundles(job_id: int) -> list[dict]:
    root = evidence_root() / f"job-{int(job_id)}"
    if not root.exists():
        return []
    bundles: list[dict] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir() or not child.name.startswith("attempt-"):
            continue
        try:
            attempt = int(child.name.split("-", 1)[1])
        except (IndexError, ValueError):
            continue
        manifest = load_manifest(job_id, attempt)
        if manifest is not None:
            bundles.append(manifest)
    return bundles


def resolve_file(job_id: int, attempt: int, name: str) -> Path:
    directory = bundle_dir(job_id, attempt)
    target = _contained(directory / safe_file_name(name), directory)
    if not target.exists() or not target.is_file():
        raise EvidenceStoreError("证据文件不存在")
    return target
