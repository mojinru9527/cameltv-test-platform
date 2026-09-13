"""AI runtime route planning for cloud/local-first rollouts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.services.ai_config_service import AIProviderUnconfiguredError, ai_config_service
from app.services.ai_gateway.runtime import local_runtime_config

VALID_RUNTIME_MODES = {"cloud_only", "shadow", "local_preferred", "local_only"}


class LocalRuntimeUnavailableError(RuntimeError):
    """The selected local-only route has no configured local runtime."""


@dataclass(frozen=True)
class RoutePlan:
    mode: str
    primary_origin: str
    primary_config: Any
    fallback_config: Any | None = None
    fallback_origin: str = ""
    shadow_config: Any | None = None
    shadow_origin: str = ""


def runtime_mode() -> str:
    mode = (settings.ai_runtime_mode or "cloud_only").strip().lower()
    return mode if mode in VALID_RUNTIME_MODES else "cloud_only"


def resolve_route(db, project_id: int, *, namespace: str = "") -> RoutePlan | None:
    """Resolve the configured route without performing any model call.

    Cloud config remains the source of truth for project-level providers. Local
    runtime config is optional and is only activated by an explicit mode.
    """
    if not settings.ai_enabled:
        return None
    try:
        cloud = ai_config_service.resolve(db, project_id)
    except AIProviderUnconfiguredError:
        cloud = None
    return build_route(cloud=cloud, mode=runtime_mode(), shadow_enabled=settings.ai_shadow_enabled)


def build_route(*, cloud: Any | None, mode: str, shadow_enabled: bool) -> RoutePlan | None:
    """Pure route builder used by tests and resolve_route()."""
    local = local_runtime_config()
    local_cfg = local.as_ai_config() if local else None

    if mode == "local_only":
        if local_cfg is None:
            raise LocalRuntimeUnavailableError("本地 runtime 未启用或未配置，local_only 路由不可用")
        return RoutePlan(mode=mode, primary_origin="local", primary_config=local_cfg)

    if cloud is None and local_cfg is None:
        return None

    if mode == "cloud_only":
        if cloud is None:
            raise LocalRuntimeUnavailableError("cloud_only 模式需要项目级云端 Provider")
        return RoutePlan(mode=mode, primary_origin="cloud", primary_config=cloud)

    if mode == "shadow":
        if cloud is None:
            raise LocalRuntimeUnavailableError("shadow 模式需要项目级云端 Provider")
        shadow = local_cfg if shadow_enabled and local_cfg is not None else None
        return RoutePlan(
            mode=mode,
            primary_origin="cloud",
            primary_config=cloud,
            shadow_config=shadow,
            shadow_origin="local" if shadow else "",
        )

    # local_preferred: degrade to cloud when local runtime is absent.
    if local_cfg is None:
        if cloud is None:
            return None
        return RoutePlan(mode=mode, primary_origin="cloud", primary_config=cloud)

    fallback = cloud if cloud is not None and settings.ai_local_fallback_to_cloud else None
    shadow = cloud if cloud is not None and shadow_enabled else None
    return RoutePlan(
        mode=mode,
        primary_origin="local",
        primary_config=local_cfg,
        fallback_config=fallback,
        fallback_origin="cloud" if fallback else "",
        shadow_config=shadow,
        shadow_origin="cloud" if shadow else "",
    )
