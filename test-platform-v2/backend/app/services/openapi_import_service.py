"""OpenAPI/Swagger 导入服务 — 预览 + 确认导入接口资产。"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.api_asset import ApiEndpoint, ApiImportBatch, ApiService


# ── source_type → source label mapping ──
_SOURCE_LABEL_MAP: dict[str, str] = {
    "openapi_url": "openapi",
    "openapi_text": "openapi",
    "swagger_doc_url": "knife4j_import",
}


def _source_label(source_type: str) -> str:
    """Map source_type to the label stored on ApiEndpoint.source."""
    return _SOURCE_LABEL_MAP.get(source_type, "openapi")


def preview_openapi_import(
    spec: dict,
    *,
    project_id: int,
    service_name: str,
) -> dict:
    """预览导入：解析 OpenAPI/Swagger spec，返回接口列表和统计。
    不写入数据库，仅返回预览结果。
    """
    endpoints = _extract_endpoints(spec)
    version = spec.get("info", {}).get("version", "")

    # 标记每个 endpoint 的 source
    for ep in endpoints:
        ep["source"] = "openapi"

    return {
        "service_name": service_name,
        "version": version,
        "total_count": len(endpoints),
        "new_count": len(endpoints),   # 预览阶段不查 DB，由 confirm 阶段去重
        "existing_count": 0,
        "endpoints": endpoints,
        "errors": [],
    }


def preview_openapi_import_with_db(
    db: Session,
    spec: dict,
    *,
    project_id: int,
    service_name: str,
) -> dict:
    """带 DB 的导入预览：检查已存在的接口。"""
    endpoints = _extract_endpoints(spec)
    version = spec.get("info", {}).get("version", "")

    # 查找已有 service
    service = db.query(ApiService).filter_by(project_id=project_id, name=service_name).first()
    existing_paths: set[tuple[str, str]] = set()
    if service:
        existing = db.query(ApiEndpoint).filter_by(project_id=project_id, service_id=service.id).all()
        existing_paths = {(ep.method.upper(), ep.path) for ep in existing}

    new_count = 0
    existing_count = 0
    for ep in endpoints:
        ep["source"] = "openapi"
        if (ep["method"].upper(), ep["path"]) in existing_paths:
            ep["_exists"] = True
            existing_count += 1
        else:
            ep["_exists"] = False
            new_count += 1

    return {
        "service_name": service_name,
        "version": version,
        "total_count": len(endpoints),
        "new_count": new_count,
        "existing_count": existing_count,
        "endpoints": endpoints,
        "errors": [],
    }


def confirm_openapi_import(
    db: Session,
    spec: dict,
    *,
    project_id: int,
    service_name: str,
    source_ref: str = "",
    source_type: str = "openapi_url",
) -> dict:
    """确认导入：将 spec 中的接口写入 api_endpoint 表（upsert），记录 import batch。"""
    endpoints = _extract_endpoints(spec)
    version = spec.get("info", {}).get("version", "")

    # 1. 确保 service 存在
    service = db.query(ApiService).filter_by(project_id=project_id, name=service_name).first()
    if not service:
        service = ApiService(project_id=project_id, name=service_name, display_name=service_name)
        db.add(service)
        db.flush()

    # 2. 创建 import batch
    batch = ApiImportBatch(
        project_id=project_id,
        service_id=service.id,
        source_type=source_type,
        source_ref=source_ref,
        version=version,
        status="processing",
        total_count=len(endpoints),
    )
    db.add(batch)
    db.flush()

    created = 0
    updated = 0
    skipped = 0
    errors = []
    source_label = _source_label(source_type)

    for ep_data in endpoints:
        try:
            method = ep_data["method"].upper()
            path = ep_data["path"]

            existing = db.query(ApiEndpoint).filter_by(
                project_id=project_id, service_id=service.id, method=method, path=path,
            ).first()

            if existing:
                # 更新已有接口
                existing.summary = ep_data.get("summary", existing.summary)
                existing.description = ep_data.get("description", existing.description)
                existing.request_schema = json.dumps(ep_data.get("request_schema", {}), ensure_ascii=False)
                existing.response_schema = json.dumps(ep_data.get("response_schema", {}), ensure_ascii=False)
                existing.module = ep_data.get("module", existing.module)
                existing.version = version
                existing.import_batch_id = batch.id
                existing.source = source_label
                existing.deprecated = ep_data.get("deprecated", False)
                updated += 1
            else:
                endpoint = ApiEndpoint(
                    project_id=project_id,
                    service_id=service.id,
                    module=ep_data.get("module", ""),
                    method=method,
                    path=path,
                    summary=ep_data.get("summary", ""),
                    description=ep_data.get("description", ""),
                    request_schema=json.dumps(ep_data.get("request_schema", {}), ensure_ascii=False),
                    response_schema=json.dumps(ep_data.get("response_schema", {}), ensure_ascii=False),
                    auth_required=ep_data.get("auth_required", False),
                    deprecated=ep_data.get("deprecated", False),
                    source=source_label,
                    import_batch_id=batch.id,
                    version=version,
                )
                db.add(endpoint)
                created += 1
        except Exception as e:
            errors.append({"method": ep_data.get("method"), "path": ep_data.get("path"), "error": str(e)})
            skipped += 1

    # 3. 更新 batch 统计
    batch.created_count = created
    batch.updated_count = updated
    batch.skipped_count = skipped
    batch.error_detail = json.dumps(errors, ensure_ascii=False)
    batch.status = "completed"

    db.commit()

    return {
        "batch_id": batch.id,
        "service_name": service_name,
        "version": version,
        "total_count": len(endpoints),
        "created_count": created,
        "updated_count": updated,
        "skipped_count": skipped,
        "generated_case_count": 0,
        "errors": errors,
    }


# ═══════════════════════════════════════════════════════
# 内部解析
# ═══════════════════════════════════════════════════════

def _extract_endpoints(spec: dict) -> list[dict]:
    """从 OpenAPI 3.x 或 Swagger 2.0 spec 提取接口列表。"""
    paths = spec.get("paths", {})
    if not paths:
        return []

    endpoints = []
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, detail in methods.items():
            if method.upper() not in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"):
                continue
            if not isinstance(detail, dict):
                continue

            tags = detail.get("tags", [])
            module = tags[0] if tags else _infer_module_from_path(path)

            # 提取 request schema（传入完整 spec 用于 $ref 解析）
            request_schema = _extract_request_schema(detail, spec)

            # 提取 response schema
            response_schema = _extract_response_schema(detail)

            # 检查是否需要认证
            auth_required = _check_auth_required(detail)

            endpoints.append({
                "module": module,
                "method": method.upper(),
                "path": path,
                "summary": detail.get("summary", ""),
                "description": detail.get("description", ""),
                "request_schema": request_schema,
                "response_schema": response_schema,
                "auth_required": auth_required,
                "deprecated": detail.get("deprecated", False),
                "tags": tags,
            })

    return endpoints


def _infer_module_from_path(path: str) -> str:
    """从接口路径推断模块名，取第二段（跳过 /api/v1 这类前缀）。"""
    segments = [s for s in path.split("/") if s]
    if not segments:
        return "default"
    # 如果第一段是 api，取第二段；否则取第二段（如果存在）或第一段
    if segments[0].lower() in ("api", "v1", "v2", "v3"):
        # 跳过 api 和版本号
        idx = 1
        while idx < len(segments) and segments[idx].lower() in ("v1", "v2", "v3"):
            idx += 1
        if idx < len(segments):
            return segments[idx]
        return segments[0]
    return segments[1] if len(segments) > 1 else segments[0]


def _resolve_ref(spec: dict, ref: str) -> dict:
    """Resolve a JSON $ref pointer against the spec.

    Supports:
      - Swagger 2.0:  #/definitions/Foo
      - OpenAPI 3.x:  #/components/schemas/Foo
    Returns the resolved schema dict, or empty dict on failure.
    """
    if not ref or not ref.startswith("#/"):
        return {}
    parts = ref[2:].split("/")
    current: Any = spec
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return {}
        if current is None:
            return {}
    return current if isinstance(current, dict) else {}


def _extract_request_schema(detail: dict, spec: dict | None = None) -> dict:
    """Extract request parameters/body schema from an operation.

    Handles:
      - OpenAPI 3.x requestBody
      - Swagger 2.0 parameters (query/path/header/body with inline or $ref schema)
    """
    schema: dict = {}

    # parameters (query, path, header) — shared by OpenAPI 3.x and Swagger 2.0
    params = detail.get("parameters", [])
    if params:
        query_params = []
        path_params = []
        header_params = []
        for p in params:
            if not isinstance(p, dict):
                continue

            # Swagger 2.0 body parameter
            if p.get("in") == "body":
                body_schema = p.get("schema", {})
                # Resolve $ref if present
                if "$ref" in body_schema and spec:
                    resolved = _resolve_ref(spec, body_schema["$ref"])
                    if resolved:
                        body_schema = resolved
                schema["body"] = {
                    "content_type": "application/json",
                    "type": body_schema.get("type", "object"),
                    "properties": body_schema.get("properties", {}),
                    "required": body_schema.get("required", []),
                }
                continue

            param_info = {
                "name": p.get("name", ""),
                "type": _resolve_schema_type(p.get("schema", {})) if p.get("schema") else p.get("type", "string"),
                "required": p.get("required", False),
                "description": p.get("description", ""),
            }
            if p.get("in") == "query":
                query_params.append(param_info)
            elif p.get("in") == "path":
                path_params.append(param_info)
            elif p.get("in") == "header":
                header_params.append(param_info)

        if query_params:
            schema["query"] = query_params
        if path_params:
            schema["path"] = path_params
        if header_params:
            schema["header"] = header_params

    # requestBody (OpenAPI 3.x)
    request_body = detail.get("requestBody", {})
    if request_body:
        content = request_body.get("content", {})
        for media_type, media_schema in content.items():
            body_schema = media_schema.get("schema", {})
            schema["body"] = {
                "content_type": media_type,
                "type": body_schema.get("type", "object"),
                "properties": body_schema.get("properties", {}),
                "required": body_schema.get("required", []),
            }
            break  # 取第一个 media type

    return schema


def _extract_response_schema(detail: dict) -> dict:
    """提取成功响应 schema。"""
    responses = detail.get("responses", {})
    # 优先取 200/201 响应
    for code in ("200", "201"):
        resp = responses.get(code, {})
        if resp:
            content = resp.get("content", {})
            for media_type, media_schema in content.items():
                return {
                    "status_code": code,
                    "content_type": media_type,
                    "schema": media_schema.get("schema", {}),
                }
    return {}


def _check_auth_required(detail: dict) -> bool:
    """检查接口是否需要认证（有 security 定义）。"""
    security = detail.get("security", [])
    if security and len(security) > 0:
        # security 是 [{"bearerAuth": []}] 格式
        return True
    return False


def _resolve_schema_type(schema: dict) -> str:
    """从 JSON Schema 中解析类型字符串。"""
    if not schema:
        return "string"
    stype = schema.get("type", "string")
    if stype == "array":
        items = schema.get("items", {})
        item_type = items.get("type", "string") if items else "string"
        return f"array<{item_type}>"
    return stype
