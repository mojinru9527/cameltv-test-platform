"""V16-024：Prometheus 指标端点（token 鉴权，生产 fail-closed）。"""
from __future__ import annotations

import hmac

from fastapi import APIRouter, Header
from fastapi.responses import PlainTextResponse

from app.aiqe.observability.metrics import metrics
from app.core.config import settings
from app.core.exceptions import APIException

router = APIRouter(prefix="/aiqe", tags=["AIQE Observability"])


@router.get("/metrics", summary="AIQE Prometheus 指标")
def get_aiqe_metrics(
    x_aiqe_metrics_token: str | None = Header(default=None, alias="X-AIQE-Metrics-Token"),
) -> PlainTextResponse:
    configured = str(settings.aiqe_metrics_token or "").strip()
    if configured:
        if not x_aiqe_metrics_token or not hmac.compare_digest(
            str(x_aiqe_metrics_token), configured
        ):
            raise APIException(code=401, msg="metrics token 无效", http_status=401)
    elif str(settings.environment) == "production":
        raise APIException(
            code=403, msg="生产环境必须配置 AIQE_METRICS_TOKEN", http_status=403
        )
    return PlainTextResponse(metrics.render())
