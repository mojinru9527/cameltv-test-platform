"""AITDE V3.7 diff providers (V37-003..007) — plan §4.

Each provider is a pure, deterministic function that compares a ``baseline`` and
``current`` normalized structure and returns a list of change-item dicts. They
do not touch the DB; ``ChangeSetService`` persists the produced items. This keeps
the breaking-change logic unit-testable and free of I/O.

A change-item dict has the shape::

    {
      "change_kind": "ADDED"|"CHANGED"|"DELETED",
      "entity_type": "<LineageNodeType>",
      "entity_key": "<stable key>",
      "before_json": "<json>|None",
      "after_json": "<json>|None",
      "risk_hint": "<RiskHint>",
      "source_refs_json": "<json list>",
    }
"""

from __future__ import annotations

import json
from typing import Any

from app.modules.aitde.common.enums import ChangeItemKind, LineageNodeType, RiskHint

_K = {
    "ADDED": ChangeItemKind.ADDED.value,
    "CHANGED": ChangeItemKind.CHANGED.value,
    "DELETED": ChangeItemKind.DELETED.value,
}


def _item(
    change_kind: str,
    entity_type: str,
    entity_key: str,
    before: Any | None,
    after: Any | None,
    risk_hint: str = RiskHint.NONE.value,
    source_refs: list | None = None,
) -> dict:
    return {
        "change_kind": _K[change_kind],
        "entity_type": entity_type,
        "entity_key": entity_key,
        "before_json": json.dumps(before, ensure_ascii=False, sort_keys=True)
        if before is not None
        else None,
        "after_json": json.dumps(after, ensure_ascii=False, sort_keys=True)
        if after is not None
        else None,
        "risk_hint": risk_hint,
        "source_refs_json": json.dumps(
            source_refs or [], ensure_ascii=False, sort_keys=True
        ),
    }


def diff_requirement(baseline: dict, current: dict) -> list[dict]:
    """PRD / requirement fragment diff (V37-003). Added/changed/deleted fragments.

    ``baseline``/``current`` map ``fragment_key -> {title, text, content_hash}.
    A content_hash change marks the fragment as changed (recent-change risk).
    """
    items: list[dict] = []
    baseline = baseline or {}
    current = current or {}
    for key, cur in current.items():
        if key not in baseline:
            items.append(
                _item(
                    "ADDED",
                    LineageNodeType.SOURCE_FRAGMENT.value,
                    key,
                    None,
                    cur,
                    RiskHint.NONE.value,
                )
            )
        else:
            prev = baseline[key]
            prev_hash = prev.get("content_hash", "")
            cur_hash = cur.get("content_hash", "")
            if prev_hash != cur_hash:
                items.append(
                    _item(
                        "CHANGED",
                        LineageNodeType.SOURCE_FRAGMENT.value,
                        key,
                        prev,
                        cur,
                        RiskHint.RECENT_CHANGE.value,
                    )
                )
    for key in baseline.keys() - current.keys():
        items.append(
            _item(
                "DELETED",
                LineageNodeType.SOURCE_FRAGMENT.value,
                key,
                baseline[key],
                None,
                RiskHint.NONE.value,
            )
        )
    return items


def diff_openapi(baseline: dict, current: dict) -> list[dict]:
    """OpenAPI breaking-change diff (V37-004).

    ``baseline``/``current`` map ``operation_key`` (``METHOD /path``) ->
    ``{request_required: [...], responses: {status: {required: [...]}}}``.

    Emits a ``CONTRACT_RULE`` risk only for schema/required/status-content-type
    breaking changes; purely additive additions stay low-risk unless a new
    required request field is added.
    """
    items: list[dict] = []
    baseline = baseline or {}
    current = current or {}
    for key, cur in current.items():
        if key not in baseline:
            items.append(
                _item(
                    "ADDED",
                    LineageNodeType.API_ENDPOINT.value,
                    key,
                    None,
                    cur,
                    RiskHint.NONE.value,
                )
            )
            continue
        prev = baseline[key]
        reasons = _openapi_breaking(prev, cur)
        if reasons:
            items.append(
                _item(
                    "CHANGED",
                    LineageNodeType.API_ENDPOINT.value,
                    key,
                    _openapi_summary(prev),
                    _openapi_summary(cur),
                    RiskHint.CONTRACT_RULE.value,
                    [f"{k}: {'; '.join(r)}" for k, r in reasons.items()],
                )
            )
    for key in baseline.keys() - current.keys():
        items.append(
            _item(
                "DELETED",
                LineageNodeType.API_ENDPOINT.value,
                key,
                baseline[key],
                None,
                RiskHint.NONE.value,
            )
        )
    return items


def _openapi_breaking(prev: dict, cur: dict) -> dict:
    """Return ``{reason_code: [details]}`` for breaking diffs (empty = non-breaking)."""
    reasons: dict = {}

    prev_req = set(prev.get("request_required", []))
    cur_req = set(cur.get("request_required", []))
    added_req = cur_req - prev_req
    if added_req:
        reasons["request_required_added"] = sorted(added_req)

    prev_responses = prev.get("responses", {}) or {}
    cur_responses = cur.get("responses", {}) or {}
    removed_status = set(prev_responses.keys()) - set(cur_responses.keys())
    if removed_status:
        reasons["response_status_removed"] = sorted(removed_status)

    for status in set(prev_responses) & set(cur_responses):
        prev_req = set((prev_responses.get(status) or {}).get("required", []))
        cur_req = set((cur_responses.get(status) or {}).get("required", []))
        removed_req = prev_req - cur_req
        if removed_req:
            reasons.setdefault(f"response_{status}_required_removed", []).extend(
                sorted(removed_req)
            )

    prev_cc = (prev.get("request_content_type") or "").strip()
    cur_cc = (cur.get("request_content_type") or "").strip()
    if prev_cc and cur_cc and prev_cc != cur_cc:
        reasons["request_content_type_changed"] = [f"{prev_cc} -> {cur_cc}"]
    return reasons


def _openapi_summary(op: dict) -> dict:
    return {
        "request_required": sorted(op.get("request_required", [])),
        "responses": {
            s: sorted((r or {}).get("required", []))
            for s, r in (op.get("responses", {}) or {}).items()
        },
    }


def diff_db_schema(baseline: dict, current: dict) -> list[dict]:
    """DB schema diff (V37-005) — column / enum / index changes.

    ``baseline``/``current`` map ``table -> {columns: {col: {type, nullable}},
    enums: [values], indexes: [...]}. Removing a column, changing its type, or
    removing an enum value are treated as contract-level changes.
    """
    items: list[dict] = []
    baseline = baseline or {}
    current = current or {}
    for table, cur in current.items():
        prev = baseline.get(table)
        if prev is None:
            items.append(
                _item(
                    "ADDED",
                    LineageNodeType.DATA_ENTITY.value,
                    table,
                    None,
                    _schema_summary(cur),
                    RiskHint.NONE.value,
                )
            )
            continue
        col_changes = _column_changes(prev, cur)
        enum_changes = _enum_changes(prev, cur)
        if col_changes or enum_changes:
            items.append(
                _item(
                    "CHANGED",
                    LineageNodeType.DATA_ENTITY.value,
                    table,
                    _schema_summary(prev),
                    _schema_summary(cur),
                    (
                        RiskHint.CONTRACT_RULE.value
                        if enum_changes
                        or any(c.startswith("type") for c in col_changes)
                        else RiskHint.RECENT_CHANGE.value
                    ),
                    col_changes + enum_changes,
                )
            )
    for table in baseline.keys() - current.keys():
        items.append(
            _item(
                "DELETED",
                LineageNodeType.DATA_ENTITY.value,
                table,
                baseline[table],
                None,
                RiskHint.NONE.value,
            )
        )
    return items


def _column_changes(prev: dict, cur: dict) -> list[str]:
    changes: list[str] = []
    prev_cols = prev.get("columns") or {}
    cur_cols = cur.get("columns") or {}
    for col in cur_cols.keys() - prev_cols.keys():
        changes.append(f"column_added:{col}")
    for col in prev_cols.keys() - cur_cols.keys():
        changes.append(f"column_removed:{col}")
    for col in set(prev_cols) & set(cur_cols):
        if (prev_cols[col] or {}).get("type") != (cur_cols[col] or {}).get("type"):
            changes.append(f"type_changed:{col}")
    return changes


def _enum_changes(prev: dict, cur: dict) -> list[str]:
    changes: list[str] = []
    prev_enums = (prev.get("enums") or {}) or {}
    cur_enums = (cur.get("enums") or {}) or {}
    for name in set(prev_enums) | set(cur_enums):
        prev_vals = set(prev_enums.get(name, []))
        cur_vals = set(cur_enums.get(name, []))
        removed = prev_vals - cur_vals
        if removed:
            changes.append(f"enum_value_removed:{name}:{sorted(removed)}")
    return changes


def _schema_summary(schema: dict) -> dict:
    return {
        "columns": {
            c: {
                "type": (cdef or {}).get("type"),
                "nullable": (cdef or {}).get("nullable"),
            }
            for c, cdef in (schema.get("columns") or {}).items()
        },
        "enums": {k: sorted(v) for k, v in (schema.get("enums") or {}).items()},
        "indexes": sorted(schema.get("indexes") or []),
    }


def diff_ui_discovery(baseline: dict, current: dict) -> list[dict]:
    """UI discovery diff (V37-006) — semantic page/action graph changes.

    ``baseline``/``current`` map ``page_key -> {semantic_hash, actions:
    {action_key: {semantic_hash, selector}}}``. A change that keeps the
    semantics but alters the locator is low-risk (cosmetic); a semantic
    action add/remove/change is a recent-change risk.
    """
    items: list[dict] = []
    baseline = baseline or {}
    current = current or {}
    for page, cur in current.items():
        prev = baseline.get(page)
        if prev is None:
            items.append(
                _item(
                    "ADDED",
                    LineageNodeType.PAGE.value,
                    page,
                    None,
                    _ui_summary(cur),
                    RiskHint.NONE.value,
                )
            )
            continue
        semantic_changed = prev.get("semantic_hash") != cur.get("semantic_hash")
        action_diff = _ui_action_diff(
            (prev.get("actions") or {}), (cur.get("actions") or {})
        )
        risk = (
            RiskHint.RECENT_CHANGE.value
            if semantic_changed or action_diff
            else RiskHint.NONE.value
        )
        if semantic_changed or action_diff:
            items.append(
                _item(
                    "CHANGED",
                    LineageNodeType.PAGE.value,
                    page,
                    _ui_summary(prev),
                    _ui_summary(cur),
                    risk,
                    action_diff,
                )
            )
    for page in baseline.keys() - current.keys():
        items.append(
            _item(
                "DELETED",
                LineageNodeType.PAGE.value,
                page,
                baseline[page],
                None,
                RiskHint.NONE.value,
            )
        )
    return items


def _ui_action_diff(prev_actions: dict, cur_actions: dict) -> list[str]:
    changes: list[str] = []
    for a in cur_actions.keys() - prev_actions.keys():
        changes.append(f"action_added:{a}")
    for a in prev_actions.keys() - cur_actions.keys():
        changes.append(f"action_removed:{a}")
    for a in set(prev_actions) & set(cur_actions):
        if (prev_actions[a] or {}).get("semantic_hash") != (cur_actions[a] or {}).get(
            "semantic_hash"
        ):
            changes.append(f"action_semantic_changed:{a}")
    return changes


def _ui_summary(page: dict) -> dict:
    return {
        "semantic_hash": page.get("semantic_hash", ""),
        "actions": {
            a: {"semantic_hash": (ad or {}).get("semantic_hash", "")}
            for a, ad in (page.get("actions") or {}).items()
        },
    }


def diff_environment(baseline: dict, current: dict) -> list[dict]:
    """Environment variable diff (V37-007-pre). Value/sensitivity changes are
    ``ENVIRONMENT`` change items carrying a recent-change risk."""
    items: list[dict] = []
    baseline = baseline or {}
    current = current or {}
    for key, cur in current.items():
        prev = baseline.get(key)
        if prev is None:
            items.append(
                _item("ADDED", "ENVIRONMENT", key, None, cur, RiskHint.NONE.value)
            )
        elif prev.get("value") != cur.get("value"):
            items.append(
                _item(
                    "CHANGED",
                    "ENVIRONMENT",
                    key,
                    {
                        "value": prev.get("value"),
                        "sensitivity": prev.get("sensitivity"),
                    },
                    {"value": cur.get("value"), "sensitivity": cur.get("sensitivity")},
                    RiskHint.RECENT_CHANGE.value,
                )
            )
    for key in baseline.keys() - current.keys():
        items.append(
            _item(
                "DELETED", "ENVIRONMENT", key, baseline[key], None, RiskHint.NONE.value
            )
        )
    return items


def diff_historical_risk(signals: list[dict]) -> list[dict]:
    """Historical risk provider (V37-007): surface risk signals per scenario.

    ``signals`` = ``[{scenario_id, scenario_version_id, risk_hint, reason,
    source_refs}]``. Emits a ``SCENARIO`` change item carrying the highest-risk
    hint so the ImpactAnalyzer includes the scenario.
    """
    items: list[dict] = []
    weight_order = {
        RiskHint.P0_RULE.value: 5,
        RiskHint.CONTRACT_RULE.value: 4,
        RiskHint.LAST_BUSINESS_FAIL.value: 4,
        RiskHint.HISTORICAL_DEFECT.value: 3,
        RiskHint.PROD_REAL_WORLD.value: 3,
        RiskHint.RECENT_CHANGE.value: 2,
        RiskHint.UNKNOWN_CHANGE.value: 2,
        RiskHint.NONE.value: 0,
    }
    cache: dict[str, dict] = {}
    for sig in signals or []:
        scenario_id = int(sig.get("scenario_id") or 0)
        if not scenario_id:
            continue
        hint = sig.get("risk_hint") or RiskHint.NONE.value
        key = str(scenario_id)
        cur = cache.get(key)
        if cur is None or weight_order.get(hint, 0) > weight_order.get(
            cur.get("risk_hint") or "", 0
        ):
            cache[key] = {
                "scenario_id": scenario_id,
                "scenario_version_id": sig.get("scenario_version_id"),
                "risk_hint": hint,
                "reason": sig.get("reason", ""),
                "source_refs": sig.get("source_refs", []),
            }
    for key, sig in sorted(cache.items()):
        items.append(
            _item(
                "CHANGED",
                LineageNodeType.SCENARIO.value,
                key,
                None,
                {
                    "scenario_version_id": sig.get("scenario_version_id"),
                    "reason": sig.get("reason", ""),
                },
                sig["risk_hint"],
                sig.get("source_refs", []),
            )
        )
    return items
