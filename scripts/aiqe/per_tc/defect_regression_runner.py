"""TC-AIQE-008 正式 Defect 一键回归 Runner（V1.6.2 FIX-008）。

正式链路
--------
``Defect Record -> Fix Commit SHA -> Mandatory Scope Snapshot -> Defect Regression API
-> Regression Run -> ExecutionJob / Worker / Driver -> Mandatory Case Results
-> Assertion / Artifact -> Comparison Snapshot -> Final Defect State``

诚实边界
--------
- 必须显式提供 ``--api-base`` / ``--defect-id`` / ``--fixed-commit-sha`` / ``--scope-snapshot``
  / ``--idempotency-key``；缺参数、API 不可达、服务端 BLOCKED、缺 mandatory case 结果或
  Comparison Snapshot 一律 ``BLOCKED`` / ``NOT_PROVEN``，绝不伪造 PASS。
- 只有原始缺陷自身（同一 ``defect_id``）的固定 SHA 回归 Run 中所有 mandatory case 通过、
  且 Comparison Snapshot 证明修复前失败/修复后通过，才可能 PASS；另一条用例（例如
  ``WWY-V5-006``）通过不改变 ``WWY-V5-001`` 的 OPEN/FAIL 状态。
- ``WWY-V5-001`` 当前证据（2026-11-27 复测仍返回 ``code=500``）保持 FAIL/OPEN。

凭据
----
    回归 API 使用平台登录 Token：默认从环境变量 ``AIQE_API_TOKEN`` 读取（Secret 注入），
    只记录 Secret 名称，不记录取值；``--token-env`` 可指定其它变量名。

用法
----
    python scripts/aiqe/per_tc/defect_regression_runner.py \\
      --api-base http://127.0.0.1:8000 --project-id 1 --defect-id 42 \\
      --fixed-commit-sha <40-hex> --scope-snapshot scope-wwy-v5-001.json \\
      --idempotency-key wwy-v5-001-20261128 \\
      --case-results case-results.json --output regression.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
AIQE_DIR = SCRIPT_DIR.parent
if str(AIQE_DIR) not in sys.path:
    sys.path.insert(0, str(AIQE_DIR))

from statuses import (  # noqa: E402
    BLOCKED,
    FAIL,
    NOT_PROVEN,
    PASS,
    is_pass,
    normalize,
)
from validators.common import is_sha, resolve_repo_path  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TOKEN_ENV = "AIQE_API_TOKEN"
DEFAULT_TIMEOUT = 30.0
REGISTRY_API = "/api/v1/aiqe/defects/{defect_id}/regressions"
REGRESSION_API = "/api/v1/aiqe/regressions/{regression_id}"
COMPARISON_API = "/api/v1/aiqe/regressions/{regression_id}/comparison"
NON_TERMINAL = frozenset({"DRAFT", "QUEUED", "RUNNING", "PENDING", ""})
DEFECT_STATES = frozenset({"OPEN", "FAILED", "FIX_VERIFIED", "CLOSED"})


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _text(value: object) -> str:
    return str(value or "").strip()


def _dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def validate_arguments(
    *,
    api_base: str,
    defect_id: object,
    fixed_commit_sha: str,
    scope_snapshot: object,
    idempotency_key: str,
) -> list[str]:
    """纯函数：校验回归调用必需参数；返回阻断原因列表（空=通过）。"""
    errors: list[str] = []
    base = _text(api_base)
    if not base:
        errors.append("缺少 --api-base（正式 Defect Regression API 基址）")
    elif not base.startswith(("http://", "https://")):
        errors.append("--api-base 必须是 http(s) URL")
    try:
        defect = int(defect_id)
    except (TypeError, ValueError):
        defect = 0
    if defect <= 0:
        errors.append("缺少/非法 --defect-id（必须是正整数缺陷主键）")
    sha = _text(fixed_commit_sha).lower()
    if not sha:
        errors.append("缺少 --fixed-commit-sha（修复提交的 40 位 SHA）")
    elif not is_sha(sha):
        errors.append("--fixed-commit-sha 不是 40 位小写十六进制 SHA")
    scope = _dict(scope_snapshot)
    mandatory = scope.get("mandatory_case_ids")
    if not isinstance(mandatory, list) or not [item for item in mandatory if _text(item)]:
        errors.append("--scope-snapshot 缺少非空 mandatory_case_ids（必须是冻结的必测用例集合）")
    key = _text(idempotency_key)
    if not key:
        errors.append("缺少 --idempotency-key（服务端幂等键）")
    elif len(key) > 128:
        errors.append("--idempotency-key 超长（服务端上限 128）")
    return errors


def load_scope_snapshot(path: str, root: Path = ROOT) -> dict:
    """读取冻结的 Mandatory Scope Snapshot；返回可校验 payload。"""
    target = resolve_repo_path(root, path) if not Path(path).is_absolute() else Path(path)
    if target is None or not target.exists():
        return {"error": f"scope snapshot 不存在或越界: {path}"}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"error": f"scope snapshot 不是合法 JSON: {exc}"}
    if not isinstance(payload, dict):
        return {"error": "scope snapshot 必须是 JSON object"}
    payload.setdefault("snapshot_id", _text(payload.get("snapshot_id")))
    return payload


def _case_results(payload: object) -> list[dict]:
    items = payload.get("mandatory_case_results") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def validate_regression_payload(
    payload: object,
    *,
    defect_id: object,
    fixed_commit_sha: str,
    mandatory_case_ids: list[str],
) -> dict:
    """纯函数：校验正式回归响应 + mandatory case 结果 + Comparison Snapshot。

    ``payload`` 形如 ``{"regression": {...}, "comparison": {...},
    "mandatory_case_results": [...]}``。缺任一关键证据 → NOT_PROVEN，绝不 PASS。
    """
    container = payload if isinstance(payload, dict) else {}
    regression = _dict(container.get("regression"))
    comparison = _dict(container.get("comparison"))
    results = _case_results(container)
    mandatory = [_text(item) for item in mandatory_case_ids if _text(item)]
    checks = {
        "fixed_sha_matches": False,
        "scope_complete": False,
        "case_results_complete": False,
        "cases_passed": False,
        "comparison_snapshot_present": False,
        "comparison_outcome_pass": False,
    }
    reasons: list[str] = []
    details: dict[str, Any] = {}

    if not regression:
        return {
            "status": NOT_PROVEN,
            "reasons": ["缺少 Defect Regression API 响应，无法证明走了正式回归链路"],
            "checks": checks,
            "details": details,
        }
    if regression.get("blocked") is True or normalize(regression.get("status")) == BLOCKED:
        blockers = regression.get("blockers") or []
        return {
            "status": BLOCKED,
            "reasons": ["Regression API 返回 BLOCKED: " + json.dumps(blockers, ensure_ascii=False)[:400]],
            "checks": checks,
            "details": details,
        }

    response_defect = regression.get("defect_id")
    try:
        same_defect = int(response_defect) == int(defect_id)
    except (TypeError, ValueError):
        same_defect = False
    if not same_defect:
        return {
            "status": NOT_PROVEN,
            "reasons": [
                f"Regression 响应 defect_id={response_defect!r} 与原始缺陷 {defect_id!r} 不一致，"
                "不能用另一条缺陷/用例替代"
            ],
            "checks": checks,
            "details": details,
        }

    sha = _text(fixed_commit_sha).lower()
    response_sha = _text(regression.get("fixed_sha")).lower()
    checks["fixed_sha_matches"] = bool(sha) and is_sha(sha) and response_sha == sha
    if not checks["fixed_sha_matches"]:
        reasons.append(
            f"fixed_sha 不匹配：请求 {sha or '<empty>'}，响应 {response_sha or '<empty>'}"
        )

    returned = [_text(item) for item in regression.get("mandatory_case_ids") or []]
    missing_scope = [case for case in mandatory if case not in returned]
    checks["scope_complete"] = bool(mandatory) and not missing_scope
    if not checks["scope_complete"]:
        reasons.append(
            "Mandatory Scope 未全覆盖：缺少 " + (", ".join(missing_scope) or "<empty>")
        )
    details["mandatory_case_ids"] = mandatory
    details["returned_case_ids"] = returned

    by_case = {_text(item.get("case_id")): item for item in results}
    missing_results = [case for case in mandatory if case not in by_case]
    checks["case_results_complete"] = bool(mandatory) and not missing_results
    if not checks["case_results_complete"]:
        reasons.append(
            "Mandatory Case Results 缺失（Regression API 未返回逐用例结果，需执行端产物）: "
            + (", ".join(missing_results) or "<empty>")
        )
    no_assertion = [
        case
        for case in mandatory
        if case in by_case
        and not (by_case[case].get("assertion_ids") or by_case[case].get("assertions"))
    ]
    if no_assertion:
        checks["case_results_complete"] = False
        reasons.append("Mandatory Case 缺少断言引用: " + ", ".join(no_assertion))
    failed_cases = [
        case
        for case in mandatory
        if case in by_case and normalize(by_case[case].get("status")) != PASS
    ]
    checks["cases_passed"] = checks["case_results_complete"] and not failed_cases
    if failed_cases:
        reasons.append("Mandatory Case 未通过: " + ", ".join(failed_cases))

    snapshot = _dict(comparison.get("snapshot"))
    available = comparison.get("available") is True
    checks["comparison_snapshot_present"] = bool(available and snapshot)
    if not checks["comparison_snapshot_present"]:
        reasons.append(
            "缺少 Comparison Snapshot（无法对比修复前后），不能作为修复验证完成"
        )
    else:
        snapshot_sha = _text(snapshot.get("fixed_sha")).lower()
        if snapshot_sha and snapshot_sha != sha:
            checks["comparison_snapshot_present"] = False
            reasons.append("Comparison Snapshot 的 fixed_sha 与本次提交不一致")
        outcome = normalize(snapshot.get("outcome"))
        new_failures = snapshot.get("new_failures") or []
        checks["comparison_outcome_pass"] = outcome == PASS and not new_failures
        if not checks["comparison_outcome_pass"]:
            reasons.append(
                f"Comparison Snapshot 结论为 {outcome or '<empty>'}（new_failures={len(new_failures)}），"
                "回归未证明修复生效"
            )

    if normalize(regression.get("status")) == FAIL:
        return {
            "status": FAIL,
            "reasons": ["Regression Run 仍 FAIL：" + "; ".join(reasons)],
            "checks": checks,
            "details": details,
        }
    if all(checks.values()):
        return {
            "status": PASS,
            "reasons": [
                "正式 Regression API 返回固定 SHA、Mandatory Scope 全覆盖、"
                "Mandatory Case 全 PASS 且 Comparison Snapshot 证明修复生效"
            ],
            "checks": checks,
            "details": details,
        }
    return {
        "status": NOT_PROVEN,
        "reasons": reasons or ["关键回归证据不完整"],
        "checks": checks,
        "details": details,
    }


def resolve_defect_state(
    *,
    defect_id: str,
    current_state: str = "OPEN",
    regression_status: str = "",
    regression_defect_id: str = "",
    passing_case_ids: tuple[str, ...] = (),
) -> dict:
    """纯函数：只有原始缺陷自身的正式回归 PASS 才能改变它的状态。

    另一条用例（例如 WWY-V5-006）PASS 不改变 WWY-V5-001；原缺陷仍失败保持 OPEN。
    """
    current = normalize_state(current_state)
    reasons: list[str] = []
    changed = False
    state = current
    same_defect = _text(regression_defect_id) == _text(defect_id)
    other_cases = [case for case in passing_case_ids if _text(case) != _text(defect_id)]

    if normalize(regression_status) == PASS and same_defect:
        state = "FIX_VERIFIED"
        changed = True
        reasons.append(f"{defect_id} 自身正式回归 PASS，可更新为修复验证完成（需审计事件）")
    elif normalize(regression_status) == PASS and not same_defect:
        reasons.append(
            f"回归 PASS 属于 {regression_defect_id or '<unknown>'}，不能改变 {defect_id}"
        )
    elif normalize(regression_status) in {NOT_PROVEN, BLOCKED} and same_defect:
        reasons.append(
            f"{defect_id} 回归证据不足或被阻塞（{normalize(regression_status)}），保持 {current}"
        )
    elif normalize(regression_status) == FAIL and same_defect:
        reasons.append(f"{defect_id} 正式回归仍 FAIL，保持 {current}")
    elif normalize(regression_status) == PASS:
        reasons.append("回归 PASS 缺少 defect_id 绑定，不能改变缺陷状态")
    if other_cases:
        reasons.append(
            "用例 " + ", ".join(other_cases) + f" 通过只代表其自身，不能覆盖/关闭 {defect_id}"
        )
    return {
        "defect_id": _text(defect_id),
        "previous_state": current,
        "state": state,
        "changed": changed,
        "reasons": reasons,
    }


def normalize_state(value: object) -> str:
    text = _text(value).upper().replace(" ", "_")
    return text if text in DEFECT_STATES else "OPEN"


def _api_payload(response: object) -> dict:
    """平台统一 envelope：{code, message, data}；兼容直接返回 data 的场景。"""
    body = response if isinstance(response, dict) else {}
    data = body.get("data")
    return data if isinstance(data, dict) else {}


class RegressionClient:
    """正式 Defect Regression API 客户端（httpx，失败即 BLOCKED）。"""

    def __init__(
        self,
        api_base: str,
        *,
        token: str = "",
        project_id: int = 0,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        import httpx

        self._httpx = httpx
        self.base = api_base.rstrip("/")
        self.timeout = timeout
        self.headers = {"accept": "application/json", "content-type": "application/json"}
        if token:
            self.headers["authorization"] = f"Bearer {token}"
        if project_id > 0:
            self.headers["X-Project-Id"] = str(project_id)

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict | None = None,
        extra_headers: dict | None = None,
    ) -> dict:
        headers = {**self.headers, **(extra_headers or {})}
        response = self._httpx.request(
            method,
            f"{self.base}{path}",
            headers=headers,
            json=json_body,
            timeout=self.timeout,
        )
        try:
            body = response.json()
        except ValueError:
            body = {}
        if response.status_code >= 400:
            raise RuntimeError(
                f"{method} {path} -> HTTP {response.status_code}: "
                f"{json.dumps(body, ensure_ascii=False)[:400]}"
            )
        return _api_payload(body)

    def create_regression(
        self,
        *,
        defect_id: int,
        fixed_commit_sha: str,
        scope: dict,
        idempotency_key: str,
        reason: str = "",
    ) -> dict:
        body = {
            "fixed_sha": fixed_commit_sha,
            "scope": _text(scope.get("scope")) or "DIRECT_FAILURES_PLUS_P0_PLUS_IMPACT",
            "selected_case_ids": [
                _text(item) for item in scope.get("mandatory_case_ids") or [] if _text(item)
            ],
            "reason": reason
            or "TC-AIQE-008 缺陷修复回归（固定 SHA + Mandatory Scope Snapshot）",
            "idempotency_key": idempotency_key,
        }
        return self._request(
            "POST",
            REGISTRY_API.format(defect_id=defect_id),
            json_body=body,
            extra_headers={"Idempotency-Key": idempotency_key},
        )

    def get_regression(self, regression_id: object) -> dict:
        return self._request("GET", REGRESSION_API.format(regression_id=regression_id))

    def get_comparison(self, regression_id: object) -> dict:
        return self._request("GET", COMPARISON_API.format(regression_id=regression_id))

    def wait_terminal(self, regression_id: object, wait_seconds: float) -> dict:
        deadline = time.monotonic() + max(wait_seconds, 0.0)
        row = self.get_regression(regression_id)
        while _text(row.get("status")).upper() in NON_TERMINAL and time.monotonic() < deadline:
            time.sleep(2.0)
            row = self.get_regression(regression_id)
        return row


def _load_case_results(path: str, root: Path) -> tuple[list[dict], list[str]]:
    if not path:
        return [], ["缺少 --case-results（Regression API 不返回逐用例结果，必须由执行端提供）"]
    target = Path(path) if Path(path).is_absolute() else resolve_repo_path(root, path)
    if target is None or not target.exists():
        return [], [f"case results 文件不存在: {path}"]
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [], [f"case results 不是合法 JSON: {exc}"]
    items = payload.get("mandatory_case_results") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        return [], ["case results 必须是数组或 {mandatory_case_results: [...]}"]
    return [item for item in items if isinstance(item, dict)], []


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TC-AIQE-008 正式 Defect 一键回归")
    parser.add_argument("--api-base", default=os.environ.get("AIQE_API_BASE", ""))
    parser.add_argument("--project-id", default=os.environ.get("AIQE_PROJECT_ID", ""))
    parser.add_argument("--defect-id", default="")
    parser.add_argument("--fixed-commit-sha", default="")
    parser.add_argument("--scope-snapshot", default="")
    parser.add_argument("--idempotency-key", default="")
    parser.add_argument("--case-results", default="")
    parser.add_argument("--reason", default="")
    parser.add_argument("--token-env", default=DEFAULT_TOKEN_ENV)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--wait-seconds", type=float, default=120.0)
    parser.add_argument("--output", default="")
    parser.add_argument("--expected-defect-state", default="OPEN")
    return parser


def _write(path: str, payload: dict) -> None:
    if not path:
        return
    target = Path(path)
    if not target.is_absolute():
        target = ROOT / target
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):  # pragma: no cover
            pass
    args = build_parser().parse_args(argv)
    result: dict[str, Any] = {
        "schema_version": "2.0",
        "artifact_kind": "defect-regression-result",
        "tc_id": "TC-AIQE-008",
        "generated_at": _now(),
        "defect_id": _text(args.defect_id),
        "fixed_commit_sha": _text(args.fixed_commit_sha).lower(),
        "idempotency_key": _text(args.idempotency_key),
        "token_secret_name": args.token_env,
        "status": BLOCKED,
        "reasons": [],
        "checks": {},
        "defect_state": {},
    }

    scope = load_scope_snapshot(args.scope_snapshot) if args.scope_snapshot else {}
    scope_error = _text(scope.get("error")) if isinstance(scope, dict) else "scope snapshot 非法"
    errors = validate_arguments(
        api_base=args.api_base,
        defect_id=args.defect_id,
        fixed_commit_sha=args.fixed_commit_sha,
        scope_snapshot=scope if not scope_error else None,
        idempotency_key=args.idempotency_key,
    )
    if scope_error:
        errors.append(scope_error)
    if errors:
        result["status"] = BLOCKED
        result["reasons"] = errors
        result["defect_state"] = resolve_defect_state(
            defect_id=result["defect_id"] or "<unknown>",
            current_state=args.expected_defect_state,
        )
        _write(args.output, result)
        print(json.dumps(result, ensure_ascii=False))
        return 1

    mandatory = [_text(item) for item in scope.get("mandatory_case_ids") or [] if _text(item)]
    token = os.environ.get(args.token_env, "")
    case_results, case_errors = _load_case_results(args.case_results, ROOT)
    try:
        project_id = int(args.project_id or 0)
    except (TypeError, ValueError):
        project_id = 0

    regression: dict = {}
    comparison: dict = {}
    if token:
        try:
            client = RegressionClient(
                args.api_base,
                token=token,
                project_id=project_id,
                timeout=args.timeout,
            )
            created = client.create_regression(
                defect_id=int(args.defect_id),
                fixed_commit_sha=result["fixed_commit_sha"],
                scope=scope,
                idempotency_key=result["idempotency_key"],
                reason=args.reason,
            )
            regression_id = created.get("id")
            if regression_id is None:
                result["reasons"] = ["Regression API 未返回 regression id，无法追踪 Run"]
                result["status"] = NOT_PROVEN
            else:
                regression = created
                result["regression_id"] = regression_id
                result["run_id"] = _dict(created.get("run")).get("id") or created.get("run_id")
                regression = client.wait_terminal(regression_id, args.wait_seconds)
                comparison = client.get_comparison(regression_id)
        except Exception as exc:  # noqa: BLE001 - 不可达/鉴权失败一律 BLOCKED
            result["status"] = BLOCKED
            result["reasons"] = [
                f"正式 Defect Regression API 不可达或拒绝请求（{type(exc).__name__}）: "
                f"{str(exc)[:400]}"
            ]
    else:
        result["status"] = BLOCKED
        result["reasons"] = [
            f"缺少 {args.token_env}（Secret 注入）；不得以匿名/默认凭据调用正式回归 API"
        ]

    if regression and not result["reasons"]:
        validation = validate_regression_payload(
            {
                "regression": regression,
                "comparison": comparison,
                "mandatory_case_results": case_results,
            },
            defect_id=args.defect_id,
            fixed_commit_sha=result["fixed_commit_sha"],
            mandatory_case_ids=mandatory,
        )
        validation["reasons"] = validation["reasons"] + case_errors
        result["status"] = validation["status"]
        result["reasons"] = validation["reasons"]
        result["checks"] = validation["checks"]
        result["evidence_details"] = validation["details"]
        result["regression_status"] = _text(regression.get("status"))
        result["comparison_available"] = bool(comparison.get("available"))

    result["defect_state"] = resolve_defect_state(
        defect_id=result["defect_id"],
        current_state=args.expected_defect_state,
        regression_status=result["status"] if regression else "",
        regression_defect_id=_text(regression.get("defect_id")) if regression else "",
        passing_case_ids=tuple(
            _text(item.get("case_id"))
            for item in case_results
            if normalize(item.get("status")) == PASS
        ),
    )
    result["scope_snapshot"] = {
        "snapshot_id": _text(scope.get("snapshot_id")),
        "checksum_sha256": _text(scope.get("checksum_sha256")),
        "mandatory_case_ids": mandatory,
    }
    if not result["reasons"]:
        result["reasons"] = ["回归证据不完整"]
    _write(args.output, result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "defect_id": result["defect_id"],
                "regression_id": result.get("regression_id"),
                "run_id": result.get("run_id"),
                "defect_state": result["defect_state"],
                "reasons": result["reasons"][:5],
            },
            ensure_ascii=False,
        )
    )
    return 0 if is_pass(result["status"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
