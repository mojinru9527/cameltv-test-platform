"""失败分析 Agent — 自动分类失败原因、提取关键信息和修复建议。

针对 API 测试和 UI 自动化执行失败的记录进行结构化分析。
"""
from __future__ import annotations

import json
import re
from typing import Any


# ── 通用分析入口 ──────────────────────────────────────────

def analyze_api_failure(item: Any) -> dict:
    """分析单条 API 执行失败项，返回结构化诊断。"""
    error_msg = getattr(item, "error_message", "") or ""
    try:
        req_snap = json.loads(getattr(item, "request_snapshot", "{}") or "{}")
    except (json.JSONDecodeError, TypeError):
        req_snap = {}
    try:
        resp_snap = json.loads(getattr(item, "response_snapshot", "{}") or "{}")
    except (json.JSONDecodeError, TypeError):
        resp_snap = {}
    try:
        assertions = json.loads(getattr(item, "assertion_results", "[]") or "[]")
    except (json.JSONDecodeError, TypeError):
        assertions = []

    # 分类
    category, confidence = _classify_api_error(error_msg, resp_snap, assertions)

    # 提取关键信息
    key_info = {
        "method": req_snap.get("method", ""),
        "url": req_snap.get("resolved_url", ""),
        "status_code": resp_snap.get("status_code", 0),
        "duration_ms": getattr(item, "duration_ms", 0),
    }

    # 修复建议
    suggestions = _suggest_api_fix(category, error_msg, resp_snap, assertions)

    return {
        "category": category,
        "confidence": confidence,
        "error_summary": error_msg[:500],
        "key_info": key_info,
        "failed_assertions": [
            {"type": a.get("type", ""), "expected": a.get("expected", ""),
             "actual": a.get("actual", ""), "message": a.get("message", "")}
            for a in assertions if not a.get("passed", True)
        ],
        "suggestions": suggestions,
    }


def analyze_ui_failure(run: Any) -> dict:
    """分析 UI 自动化运行失败项，返回结构化诊断。"""
    error_msg = getattr(run, "error_message", "") or ""
    base_url = getattr(run, "base_url", "") or ""

    try:
        result = json.loads(getattr(run, "result", "{}") or "{}")
    except (json.JSONDecodeError, TypeError):
        result = {}

    # 分类
    category, confidence = _classify_ui_error(error_msg)

    key_info = {
        "base_url": base_url,
        "total_tests": result.get("total", 0),
        "passed": result.get("pass_", 0),
        "failed": result.get("fail", 0),
    }

    suggestions = _suggest_ui_fix(category, error_msg)

    return {
        "category": category,
        "confidence": confidence,
        "error_summary": error_msg[:500],
        "key_info": key_info,
        "suggestions": suggestions,
    }


# ── 错误分类 ──────────────────────────────────────────────

def _classify_api_error(error_msg: str, resp_snapshot: dict, assertions: list[dict]) -> tuple[str, float]:
    """分类 API 错误。返回 (category, confidence 0-1)。"""
    msg_lower = error_msg.lower()
    status_code = resp_snapshot.get("status_code", 0)

    # 超时
    if "超时" in msg_lower or "timeout" in msg_lower:
        return "timeout", 0.95

    # 连接错误
    if any(kw in msg_lower for kw in ("连接失败", "connect", "connection", "refused", "dns")):
        return "connection", 0.9

    # 生产环境保护
    if "生产环境" in msg_lower or "confirm_prod" in msg_lower:
        return "prod_protection", 0.99

    # 断言失败
    failed_assertions = [a for a in assertions if not a.get("passed", True)]
    if failed_assertions:
        # 按类型细分
        a_types = {a.get("type", "") for a in failed_assertions}
        if "status_code" in a_types:
            return "status_mismatch", 0.85
        if "jsonpath" in a_types:
            return "jsonpath_mismatch", 0.8
        if "response_time" in a_types:
            return "slow_response", 0.8
        return "assertion_failed", 0.75

    # HTTP 错误状态码
    if isinstance(status_code, int) and status_code >= 500:
        return "server_error", 0.7
    if isinstance(status_code, int) and status_code >= 400:
        return "client_error", 0.7

    return "unknown", 0.3


def _classify_ui_error(error_msg: str) -> tuple[str, float]:
    """分类 UI 错误。返回 (category, confidence 0-1)。"""
    msg_lower = error_msg.lower()

    if "超时" in msg_lower or "timeout" in msg_lower or "timed out" in msg_lower:
        return "timeout", 0.95
    if "playwright" in msg_lower and ("不可用" in msg_lower or "not" in msg_lower):
        return "playwright_unavailable", 0.95
    if "npx" in msg_lower:
        return "npx_missing", 0.9
    if "不存在" in msg_lower or "not found" in msg_lower:
        return "spec_missing", 0.9
    if "取消" in msg_lower or "cancel" in msg_lower:
        return "cancelled", 0.99
    if any(kw in msg_lower for kw in ("exit", "returncode", "execution")):
        return "execution_error", 0.7
    return "other", 0.3


# ── 修复建议 ──────────────────────────────────────────────

def _suggest_api_fix(category: str, error_msg: str, resp_snapshot: dict, assertions: list[dict]) -> list[str]:
    """根据失败分类给出修复建议。"""
    suggestions: list[str] = []

    if category == "timeout":
        suggestions = [
            "确认目标服务是否正常运行",
            "检查网络连接和防火墙规则",
            "考虑增加超时时间（当前默认 30s）",
            "检查是否存在慢查询或资源瓶颈",
        ]
    elif category == "connection":
        suggestions = [
            "确认目标 URL 和端口是否正确",
            "检查目标服务是否已启动",
            "检查 DNS 解析是否正常",
            "如果是内部服务，确认在同一网络内",
        ]
    elif category == "prod_protection":
        suggestions = [
            "生产环境写操作需设置 confirm_prod=true",
            "确认是否为误操作，建议在测试环境先行验证",
            "如需执行，请二次确认并联系管理员审批",
        ]
    elif category == "status_mismatch":
        status_code = resp_snapshot.get("status_code", 0)
        suggestions = [
            f"服务端返回 HTTP {status_code}，与预期不符",
            f"检查请求参数和 Header 是否正确",
            "查看服务端日志确认错误根因",
            "确认 API 版本和接口契约是否有变更",
        ]
    elif category == "client_error":
        suggestions = [
            "检查请求参数格式和必填字段",
            "确认认证 Token/Header 是否有效",
            "检查 Content-Type 是否与服务端期望一致",
        ]
    elif category == "server_error":
        suggestions = [
            "服务端内部错误，查看服务端日志",
            "检查服务端资源（CPU/内存/数据库连接）",
            "尝试降低并发或增大重试间隔",
        ]
    elif category == "slow_response":
        suggestions = [
            "检查服务端响应时间是否超出预期",
            "考虑调整 response_time 断言阈值",
            "检查是否有慢查询或网络延迟",
        ]
    elif category == "jsonpath_mismatch":
        suggestions = [
            "检查 JSONPath 表达式是否正确",
            "确认响应体结构是否与预期一致",
            "接口契约变更可能导致字段路径变化",
        ]
    else:
        suggestions = [
            "查看完整错误信息获取更多细节",
            "使用 curl 复现接口调用",
            "与服务端开发确认接口行为",
        ]

    return suggestions


def _suggest_ui_fix(category: str, error_msg: str) -> list[str]:
    """根据 UI 失败分类给出修复建议。"""
    if category == "timeout":
        return [
            "UI 测试超时，检查页面加载速度",
            "增加测试超时时间",
            "检查目标环境是否可达",
            "考虑拆分过长的测试用例",
        ]
    elif category == "spec_missing":
        return [
            "确认 Playwright spec 文件路径正确",
            "检查脚本是否已上传到 tests/playwright/ 目录",
            "验证文件扩展名为 .spec.ts 或 .spec.js",
            "在脚本资产管理中注册该脚本",
        ]
    elif category == "playwright_unavailable":
        return [
            "运行 npx playwright install 安装 Playwright",
            "确认 Node.js 版本 >= 16",
            "检查 npx 命令是否在 PATH 中",
        ]
    elif category == "npx_missing":
        return [
            "安装 Node.js (https://nodejs.org)",
            "确保 npx 在系统 PATH 中",
            "验证 npm 安装: npm install -g npx",
        ]
    elif category == "cancelled":
        return [
            "任务被手动取消，可在确认后重新触发",
            "检查是否有其他并发任务冲突",
        ]
    elif category == "execution_error":
        return [
            "查看 Playwright 测试报告获取详细错误",
            "检查页面选择器是否仍然有效",
            "确认测试数据是否准备就绪",
        ]
    return [
        "查看产物目录中的截图和报告",
        "使用 npx playwright test --debug 调试",
        "检查测试脚本中的选择器和断言",
    ]
