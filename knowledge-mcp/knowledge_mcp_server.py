#!/usr/bin/env python3
"""
测试平台知识中心 MCP 服务器（DSH 测试 Agent 框架 · 阶段 1/2）

把测试平台知识中心（L0 骨架）与执行链路暴露为 MCP 工具，供 DSH 测试船长
团队（tester-team）使用：

- 查询面：search_knowledge / get_module_topology / get_knowledge_sources /
  get_requirements / get_test_cases（Agent 熟悉项目、按图索骥）
- 执行面：trigger_test_plan / get_execution_result（平台 Runner 执行，agent 只编排）
- 回写面：submit_test_cases（用例直接入库，规则单一事实源 = test-case-design skill）

只经平台开放 API（/api/v1/open/*）通信，不直连数据库。
鉴权：PLATFORM_API_TOKEN（Bearer tpat_xxx）+ PLATFORM_PROJECT_ID（X-Project-Id）。
仿照 lanhu-mcp 的 FastMCP HTTP 模式（path=/mcp）。
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import httpx

# 加载 .env（不覆盖已存在的环境变量，与 lanhu-mcp 一致）
try:
    from dotenv import load_dotenv

    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)
    else:
        load_dotenv(override=False)
except ImportError:
    pass

from fastmcp import FastMCP  # noqa: E402

logger = logging.getLogger("knowledge-mcp")

# ── 配置 ──────────────────────────────────────────────
BASE_URL = os.getenv("PLATFORM_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
API_TOKEN = os.getenv("PLATFORM_API_TOKEN", "")
PROJECT_ID = os.getenv("PLATFORM_PROJECT_ID", "1")
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "30"))

mcp = FastMCP("CamelTv Knowledge Center")


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {API_TOKEN}",
        "X-Project-Id": PROJECT_ID,
        "Content-Type": "application/json",
    }


def _call(method: str, path: str, json_body: dict | None = None, params: dict | None = None) -> Any:
    """调用平台开放 API，返回 envelope data；非 0 code 抛异常。"""
    url = f"{BASE_URL}/api/v1/open{path}"
    try:
        if method == "GET":
            resp = httpx.get(url, headers=_headers(), params=params, timeout=HTTP_TIMEOUT)
        else:
            resp = httpx.post(url, headers=_headers(), json=json_body or {}, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"平台 API {method} {path} 失败: HTTP {exc.response.status_code}: {exc.response.text[:300]}") from exc
    except httpx.HTTPError as exc:
        raise RuntimeError(f"平台 API {method} {path} 不可达: {exc}") from exc

    payload = resp.json()
    if payload.get("code") != 0:
        raise RuntimeError(f"平台 API {method} {path} 业务错误: code={payload.get('code')} msg={payload.get('msg')}")
    return payload.get("data")


# ── 查询面 ────────────────────────────────────────────

@mcp.tool()
def search_knowledge(query: str, top_k: int = 8) -> list[dict]:
    """RAG 混合检索项目知识（需求/接口/用例/缺陷/执行结果切片）。

    Agent 熟悉项目/定位用例时优先调用；结果含 title/snippet/source 归属。
    """
    return _call("POST", "/knowledge/search", json_body={"query": query, "top_k": top_k})


@mcp.tool()
def get_module_topology(module: str | None = None) -> dict:
    """项目知识拓扑：模块实体 + 挂接子实体（需求/用例/接口/设计稿）。

    Agent onboarding 先取拓扑定位影响面（L0 骨架），再按需拉详情。
    module 为可选模块名过滤。
    """
    params = {"module": module} if module else None
    return _call("GET", "/knowledge/modules", params=params)


@mcp.tool()
def get_knowledge_sources(source_type: str | None = None, keyword: str | None = None) -> dict:
    """知识源列表（source_type: requirement/test_case/api/defect/execution）。"""
    params: dict[str, Any] = {}
    if source_type:
        params["source_type"] = source_type
    if keyword:
        params["keyword"] = keyword
    return _call("GET", "/knowledge/sources", params=params)


@mcp.tool()
def get_requirements(keyword: str | None = None) -> dict:
    """需求文档列表（不含全文），定位需求/追溯用例用。"""
    params = {"keyword": keyword} if keyword else None
    return _call("GET", "/requirements", params=params)


@mcp.tool()
def get_test_cases(module: str = "", keyword: str = "", case_type: str = "", priority: str = "") -> dict:
    """用例列表（含模块/需求追溯/接口契约三关联元数据）。"""
    params: dict[str, Any] = {}
    if module:
        params["module"] = module
    if keyword:
        params["keyword"] = keyword
    if case_type:
        params["case_type"] = case_type
    if priority:
        params["priority"] = priority
    return _call("GET", "/test-cases", params=params)


# ── 执行面（阶段 2 打通，API 已就位）────────────────────

@mcp.tool()
def get_test_plans(status: str = "", keyword: str = "") -> dict:
    """测试计划列表（含用例统计），api-tester 选择触发目标用。"""
    params: dict[str, Any] = {}
    if status:
        params["status"] = status
    if keyword:
        params["keyword"] = keyword
    return _call("GET", "/plans", params=params)


@mcp.tool()
def get_test_plan(plan_id: int) -> dict:
    """测试计划详情（含用例清单），执行前核对用例/环境用。"""
    return _call("GET", f"/plans/{plan_id}")


@mcp.tool()
def get_plan_executions(plan_id: int, page_size: int = 50) -> dict:
    """计划最近执行记录（含每条用例 last_status），判定/回读用。"""
    params = {"page_size": page_size}
    return _call("GET", f"/plans/{plan_id}/executions", params=params)


@mcp.tool()
def trigger_test_plan(plan_id: int) -> dict:
    """触发平台测试计划执行（平台 Runner 执行，agent 只编排不直连测试环境）。

    返回 triggered/plan_name/cases_queued；结果用 get_execution_result 查询。
    """
    return _call("POST", f"/plans/{plan_id}/trigger")


@mcp.tool()
def get_execution_result(run_id: int) -> dict:
    """查询一次测试计划执行的状态与结果（run_id 来自 trigger_test_plan 或平台）。"""
    return _call("GET", f"/runs/{run_id}")


# ── UI 自动化面（阶段 3 ui-tester 编排入口）──────────────

@mcp.tool()
def get_ui_test_jobs(keyword: str = "") -> dict:
    """UI 自动化任务列表（含最近运行状态），ui-tester 选择触发目标用。"""
    params = {"keyword": keyword} if keyword else None
    return _call("GET", "/ui-tests", params=params)


@mcp.tool()
def trigger_ui_test(job_id: int) -> dict:
    """触发平台 UI 自动化任务（平台 Runner 执行）。

    返回 run_id/run_status；结果用 get_ui_test_run 查询。
    """
    return _call("POST", f"/ui-tests/{job_id}/trigger")


@mcp.tool()
def get_ui_test_run(run_id: int) -> dict:
    """查询 UI 测试运行状态与结果。"""
    return _call("GET", f"/ui-tests/runs/{run_id}")


# ── 回写面 ────────────────────────────────────────────

@mcp.tool()
def submit_test_cases(cases: list[dict]) -> list[dict]:
    """用例直接入库（走 test-case-design skill 规则产出，不经 AI 审核台）。

    每个 case 必填 title；建议含 module/priority/case_type/steps/expected_result/
    source_req_id（需求追溯）/api_endpoint（接口关联）。project 由平台 token 隔离。
    """
    results = []
    for case in cases:
        data = _call("POST", "/test-cases", json_body=case)
        results.append(data)
    return results


@mcp.tool()
def submit_defect(defect: dict) -> dict:
    """缺陷直接入库（C-A4：测试发现缺陷回写平台缺陷库）。

    必填 title；建议含 description/severity(P0-P3)/case_id/execution_id/
    external_id/external_url（证据链接）。project 由平台 token 隔离；
    入库后自动沉淀知识中心（缺陷知识源）。
    """
    return _call("POST", "/defects", json_body=defect)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT = int(os.getenv("MCP_PORT", "8110"))
    mcp.run(transport="http", path="/mcp", host=SERVER_HOST, port=SERVER_PORT)
