"""Server-side guard for environment-targeted production operations."""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy.orm import Session

from app.core.exceptions import APIException, forbidden, not_found
from app.models.environment import Environment
from app.services.audit_service import write_audit


@dataclass(frozen=True)
class ProductionOperation:
    action: str
    project_id: int
    environment_id: int | None
    permission: str
    confirmed: bool


def require_allowed_operation(
    db: Session,
    operation: ProductionOperation,
    user_permissions: set[str],
) -> Environment | None:
    """Return a project-owned environment after policy and audit checks.

    A non-empty ``permission`` marks an operation as production-sensitive.
    Production-sensitive actions require both the dedicated permission and an
    explicit confirmation. Read-only operations pass an empty permission while
    still receiving project-isolation and audit enforcement.
    """
    action = operation.action.strip()
    if not action:
        raise APIException(code=400, msg="操作名称不能为空", http_status=400)
    if operation.project_id <= 0:
        raise APIException(code=400, msg="操作缺少有效项目", http_status=400)
    if operation.environment_id is None:
        raise APIException(code=400, msg="操作必须指定目标环境", http_status=400)

    environment = db.query(Environment).filter(
        Environment.id == operation.environment_id,
        Environment.project_id == operation.project_id,
    ).first()
    if environment is None:
        raise not_found("环境不存在或不属于当前项目")

    is_production = environment.env_type == "prod" or environment.is_production
    if is_production and operation.permission:
        if "*" not in user_permissions and operation.permission not in user_permissions:
            raise forbidden(f"生产环境操作需要 {operation.permission} 权限")
        if not operation.confirmed:
            raise APIException(
                code=400,
                msg="生产环境操作需要 confirm_prod=true 明确确认",
                http_status=400,
            )

    target = (
        f'env#{environment.id} "{environment.name}" '
        f'({_sanitized_base_url(environment.base_url)})'
    )
    write_audit(
        db,
        project_id=operation.project_id,
        action="production_operation:allowed",
        target=target,
        detail=f"{action}; environment_type={environment.env_type}",
    )
    return environment


def _sanitized_base_url(value: str) -> str:
    """Remove credentials, query strings and fragments from an audit target."""
    if not value:
        return "no-base-url"
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        if parsed.port:
            host = f"{host}:{parsed.port}"
        safe = urlunsplit((parsed.scheme, host, parsed.path, "", ""))
        return safe or "invalid-base-url"
    except ValueError:
        return "invalid-base-url"
