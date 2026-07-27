"""统一业务异常 + 处理器。"""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class APIException(Exception):
    """业务异常：携带业务错误码与提示。"""

    def __init__(self, code: int = 1, msg: str = "操作失败", http_status: int = 200):
        self.code = code
        self.msg = msg
        self.http_status = http_status
        super().__init__(msg)


def unauthorized(msg: str = "未登录或登录已过期") -> APIException:
    return APIException(code=401, msg=msg, http_status=401)


def forbidden(msg: str = "无权限") -> APIException:
    return APIException(code=403, msg=msg, http_status=403)


def not_found(msg: str = "资源不存在") -> APIException:
    return APIException(code=404, msg=msg, http_status=404)


async def api_exception_handler(_: Request, exc: APIException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content={"code": exc.code, "msg": exc.msg, "data": None},
    )
