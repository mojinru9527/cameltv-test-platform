"""V16-014：A5 Change Impact 证据化分析。

- 输入必须是完整 base/head SHA + 变更文件 + unified diff；
- 影响关系必须带证据来源：route/OpenAPI operation、AST symbol、migration table/column、
  dependency graph、UI route；不允许仅凭文件名关键词下结论；
- 无法分析的文件类型 / 无 baseline / 生成代码 → status=UNKNOWN 且要求更广回归；
- 输出记录算法版本、规则版本、diff hash 与结果 checksum。
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ROUTE_RE = re.compile(r"@(?:router|app)\.(get|post|put|patch|delete)\(\s*[\"']([^\"']+)")
MIGRATION_RE = re.compile(r"op\.(create_table|add_column|drop_column|create_index)\(\s*[\"']([^\"']+)")
CLASS_RE = re.compile(r"^\+?\s*class\s+([A-Za-z_]\w*)")
DEF_RE = re.compile(r"^\+?\s*(?:async\s+)?def\s+([A-Za-z_]\w*)")
PERMISSION_RE = re.compile(r"(require_permission|permission|rbac|auth|login|token|session)", re.I)
UI_ROUTE_RE = re.compile(r"[\"'](/[a-zA-Z0-9_\-/{}.]+)[\"']")
AREA_SUITES: dict[str, tuple[str, ...]] = {
    "auth": ("auth-suite", "smoke-suite"),
    "payment": ("payment-suite", "smoke-suite"),
    "live": ("live-suite",),
    "admin": ("admin-suite",),
    "api": ("api-suite",),
    "ui": ("ui-suite",),
    "data": ("data-suite",),
}
ALGORITHM_VERSION = "V16-014.1"
RULE_VERSION = "V16-014.1"
SUPPORTED_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".sql"}


class ImpactError(ValueError):
    pass


def _hash(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _diff_hash(base_sha: str, head_sha: str, files: list[str], diff_text: str) -> str:
    return _hash(
        {
            "base": base_sha,
            "head": head_sha,
            "files": sorted(files),
            "diff": diff_text or "",
        }
    )


def _changed_lines(diff_text: str, file: str) -> list[str]:
    """从 unified diff 提取目标文件的 + 行（含路径头判断）。"""
    lines: list[str] = []
    current = ""
    capture = False
    for line in (diff_text or "").splitlines():
        if line.startswith("+++ b/"):
            current = line[6:].strip()
            capture = current == file
            continue
        if line.startswith("diff --git "):
            capture = False
            continue
        if capture and line.startswith("+") and not line.startswith("+++"):
            lines.append(line[1:])
    return lines


def _evidence_for_file(file: str, added: list[str]) -> list[dict[str, str]]:
    evidence: list[dict[str, str]] = []
    suffix = Path(file).suffix.lower()
    for line in added:
        for match in ROUTE_RE.finditer(line):
            evidence.append(
                {"kind": "route", "file": file, "detail": match.group(2), "method": match.group(1).upper()}
            )
        for match in MIGRATION_RE.finditer(line):
            evidence.append(
                {"kind": "migration", "file": file, "detail": match.group(2), "operation": match.group(1)}
            )
        class_match = CLASS_RE.match(line)
        if class_match:
            evidence.append({"kind": "symbol", "file": file, "detail": class_match.group(1)})
        def_match = DEF_RE.match(line)
        if def_match:
            evidence.append({"kind": "symbol", "file": file, "detail": def_match.group(1)})
        if "require_permission(" in line or "Depends(require_permission" in line:
            evidence.append({"kind": "permission", "file": file, "detail": line.strip()[:120]})
        if suffix in {".tsx", ".jsx", ".ts", ".js"}:
            for match in UI_ROUTE_RE.finditer(line):
                evidence.append({"kind": "ui_route", "file": file, "detail": match.group(1)})
    if not evidence:
        evidence.append({"kind": "file", "file": file, "detail": "unsupported-or-no-symbol"})
    return evidence


def _transitive_imports(repo_root: Path | None, changed: Iterable[str]) -> list[dict[str, str]]:
    if repo_root is None or not repo_root.exists():
        return []
    modules = {
        Path(path).with_suffix("").as_posix().replace("/", ".")
        for path in changed
        if path.endswith(".py")
    }
    if not modules:
        return []
    evidence: list[dict[str, str]] = []
    for py_file in repo_root.rglob("*.py"):
        try:
            text = py_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for module in modules:
            if f"from {module} import" in text or f"import {module}" in text:
                evidence.append(
                    {
                        "kind": "dependency",
                        "file": py_file.relative_to(repo_root).as_posix(),
                        "detail": module,
                    }
                )
                break
    return evidence


def analyze_change_impact(
    *,
    base_sha: str,
    head_sha: str,
    changed_files: list[str],
    diff_text: str = "",
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    base = str(base_sha or "").strip().lower()
    head = str(head_sha or "").strip().lower()
    if not SHA_RE.match(base) or not SHA_RE.match(head):
        raise ImpactError("base/head 必须是完整 40 位 SHA")
    if base == head:
        raise ImpactError("base 与 head 不能相同")
    files = [str(item).replace("\\", "/").strip() for item in changed_files or []]
    files = [item for item in files if item]
    if not files:
        raise ImpactError("changed_files 不能为空")
    if any(Path(item).name.startswith("generated_") or item.endswith(".pb.go") for item in files):
        unknown_reason = "GENERATED_CODE"
    else:
        unknown_reason = ""

    evidence: list[dict[str, str]] = []
    for file in files:
        added = _changed_lines(diff_text, file)
        evidence.extend(_evidence_for_file(file, added))
    evidence.extend(_transitive_imports(Path(repo_root) if repo_root else None, files))

    classifications: dict[str, list[str]] = {
        "DIRECT": [],
        "TRANSITIVE": [],
        "CONTRACT": [],
        "DATA": [],
        "UI": [],
        "RISK": [],
    }
    for item in evidence:
        kind = item["kind"]
        if kind == "dependency":
            classifications["TRANSITIVE"].append(item["file"])
        elif kind == "migration":
            classifications["DATA"].append(f"{item['file']}:{item['detail']}")
        elif kind in {"route", "symbol"}:
            classifications["CONTRACT"].append(f"{item['file']}:{item['detail']}")
        elif kind == "ui_route":
            classifications["UI"].append(f"{item['file']}:{item['detail']}")
        elif kind == "permission":
            classifications["RISK"].append(f"{item['file']}:permission")
        if PERMISSION_RE.search(f"{item['file']} {item.get('detail', '')}"):
            classifications["RISK"].append(f"{item['file']}:{item.get('detail', '')}")
    classifications["DIRECT"] = sorted(set(files))
    for key in classifications:
        classifications[key] = sorted(set(classifications[key]))

    unsupported = [file for file in files if Path(file).suffix.lower() not in SUPPORTED_SUFFIXES]
    weak_evidence = [
        item for item in evidence if item["kind"] == "file"
    ]
    status = "OK"
    reason = ""
    if unknown_reason:
        status, reason = "UNKNOWN", unknown_reason
    elif unsupported:
        status, reason = "UNKNOWN", f"UNSUPPORTED_FILE_TYPES:{sorted(set(unsupported))}"
    elif not diff_text and changed_files:
        status, reason = "UNKNOWN", "NO_DIFF_BASELINE"
    elif weak_evidence and not any(
        item["kind"] in {"route", "symbol", "migration", "ui_route"} for item in evidence
    ):
        status, reason = "UNKNOWN", "NO_STRUCTURAL_EVIDENCE"

    areas: set[str] = set()
    if classifications["RISK"]:
        areas.add("auth")
    if classifications["CONTRACT"]:
        areas.add("api")
    if classifications["DATA"]:
        areas.add("data")
    if classifications["UI"]:
        areas.add("ui")
    if not areas:
        areas.add("unknown")
    suites: set[str] = set()
    for area in areas:
        suites.update(AREA_SUITES.get(area, ("smoke-suite",)))
    if status == "UNKNOWN":
        # 无法分析 → 更广回归，而不是“无影响”。
        suites.update({"smoke-suite", "auth-suite", "api-suite", "ui-suite", "data-suite"})

    payload = {
        "algorithm_version": ALGORITHM_VERSION,
        "rule_version": RULE_VERSION,
        "base_sha": base,
        "head_sha": head,
        "diff_hash": _diff_hash(base, head, files, diff_text),
        "changed_files": sorted(set(files)),
        "evidence": evidence,
        "classifications": classifications,
        "impacted_areas": sorted(areas),
        "candidate_suites": sorted(suites),
        "forced_suites": sorted(
            {"auth-suite", "smoke-suite"} if "auth" in areas else suites
        ),
        "status": status,
        "reason": reason,
        "broad_regression_required": status == "UNKNOWN",
        "impacted_node_keys": [],
    }
    payload["checksum"] = _hash(payload)
    return payload


__all__ = [
    "ALGORITHM_VERSION",
    "RULE_VERSION",
    "ImpactError",
    "analyze_change_impact",
]
