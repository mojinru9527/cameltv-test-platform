"""外部 LLM-Wiki 连接器（只读）—— 对接外部 LLM Wiki Desktop/API。

方法约定：
- 所有函数接收 ExternalWikiConnection 模型对象，不直接操作数据库。
- 所有外部 HTTP 调用均设置超时（默认 10s），超时不抛异常，返回结构化错误。
- token 通过 app.core.cipher.decrypt_value 解密后使用。
- 不支持的 provider 返回明确错误，不抛出异常。
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.cipher import decrypt_value

logger = logging.getLogger("external_llm_wiki")

_DEFAULT_TIMEOUT = 10.0  # seconds


def _parse_connection(connection: Any) -> dict:
    """从 ExternalWikiConnection ORM 对象提取所需字段。"""
    base_url = (getattr(connection, "base_url", "") or "").rstrip("/")
    token = ""
    encrypted = getattr(connection, "token_encrypted", None) or None
    if encrypted:
        try:
            token = decrypt_value(encrypted)
        except Exception:
            logger.warning("Failed to decrypt token for connection id=%s", getattr(connection, "id", 0),
                           exc_info=True)
            token = ""
    provider = getattr(connection, "provider", "") or ""
    external_project_id = getattr(connection, "external_project_id", None) or ""
    return {
        "base_url": base_url,
        "token": token,
        "provider": provider,
        "external_project_id": external_project_id,
    }


def _build_headers(token: str) -> dict[str, str]:
    """构建通用请求头。"""
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _make_request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = _DEFAULT_TIMEOUT,
    **kwargs: Any,
) -> dict:
    """通用 httpx 请求封装，始终返回 dict，不抛异常。"""
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.request(method, url, headers=headers or {}, **kwargs)
            try:
                body = resp.json()
            except Exception:
                body = {"raw": resp.text[:4096]}
            return {"ok": resp.is_success, "status_code": resp.status_code, "data": body}
    except httpx.TimeoutException:
        return {"ok": False, "status_code": 0, "error": f"请求超时（{timeout}s）", "data": None}
    except httpx.ConnectError:
        return {"ok": False, "status_code": 0, "error": "连接失败，目标不可达", "data": None}
    except Exception as exc:
        logger.warning("External wiki request failed: %s %s — %s", method, url, exc)
        return {"ok": False, "status_code": 0, "error": str(exc)[:500], "data": None}


def health_check(connection: Any) -> dict:
    """检查外部 Wiki 是否可达。

    Returns:
        {"ok": bool, "version": str, "message": str}
    """
    cfg = _parse_connection(connection)
    if not cfg["base_url"]:
        return {"ok": False, "version": "", "message": "base_url 未配置"}

    if cfg["provider"] == "llm_wiki_desktop":
        # LLM Wiki Desktop 默认健康检查端点
        url = f"{cfg['base_url']}/api/health"
    else:
        url = f"{cfg['base_url']}/health"

    headers = _build_headers(cfg["token"])
    result = _make_request("GET", url, headers=headers, timeout=10)

    if result["ok"]:
        version = ""
        if isinstance(result.get("data"), dict):
            version = str(result["data"].get("version", result["data"].get("app_version", "")))
        return {"ok": True, "version": version, "message": "连接正常"}
    else:
        err = result.get("error", f"HTTP {result.get('status_code', '?')}")
        return {"ok": False, "version": "", "message": err}


def search(connection: Any, query: str, limit: int = 10) -> list[dict]:
    """搜索外部 Wiki 页面。

    Returns:
        list[dict]: 搜索结果列表，每个元素含 title/snippet/path/score 等字段。
        出错时返回空列表。
    """
    cfg = _parse_connection(connection)
    if not cfg["base_url"]:
        return []

    if cfg["provider"] == "llm_wiki_desktop":
        url = f"{cfg['base_url']}/api/search"
    else:
        url = f"{cfg['base_url']}/search"

    headers = _build_headers(cfg["token"])
    result = _make_request("GET", url, headers=headers, timeout=15,
                           params={"q": query, "limit": limit})

    if result["ok"] and isinstance(result.get("data"), dict):
        items = result["data"].get("items", result["data"].get("results", []))
        if isinstance(items, list):
            return items
    if result["ok"] and isinstance(result.get("data"), list):
        return result["data"]

    logger.warning("External wiki search failed: %s", result.get("error", "unknown"))
    return []


def read_page(connection: Any, path: str) -> dict:
    """读取外部 Wiki 中的指定页面。

    Returns:
        dict: {"ok": bool, "title": str, "content_md": str, "meta": dict}
        出错时 ok=False 并携带 error 字段。
    """
    cfg = _parse_connection(connection)
    if not cfg["base_url"]:
        return {"ok": False, "error": "base_url 未配置", "title": "", "content_md": "", "meta": {}}

    if cfg["provider"] == "llm_wiki_desktop":
        url = f"{cfg['base_url']}/api/files/{path.lstrip('/')}"
    else:
        url = f"{cfg['base_url']}/pages/{path.lstrip('/')}"

    headers = _build_headers(cfg["token"])
    result = _make_request("GET", url, headers=headers, timeout=15)

    if result["ok"]:
        data = result.get("data") or {}
        if isinstance(data, dict):
            return {
                "ok": True,
                "title": str(data.get("title", data.get("name", ""))),
                "content_md": str(data.get("content", data.get("content_md", data.get("body", "")))),
                "meta": data.get("meta", data.get("metadata", {})),
            }
        return {"ok": True, "title": "", "content_md": str(data), "meta": {}}
    else:
        return {
            "ok": False,
            "error": result.get("error", f"HTTP {result.get('status_code', '?')}"),
            "title": "",
            "content_md": "",
            "meta": {},
        }


def graph(connection: Any, node: str) -> dict:
    """获取外部 Wiki 中节点的图谱/连接。

    Returns:
        dict: {"ok": bool, "node": str, "edges": list[dict], "nodes": list[dict]}
        出错时 ok=False 并携带 error 字段。
    """
    cfg = _parse_connection(connection)
    if not cfg["base_url"]:
        return {"ok": False, "error": "base_url 未配置", "node": node, "edges": [], "nodes": []}

    if cfg["provider"] == "llm_wiki_desktop":
        url = f"{cfg['base_url']}/api/graph"
    else:
        url = f"{cfg['base_url']}/graph"

    headers = _build_headers(cfg["token"])
    result = _make_request("GET", url, headers=headers, timeout=15,
                           params={"node": node})

    if result["ok"]:
        data = result.get("data") or {}
        if isinstance(data, dict):
            return {
                "ok": True,
                "node": node,
                "edges": data.get("edges", data.get("links", [])),
                "nodes": data.get("nodes", data.get("vertices", [])),
            }
        return {"ok": True, "node": node, "edges": [], "nodes": []}
    else:
        return {
            "ok": False,
            "error": result.get("error", f"HTTP {result.get('status_code', '?')}"),
            "node": node,
            "edges": [],
            "nodes": [],
        }
