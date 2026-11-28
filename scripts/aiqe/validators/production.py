"""生产发布阶段语义校验（FIX-010 / Gate F）。

Gate F 不再只看 ``status`` 字符串。每个强制阶段必须给出原始部署/观测证据：
目标 SHA、镜像 digest、环境、起止时间、原始 checks、artifact、操作者身份。
WAIVED 只能按发布策略豁免，且永远不计入 PASS。
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from statuses import BLOCKED, FAIL, NOT_PROVEN, NOT_RUN, PASS, WAIVED
from validators.common import is_digest, is_sha, parse_time, resolve_repo_path
from validators.models import GateCheck

MANDATORY_STAGES = (
    "stage1_shadow",
    "stage2_dogfood",
    "stage3_small_traffic",
    "stage4_expand",
    "rollback_drill",
)
OPTIONAL_STAGES = ("stage5_ga",)


def _stage_payload(stages: Any, key: str) -> Any:
    if isinstance(stages, dict):
        return stages.get(key)
    if isinstance(stages, list):
        for item in stages:
            if isinstance(item, dict) and str(item.get("stage_id") or item.get("id")) == key:
                return item
    return None


def validate_production_evidence(
    payload: Any,
    *,
    expected_commit: str = "",
    root: Path | None = None,
    mandatory: tuple[str, ...] = MANDATORY_STAGES,
    allow_waivers: bool = False,
    now: datetime | None = None,
) -> GateCheck:
    check = GateCheck()
    check.status = PASS
    if not isinstance(payload, dict) or not payload:
        return GateCheck.unproven("缺少 production-evidence.json 或格式非法")
    if root is None:
        raise ValueError("validate_production_evidence 需要 root 解析 artifact")
    stages = payload.get("stages")
    if not stages:
        return GateCheck.unproven("production-evidence 没有 stage 记录")
    current = now or datetime.now(UTC)

    for key in mandatory:
        item = _stage_payload(stages, key)
        if not isinstance(item, dict):
            check.add(f"{key}: 缺少阶段记录")
            continue
        status = str(item.get("status") or "").strip().upper()
        if status == PASS:
            target_sha = str(item.get("target_release_sha") or "").strip().lower()
            digest = str(item.get("deployed_image_digest") or "").strip().lower()
            if not is_sha(target_sha):
                check.add(f"{key}: PASS 缺少 target_release_sha")
            elif expected_commit and target_sha != expected_commit.strip().lower():
                check.add(f"{key}: target_release_sha={target_sha[:12]} 与验收 SHA 不一致")
            if not is_digest(digest):
                check.add(f"{key}: PASS 缺少 immutable deployed_image_digest")
            if not str(item.get("environment") or "").strip():
                check.add(f"{key}: PASS 缺少 environment")
            started, finished = item.get("started_at"), item.get("finished_at")
            start_time, end_time = parse_time(started), parse_time(finished)
            if start_time is None or end_time is None or end_time < start_time:
                check.add(f"{key}: PASS 缺少有效 started_at/finished_at")
            checks = item.get("checks")
            if not isinstance(checks, dict) or not checks:
                check.add(f"{key}: PASS 缺少原始 checks/观测值")
            else:
                for check_name, value in checks.items():
                    if value in (None, "", [], {}):
                        check.add(f"{key}: check {check_name} 无原始观测值")
            artifacts = item.get("artifact_refs") or item.get("artifacts") or []
            if not isinstance(artifacts, list) or not artifacts:
                check.add(f"{key}: PASS 缺少 artifact_refs")
            else:
                for raw in artifacts:
                    path = resolve_repo_path(root, raw)
                    if path is None or not path.exists():
                        check.add(f"{key}: artifact 不存在或越界: {raw!r}")
            if not str(item.get("operator_identity") or "").strip():
                check.add(f"{key}: PASS 缺少 operator_identity")
            if key == "rollback_drill":
                drill = item.get("drill") if isinstance(item.get("drill"), dict) else item
                if not str(drill.get("rollback_target_sha") or "").strip():
                    check.add("rollback_drill: 缺少 rollback_target_sha")
                if not isinstance(drill.get("verification"), dict) or not drill.get("verification"):
                    check.add("rollback_drill: 缺少回滚后验证结果（只有命令不算演练）")
                try:
                    recovery = int(drill.get("recovery_seconds"))
                except (TypeError, ValueError):
                    recovery = -1
                if recovery < 0:
                    check.add("rollback_drill: 缺少 recovery_seconds")
        elif status == WAIVED:
            if not allow_waivers:
                check.add(f"{key}: WAIVED 但发布策略不允许豁免")
            for field in (
                "approved_by",
                "approved_at",
                "reason",
                "risk",
                "compensating_controls",
                "expires_at",
            ):
                if not str(item.get(field) or "").strip():
                    check.add(f"{key}: WAIVED 缺少 {field}")
            expires = parse_time(item.get("expires_at"))
            if expires is not None and expires < current:
                check.add(f"{key}: WAIVED 已过期（{item.get('expires_at')}）")
            check.add(f"{key}: WAIVED 不计入 Gate F PASS", demote_to=NOT_PROVEN)
        elif status == FAIL:
            check.demote(FAIL)
            check.add(f"{key}: FAIL", demote_to=FAIL)
        elif status in {NOT_RUN, BLOCKED}:
            check.add(f"{key}: {status}，Gate F 不得 PASS")
        else:
            check.add(f"{key}: 状态 {status or '<empty>'} 不是可接受的生产阶段状态")

    for key in OPTIONAL_STAGES:
        item = _stage_payload(stages, key)
        if item is None:
            continue
        status = str(item.get("status") or "").strip().upper()
        if status in {FAIL, BLOCKED, NOT_RUN}:
            check.demote(FAIL if status == FAIL else NOT_PROVEN)
            check.add(f"{key}: {status}")

    independent = payload.get("independent_verification") or {}
    if not isinstance(independent, dict) or not str(independent.get("reviewed_by") or "").strip():
        check.add("缺少独立验收签署（independent_verification.reviewed_by）")
    if isinstance(independent, dict):
        for field in ("review_id", "reviewed_commit_sha"):
            if not str(independent.get(field) or "").strip():
                check.add(f"独立验收缺少 {field}，不能证明签署的是当前 SHA")

    if check.status == PASS:
        check.note("生产阶段逐项通过：SHA/digest/原始观测/artifact/操作者/回滚演练齐全")
        check.evidence_refs.append("docs/aiqe/v1.6/governance/production-evidence.json")
    return check


__all__ = ["MANDATORY_STAGES", "OPTIONAL_STAGES", "validate_production_evidence"]
