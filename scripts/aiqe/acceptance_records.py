"""V16-025 独立验收记录（acceptance records）。

设计
----
- ``requirements.yaml`` 只声明需求与证据；**独立验收**写在
  ``docs/aiqe/v1.6/acceptance/records/<REQ-ID>.json``，由非原作者人工签署，
  包含 reviewer / reviewer_role / reviewed_at / artifact。
- 校验时把 records 合并进矩阵条目：只有合法记录才能把
  ``acceptance.status`` 从 NOT_REVIEWED 提升为 REVIEWED/WAIVED。
- 角色矩阵 ``governance/review-roles.yaml`` 强制 reviewer 角色域 ≠ owner 角色域，
  防止“同一账号换角色字符串”冒充独立验收。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs/aiqe/v1.6"
RECORDS_DIR = DOCS / "acceptance/records"
ROLE_MATRIX = DOCS / "governance/review-roles.yaml"

DECISIONS = {"REVIEWED", "WAIVED"}
PENDING_REVIEWERS = {"", "pending", "tbd", "n/a", "none"}
REQUIRED_FIELDS = ("requirement_id", "decision", "reviewer", "reviewed_at")


@dataclass
class AcceptanceReport:
    records: dict[str, dict[str, Any]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def load_role_matrix(path: Path = ROLE_MATRIX) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {"owners": {}, "reviewers": {}}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    roles = data.get("roles") or {}
    return {
        "owners": {str(k): str(v) for k, v in (roles.get("owners") or {}).items()},
        "reviewers": {str(k): str(v) for k, v in (roles.get("reviewers") or {}).items()},
    }


def _resolve_repo_path(raw: str) -> Path | None:
    if not raw:
        return None
    text = str(raw).replace("\\", "/").strip()
    candidate = ROOT / text
    return candidate if candidate.exists() else None


def validate_record(
    record: Any,
    *,
    requirement_id: str,
    owner: str,
    roles: dict[str, dict[str, str]],
) -> list[str]:
    errors: list[str] = []
    if not isinstance(record, dict):
        return [f"{requirement_id}: acceptance record 必须是对象"]
    for key in REQUIRED_FIELDS:
        if not str(record.get(key) or "").strip():
            errors.append(f"{requirement_id}: acceptance record 缺少 {key}")
    if str(record.get("requirement_id") or "").strip() != requirement_id:
        errors.append(f"{requirement_id}: record.requirement_id 不匹配")
    decision = str(record.get("decision") or "").upper()
    if decision not in DECISIONS:
        errors.append(f"{requirement_id}: 非法 decision {decision!r}（只允许 {sorted(DECISIONS)}）")
    if str(record.get("reviewed_at") or "").strip() and not str(record["reviewed_at"])[:4].isdigit():
        errors.append(f"{requirement_id}: reviewed_at 必须是日期")
    reviewer = str(record.get("reviewer") or "").strip()
    reviewer_role = str(record.get("reviewer_role") or "").strip()
    if reviewer.lower() in PENDING_REVIEWERS:
        errors.append(f"{requirement_id}: reviewer 不能是 pending/{reviewer!r}")
    owner_role = roles["owners"].get(owner)
    if owner_role is None:
        errors.append(
            f"{requirement_id}: owner {owner!r} 未在 governance/review-roles.yaml 注册"
        )
    mapped_reviewer_role = roles["reviewers"].get(reviewer)
    if mapped_reviewer_role is None and not reviewer_role:
        errors.append(
            f"{requirement_id}: reviewer {reviewer!r} 未注册角色，且 record 未提供 reviewer_role"
        )
    effective_reviewer_role = mapped_reviewer_role or reviewer_role
    if reviewer_role and mapped_reviewer_role and reviewer_role != mapped_reviewer_role:
        errors.append(
            f"{requirement_id}: reviewer_role {reviewer_role!r} 与角色矩阵 "
            f"{mapped_reviewer_role!r} 不一致"
        )
    if owner_role and effective_reviewer_role and effective_reviewer_role == owner_role:
        errors.append(
            f"{requirement_id}: Reviewer 角色域 {effective_reviewer_role!r} 与 Owner "
            f"角色域相同，不构成独立验收"
        )
    artifact = str(record.get("artifact") or "").strip()
    if decision == "REVIEWED":
        if not artifact:
            errors.append(f"{requirement_id}: REVIEWED 需要 artifact（人工评审记录）")
        elif _resolve_repo_path(artifact) is None:
            errors.append(f"{requirement_id}: acceptance artifact 不存在: {artifact}")
    if decision == "WAIVED":
        for key in ("waiver_reason", "waived_by"):
            if not str(record.get(key) or "").strip():
                errors.append(f"{requirement_id}: WAIVED 需要 {key}")
    return errors


def load_records(
    *,
    records_dir: Path = RECORDS_DIR,
    entries: list[dict[str, Any]] | None = None,
    role_matrix_path: Path = ROLE_MATRIX,
) -> AcceptanceReport:
    report = AcceptanceReport()
    roles = load_role_matrix(role_matrix_path)
    owners = {str(entry.get("id")): str(entry.get("owner") or "") for entry in entries or []}
    if not records_dir.exists():
        return report
    for path in sorted(records_dir.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            report.errors.append(f"{path.name}: 无法解析 JSON: {exc}")
            continue
        requirement_id = str((record or {}).get("requirement_id") or path.stem)
        if entries is not None and requirement_id not in owners:
            report.errors.append(f"{path.name}: 未知 requirement_id {requirement_id!r}")
            continue
        errors = validate_record(
            record,
            requirement_id=requirement_id,
            owner=owners.get(requirement_id, ""),
            roles=roles,
        )
        report.errors.extend(errors)
        if errors:
            continue
        try:
            record_path = path.relative_to(ROOT).as_posix()
        except ValueError:  # pragma: no cover - 测试/临时目录
            record_path = path.as_posix()
        report.records[requirement_id] = {
            "status": str(record.get("decision") or "").upper(),
            "reviewer": str(record.get("reviewer") or "").strip(),
            "reviewer_role": str(
                record.get("reviewer_role") or roles["reviewers"].get(str(record.get("reviewer")))
            ),
            "reviewed_at": str(record.get("reviewed_at") or "").strip(),
            "artifact": str(record.get("artifact") or "").strip(),
            "waiver_reason": str(record.get("waiver_reason") or ""),
            "waived_by": str(record.get("waived_by") or ""),
            "record": record_path,
        }
    return report


def apply_records(
    entries: list[dict[str, Any]], report: AcceptanceReport
) -> list[dict[str, Any]]:
    """把合法 acceptance record 合并进矩阵条目（返回新列表，不改原对象）。"""
    merged: list[dict[str, Any]] = []
    for entry in entries:
        item = dict(entry)
        requirement_id = str(item.get("id"))
        record = report.records.get(requirement_id)
        if record:
            item["reviewer"] = record["reviewer"]
            item["acceptance"] = {
                "status": record["status"],
                "reviewed_at": record["reviewed_at"],
                "artifact": record["artifact"],
                "reviewer_role": record["reviewer_role"],
                "record": record["record"],
            }
            if record["status"] == "WAIVED":
                item["acceptance"]["waiver_reason"] = record["waiver_reason"]
                item["acceptance"]["waived_by"] = record["waived_by"]
        merged.append(item)
    return merged


__all__ = [
    "AcceptanceReport",
    "RECORDS_DIR",
    "ROLE_MATRIX",
    "apply_records",
    "load_records",
    "load_role_matrix",
    "validate_record",
]
