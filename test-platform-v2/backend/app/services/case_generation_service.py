"""Generate API/UI test assets for version missions."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.test_case import TestCase
from app.models.version_mission import VersionMission
from app.services import version_mission_service


PLAYWRIGHT_SPECS_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "playwright" / "specs"


def generate_api_cases_from_openapi(
    db: Session,
    *,
    mission_id: int,
    project_id: int,
    spec: dict[str, Any],
    source_name: str = "swagger",
    import_to_case_library: bool = True,
) -> dict:
    mission = _mission_or_raise(db, mission_id, project_id)
    cases = _openapi_to_cases(spec, mission, project_id, source_name)
    imported_ids: list[int] = []
    if import_to_case_library:
        imported_ids = _upsert_cases(db, cases, project_id)
    artifact = version_mission_service.record_artifact(
        db,
        project_id=project_id,
        mission_id=mission_id,
        artifact_type="api_cases",
        source=source_name,
        name=f"{mission.version} API cases from OpenAPI",
        content=json.dumps(cases, ensure_ascii=False, indent=2),
        meta={"case_count": len(cases), "imported_ids": imported_ids},
    )
    version_mission_service.write_log(
        db,
        project_id=project_id,
        mission_id=mission_id,
        department="qa-department",
        agent_name="api-tester",
        action="api-cases:generate:openapi",
        input_ref=source_name,
        output_ref=f"artifact:{artifact['id']}",
        detail=f"Generated {len(cases)} API cases from OpenAPI",
        payload={"case_count": len(cases), "imported_ids": imported_ids},
    )
    db.commit()
    return {"cases": cases, "imported_ids": imported_ids, "artifact": artifact}


def generate_api_cases_from_traffic(
    db: Session,
    *,
    mission_id: int,
    project_id: int,
    traffic: list[dict[str, Any]],
    source_name: str = "ui-capture",
    import_to_case_library: bool = True,
) -> dict:
    mission = _mission_or_raise(db, mission_id, project_id)
    cases = _traffic_to_cases(traffic, mission, project_id, source_name)
    imported_ids: list[int] = []
    if import_to_case_library:
        imported_ids = _upsert_cases(db, cases, project_id)
    artifact = version_mission_service.record_artifact(
        db,
        project_id=project_id,
        mission_id=mission_id,
        artifact_type="api_cases",
        source=source_name,
        name=f"{mission.version} API cases from captured traffic",
        content=json.dumps(cases, ensure_ascii=False, indent=2),
        meta={"case_count": len(cases), "imported_ids": imported_ids},
    )
    version_mission_service.write_log(
        db,
        project_id=project_id,
        mission_id=mission_id,
        department="qa-department",
        agent_name="api-tester",
        action="api-cases:generate:traffic",
        input_ref=source_name,
        output_ref=f"artifact:{artifact['id']}",
        detail=f"Generated {len(cases)} supplemental API cases from UI traffic",
        payload={"case_count": len(cases), "imported_ids": imported_ids},
    )
    db.commit()
    return {"cases": cases, "imported_ids": imported_ids, "artifact": artifact}


def generate_ui_drafts(
    db: Session,
    *,
    mission_id: int,
    project_id: int,
    priorities: list[str],
    write_specs: bool = True,
    max_cases: int = 30,
) -> dict:
    mission = _mission_or_raise(db, mission_id, project_id)
    stmt = select(TestCase).where(
        TestCase.project_id == project_id,
        TestCase.case_type.in_(["manual", "ui"]),
        TestCase.priority.in_(priorities),
        TestCase.status != "archived",
    )
    if mission.requirement_doc_id:
        stmt = stmt.where(TestCase.source_doc_id == mission.requirement_doc_id)
    cases = db.scalars(stmt.order_by(TestCase.priority, TestCase.id).limit(max_cases)).all()
    spec_text = _build_playwright_spec(mission, cases)
    spec_rel = f"generated/{_slug(mission.mission_key)}.spec.ts"
    spec_abs = PLAYWRIGHT_SPECS_DIR / spec_rel
    if write_specs:
        spec_abs.parent.mkdir(parents=True, exist_ok=True)
        spec_abs.write_text(spec_text, encoding="utf-8")
    artifact = version_mission_service.record_artifact(
        db,
        project_id=project_id,
        mission_id=mission_id,
        artifact_type="ui_draft",
        source="functional-p0-p1",
        name=f"{mission.version} UI automation draft",
        ref_id=spec_rel,
        content=spec_text,
        meta={"case_count": len(cases), "written": write_specs, "spec": spec_rel},
    )
    version_mission_service.write_log(
        db,
        project_id=project_id,
        mission_id=mission_id,
        department="qa-department",
        agent_name="ui-automation-planner",
        action="ui-draft:generate",
        output_ref=spec_rel if write_specs else f"artifact:{artifact['id']}",
        detail=f"Generated UI automation draft for {len(cases)} P0/P1 cases",
        payload={"case_count": len(cases), "priorities": priorities, "spec": spec_rel},
    )
    db.commit()
    return {"spec": spec_rel, "content": spec_text, "case_count": len(cases), "artifact": artifact}


def _openapi_to_cases(
    spec: dict[str, Any],
    mission: VersionMission,
    project_id: int,
    source_name: str,
) -> list[dict[str, Any]]:
    paths = spec.get("paths") or {}
    cases: list[dict[str, Any]] = []
    seq = 1
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, op in methods.items():
            method_upper = method.upper()
            if method_upper not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}:
                continue
            op = op if isinstance(op, dict) else {}
            title = op.get("summary") or op.get("operationId") or f"{method_upper} {path}"
            tags = op.get("tags") if isinstance(op.get("tags"), list) else []
            module = str(tags[0]) if tags else _module_from_path(path)
            case_id = f"API-{_slug(module).upper()}-{seq:03d}"
            assertions = [
                {"type": "status_code", "operator": "lt", "expected": 500},
                {"type": "response_time", "operator": "lt", "expected": 3000},
            ]
            cases.append({
                "project_id": project_id,
                "case_id": case_id,
                "title": title,
                "domain": "接口测试",
                "module": module,
                "case_type": "api",
                "priority": _priority_from_method(method_upper),
                "status": "active",
                "tags": json.dumps(["version:" + mission.version, "source:" + source_name], ensure_ascii=False),
                "preconditions": f"目标版本 {mission.version} 已部署，接口服务可访问。",
                "steps": json.dumps([
                    {"step": 1, "desc": f"发送 {method_upper} {path}", "expected": "接口返回非 5xx 响应"},
                    {"step": 2, "desc": "校验响应时间和基础结构", "expected": "响应时间小于 3000ms"},
                ], ensure_ascii=False),
                "expected_result": "接口响应符合契约，且无服务端错误。",
                "api_method": method_upper,
                "api_endpoint": path,
                "api_spec_ref": op.get("operationId", ""),
                "api_headers": json.dumps({"Content-Type": "application/json"}, ensure_ascii=False),
                "api_body": _sample_body(op),
                "api_assertions": json.dumps(assertions, ensure_ascii=False),
                "source": "swagger_import" if source_name == "swagger" else source_name,
                "source_doc_id": mission.requirement_doc_id,
            })
            seq += 1
    return cases


def _traffic_to_cases(
    traffic: list[dict[str, Any]],
    mission: VersionMission,
    project_id: int,
    source_name: str,
) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    cases: list[dict[str, Any]] = []
    for item in traffic:
        method = str(item.get("method") or item.get("request", {}).get("method") or "GET").upper()
        url = str(item.get("url") or item.get("request", {}).get("url") or "")
        path = _path_from_url(url)
        if not path or method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            continue
        key = (method, path)
        if key in seen:
            continue
        seen.add(key)
        status_code = item.get("status") or item.get("response", {}).get("status") or 200
        module = _module_from_path(path)
        idx = len(cases) + 1
        cases.append({
            "project_id": project_id,
            "case_id": f"API-CAP-{idx:03d}",
            "title": f"UI 流量覆盖 {method} {path}",
            "domain": "接口测试",
            "module": module,
            "case_type": "api",
            "priority": "P1",
            "status": "active",
            "tags": json.dumps(["version:" + mission.version, "source:" + source_name], ensure_ascii=False),
            "preconditions": "已通过 UI 自动化或手工流程捕获真实请求。",
            "steps": json.dumps([
                {"step": 1, "desc": f"回放捕获请求 {method} {path}", "expected": f"HTTP {status_code} 或符合业务预期"},
            ], ensure_ascii=False),
            "expected_result": "捕获接口可稳定回放，响应符合版本预期。",
            "api_method": method,
            "api_endpoint": path,
            "api_spec_ref": "",
            "api_headers": json.dumps(_headers_from_traffic(item), ensure_ascii=False),
            "api_body": json.dumps(item.get("postData") or item.get("body") or {}, ensure_ascii=False),
            "api_assertions": json.dumps([
                {"type": "status_code", "operator": "lt", "expected": 500},
            ], ensure_ascii=False),
            "source": "ui_capture",
            "source_doc_id": mission.requirement_doc_id,
        })
    return cases


def _upsert_cases(db: Session, cases: list[dict[str, Any]], project_id: int) -> list[int]:
    imported_ids: list[int] = []
    for case in cases:
        existing = db.scalar(
            select(TestCase).where(
                TestCase.project_id == project_id,
                TestCase.case_type == "api",
                TestCase.api_method == case["api_method"],
                TestCase.api_endpoint == case["api_endpoint"],
            )
        )
        if existing:
            for key, value in case.items():
                if key in {"project_id", "case_id"}:
                    continue
                setattr(existing, key, value)
            imported_ids.append(existing.id)
        else:
            row = TestCase(**case)
            db.add(row)
            db.flush()
            imported_ids.append(row.id)
    return imported_ids


def _build_playwright_spec(mission: VersionMission, cases: list[TestCase]) -> str:
    base_url = mission.test_env_url or "process.env.TEST_BASE_URL || 'http://localhost:5173'"
    lines = [
        "import { test, expect } from '@playwright/test';",
        "",
        f"const baseUrl = {json.dumps(base_url, ensure_ascii=False)};",
        "",
        f"test.describe({json.dumps(mission.title + ' UI draft', ensure_ascii=False)}, () => {{",
    ]
    if not cases:
        lines.extend([
            "  test('mission has no P0/P1 functional cases yet', async ({ page }) => {",
            "    await page.goto(baseUrl);",
            "    await expect(page).toHaveURL(/.*/);",
            "  });",
        ])
    for case in cases:
        title = f"{case.case_id or 'TC'} {case.title}"
        steps = _safe_json(case.steps, [])
        lines.append(f"  test({json.dumps(title, ensure_ascii=False)}, async ({{ page }}) => {{")
        lines.append("    await page.goto(baseUrl);")
        lines.append("    await expect(page).toHaveURL(/.*/);")
        lines.append(f"    // Source case priority: {case.priority}; module: {case.module}")
        for idx, step in enumerate(steps[:8], start=1):
            desc = step.get("desc") or step.get("step") or str(step)
            expected = step.get("expected", "")
            lines.append(f"    await test.step({json.dumps(str(idx) + '. ' + desc, ensure_ascii=False)}, async () => {{")
            lines.append(f"      // Expected: {expected}")
            lines.append("    });")
        lines.append("  });")
    lines.append("});")
    lines.append("")
    return "\n".join(lines)


def _sample_body(op: dict[str, Any]) -> str:
    content = ((op.get("requestBody") or {}).get("content") or {})
    app_json = content.get("application/json") or next(iter(content.values()), {})
    schema = app_json.get("schema") if isinstance(app_json, dict) else {}
    if not isinstance(schema, dict):
        return ""
    sample = _sample_from_schema(schema)
    return json.dumps(sample, ensure_ascii=False) if sample not in (None, {}) else ""


def _sample_from_schema(schema: dict[str, Any]) -> Any:
    if "example" in schema:
        return schema["example"]
    if schema.get("type") == "object":
        props = schema.get("properties") or {}
        return {k: _sample_from_schema(v if isinstance(v, dict) else {}) for k, v in props.items()}
    if schema.get("type") == "array":
        return [_sample_from_schema(schema.get("items") or {})]
    if schema.get("type") == "integer":
        return 1
    if schema.get("type") == "number":
        return 1.0
    if schema.get("type") == "boolean":
        return True
    return "string"


def _mission_or_raise(db: Session, mission_id: int, project_id: int) -> VersionMission:
    mission = db.scalar(
        select(VersionMission).where(
            VersionMission.id == mission_id,
            VersionMission.project_id == project_id,
        )
    )
    if not mission:
        raise ValueError("版本测试任务不存在")
    return mission


def _module_from_path(path: str) -> str:
    parts = [p for p in path.split("/") if p and not p.startswith("{")]
    return parts[1] if len(parts) > 1 and parts[0].lower() in {"api", "v1", "v2"} else (parts[0] if parts else "default")


def _priority_from_method(method: str) -> str:
    return "P0" if method in {"POST", "PUT", "PATCH", "DELETE"} else "P1"


def _path_from_url(url: str) -> str:
    if not url:
        return ""
    match = re.match(r"^https?://[^/]+(?P<path>/[^?#]*)", url)
    return match.group("path") if match else url.split("?", 1)[0]


def _headers_from_traffic(item: dict[str, Any]) -> dict[str, str]:
    headers = item.get("headers") or item.get("request", {}).get("headers") or {}
    if isinstance(headers, list):
        return {str(h.get("name", "")): str(h.get("value", "")) for h in headers if h.get("name")}
    if isinstance(headers, dict):
        return {str(k): str(v) for k, v in headers.items()}
    return {}


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or "generated"


def _safe_json(raw: str, default: Any) -> Any:
    try:
        return json.loads(raw) if raw else default
    except (TypeError, json.JSONDecodeError):
        return default
