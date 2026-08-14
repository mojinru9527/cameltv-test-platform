"""会话凭证自动注入服务 — 为 API 用例执行提供全局 token/mid 自动获取与注入。

背景（XMind「测试流程与AI自动化」建议落地）：
- 体育平台等被测系统通常需要「先匿名登录/获取会话，再携带 token 访问业务接口」。
- 传统做法：人工在环境变量里手填 token，token 过期后需人工刷新。
- 本服务：在环境变量中配置会话凭证获取接口（session_credential_url 等），
  执行 API 用例时若请求引用了 $session.* 变量，则自动调用凭证接口获取
  token/mid，合并进变量表后统一替换 —— 全局 token、全局 mid 自动配置。

约定（环境变量键）：
- session_credential_url    凭证接口完整 URL（支持 ${ENV} 占位，必填）
- session_credential_method 凭证接口方法，默认 POST
- session_credential_headers 额外请求头 JSON（可选）
- session_credential_body   凭证接口请求体模板（可选，支持 ${ENV} 占位）
- session_credential_app_code 体育平台 appCode 快捷参数（可选，会并入请求体）

注入变量（$session.*）：
- $session.token  → 响应体 detail.value（蓝湖/体育平台匿名登录响应结构
                    {"code":0,"detail":{"key":"Anonyxxx","value":"C_..."}}）
- $session.key    → 响应体 detail.key
- $session.mid    → 响应体 detail.mid（若存在）或自定义 jsonpath（见下）
- $session.<field> → 响应体顶层 detail.<field> / data.<field> / result.<field>

凭证缓存：按 (project_id, environment_id, 配置指纹) 缓存到执行进程内，
TTL 默认 300 秒，避免每次用例都重复调用凭证接口。
"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from app.services.environment_service import resolve_variables

# ── 配置键（环境变量名） ──
KEY_URL = "session_credential_url"
KEY_METHOD = "session_credential_method"
KEY_HEADERS = "session_credential_headers"
KEY_BODY = "session_credential_body"
KEY_APP_CODE = "session_credential_app_code"
KEY_FIELD_MAP = "session_field_map"  # 可选 JSON: {"mid": "$.detail.mid"} 自定义取值路径

_SESSION_VAR_PREFIX = "session."

# 凭证缓存：{(project_id, environment_id, fingerprint): (expires_at, creds)}
_CRED_CACHE: dict[tuple[int, int, str], tuple[float, dict[str, str]]] = {}
CRED_CACHE_TTL = 300.0  # 秒


def _fingerprint(env_config: dict[str, str]) -> str:
    """基于凭证配置内容生成指纹，配置变化时缓存自动失效。"""
    return json.dumps(env_config, ensure_ascii=False, sort_keys=True)


def _dig(obj: Any, path: str) -> Any:
    """按点路径取 dict 字段（支持嵌套，如 detail.key / data.token）。"""
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def _extract_credentials(resp_json: dict) -> dict[str, str]:
    """从凭证接口响应中提取 token/key/mid。

    支持响应结构：
    - {"code":0,"detail":{"key":"Anonyxxx","value":"C_..."}}        （体育平台匿名登录）
    - {"code":0,"data":{"token":"...","mid":"..."}}
    - {"result":{"token":"...","key":"..."}}
    """
    creds: dict[str, str] = {}

    detail = (
        resp_json.get("detail") if isinstance(resp_json.get("detail"), dict) else None
    )
    data = resp_json.get("data") if isinstance(resp_json.get("data"), dict) else None
    result = (
        resp_json.get("result") if isinstance(resp_json.get("result"), dict) else None
    )

    # value 优先作为 token（匿名登录响应语义）
    if detail and detail.get("value"):
        creds["token"] = str(detail["value"])
    if detail and detail.get("key"):
        creds["key"] = str(detail["key"])
    if detail and detail.get("mid") is not None:
        creds["mid"] = str(detail["mid"])

    for src in (data, result):
        if not src:
            continue
        if "token" in src and "token" not in creds:
            creds["token"] = str(src["token"])
        if "access_token" in src and "token" not in creds:
            creds["token"] = str(src["access_token"])
        if "mid" in src and "mid" not in creds:
            creds["mid"] = str(src["mid"])
        if "key" in src and "key" not in creds:
            creds["key"] = str(src["key"])
        if "value" in src and "token" not in creds:
            creds["token"] = str(src["value"])

    return creds


def _load_env_config(db, environment_id: int, project_id: int) -> dict[str, str] | None:
    """读取环境变量中会话凭证相关配置；未配置返回 None。"""
    url = resolve_variables(db, environment_id, project_id, "${" + KEY_URL + "}")
    if not url or url == "${" + KEY_URL + "}":
        return None
    method = resolve_variables(db, environment_id, project_id, "${" + KEY_METHOD + "}")
    if not method or method == "${" + KEY_METHOD + "}":
        method = "POST"
    headers_raw = resolve_variables(
        db, environment_id, project_id, "${" + KEY_HEADERS + "}"
    )
    body_raw = resolve_variables(db, environment_id, project_id, "${" + KEY_BODY + "}")
    app_code = resolve_variables(
        db, environment_id, project_id, "${" + KEY_APP_CODE + "}"
    )
    field_map_raw = resolve_variables(
        db, environment_id, project_id, "${" + KEY_FIELD_MAP + "}"
    )

    def _unset(v: str | None) -> bool:
        return not v or (v.startswith("${") and v.endswith("}"))

    cfg: dict[str, str] = {"url": url, "method": method.upper()}
    if not _unset(headers_raw):
        cfg["headers"] = headers_raw  # type: ignore[assignment]
    if not _unset(body_raw):
        cfg["body"] = body_raw  # type: ignore[assignment]
    if not _unset(app_code):
        cfg["app_code"] = app_code  # type: ignore[assignment]
    if not _unset(field_map_raw):
        cfg["field_map"] = field_map_raw  # type: ignore[assignment]
    return cfg


def fetch_session_credentials(
    db,
    environment_id: int | None,
    project_id: int,
    *,
    force: bool = False,
) -> dict[str, str]:
    """获取会话凭证。返回 {token, key, mid, ...}；未配置或失败时返回空 dict。

    - 未配置凭证接口 → {}
    - 配置但调用失败 → {}（调用方降级为不注入，不影响用例执行）
    - 配置成功 → 缓存并返回凭证
    """
    if not environment_id:
        return {}
    cfg = _load_env_config(db, environment_id, project_id)
    if not cfg:
        return {}

    fp = _fingerprint(cfg)
    cache_key = (project_id, environment_id, fp)
    now = time.time()
    cached = _CRED_CACHE.get(cache_key)
    if cached and not force and cached[0] > now:
        return cached[1]

    # 构造请求
    headers = {"Content-Type": "application/json"}
    try:
        if "headers" in cfg:
            headers.update(json.loads(cfg["headers"]))  # type: ignore[arg-type]
    except (json.JSONDecodeError, TypeError):
        pass

    body: dict[str, Any] = {}
    try:
        if "body" in cfg:
            parsed = json.loads(cfg["body"])
            if isinstance(parsed, dict):
                body.update(parsed)
    except (json.JSONDecodeError, TypeError):
        pass
    if "app_code" in cfg and "appCode" not in body:
        body["appCode"] = cfg["app_code"]

    try:
        resp = httpx.request(
            cfg["method"],
            cfg["url"],
            headers=headers,
            json=body if body else None,
            timeout=15,
        )
        resp.raise_for_status()
        resp_json = resp.json()
    except Exception:
        # 凭证获取失败：降级为不注入，保证用例主流程不受影响
        return {}

    creds = _extract_credentials(resp_json)

    # 自定义字段映射（field_map: {"mid": "$.detail.mid" ...}）
    try:
        if "field_map" in cfg:
            fm = json.loads(cfg["field_map"])
            if isinstance(fm, dict):
                for name, path in fm.items():
                    val = _dig(resp_json, str(path).lstrip("$."))
                    if val is not None:
                        creds[name] = str(val)
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass

    if creds:
        _CRED_CACHE[cache_key] = (now + CRED_CACHE_TTL, creds)
    return creds


def session_variable_map(
    db,
    environment_id: int | None,
    project_id: int,
) -> dict[str, str]:
    """构造 $session.* 变量映射表（key 去掉 'session.' 前缀）。

    供执行引擎在变量替换前合并：若请求引用 $session.token 等变量，
    则自动获取凭证并注入；未配置或未引用时返回空 dict（零开销）。
    """
    if not environment_id:
        return {}
    creds = fetch_session_credentials(db, environment_id, project_id)
    if not creds:
        return {}
    return {f"session.{k}": v for k, v in creds.items()}


def clear_credential_cache() -> None:
    """清空凭证缓存（测试/配置变更时调用）。"""
    _CRED_CACHE.clear()
