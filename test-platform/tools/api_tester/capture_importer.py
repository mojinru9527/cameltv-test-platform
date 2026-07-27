"""UI 捕获流量导入器：读取 UI 自动化捕获的 JSONL → EndpointSpec 列表。

输入格式: JSONL，每行一条 API 请求记录
  {
    "method": "GET",
    "path": "/api/ugc/list",
    "query": {"categoryId": "A"},
    "body": {},
    "headers": {},
    "status": 200,
    "response_body": {...},
    "timestamp": "2024-..."
  }

输出: EndpointSpec 列表，标记 source: ui-capture
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.api_tester.swagger_parser import EndpointSpec

ROOT = Path(__file__).resolve().parent.parent.parent


class CaptureImporter:
    """从 UI 自动化捕获的流量 JSONL 提取接口定义。"""

    def import_session(self, session_id: str) -> list[EndpointSpec]:
        """读取指定 session 的捕获流量，去重后返回 EndpointSpec 列表。"""
        captured_dir = ROOT / "tests" / "api-testing" / "captured"
        # 查找匹配 session_id 的 JSONL 文件
        pattern = f"*{session_id}*.jsonl"
        files = sorted(captured_dir.glob(pattern))
        if not files:
            # 也尝试从 automation/ui/captured 查找
            alt_dir = ROOT / "tests" / "automation" / "ui" / "captured"
            files = sorted(alt_dir.glob(pattern))

        if not files:
            print(f"[WARN] 未找到 session '{session_id}' 的捕获流量文件。")
            print(f"  搜索路径: {captured_dir}, {alt_dir}")
            return []

        all_entries = []
        for fp in files:
            all_entries.extend(self._parse_jsonl(fp))

        # 按 (method, path) 去重，每个唯一接口只保留一个
        seen: dict[str, EndpointSpec] = {}
        for entry in all_entries:
            method = entry.get("method", "GET").upper()
            path = self._normalize_path(entry.get("path", ""))
            if not path:
                continue

            key = f"{method} {path}"
            if key not in seen:
                seen[key] = EndpointSpec(
                    method=method,
                    path=path,
                    summary=f"UI captured: {method} {path}",
                    parameters=self._extract_params(entry),
                    request_body=self._extract_body(entry),
                    responses={"200": {"description": "captured response"}},
                    source="ui-capture",
                )

        return list(seen.values())

    def _parse_jsonl(self, filepath: Path) -> list[dict[str, Any]]:
        """解析 JSONL 文件。"""
        entries = []
        try:
            for line in filepath.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        except OSError:
            pass
        return entries

    @staticmethod
    def _normalize_path(path: str) -> str:
        """规范化路径：去掉 query string，确保以 / 开头。"""
        p = path.split("?")[0]
        if not p.startswith("/"):
            p = "/" + p
        return p

    @staticmethod
    def _extract_params(entry: dict) -> list[dict[str, Any]]:
        """从捕获的 query 参数中提取参数列表。"""
        query = entry.get("query", {})
        if not isinstance(query, dict) or not query:
            return []
        params = []
        for k, v in query.items():
            params.append({
                "name": k,
                "in": "query",
                "schema": {"type": "string", "example": v},
            })
        return params

    @staticmethod
    def _extract_body(entry: dict) -> dict[str, Any] | None:
        """从捕获的 body 构造 requestBody。"""
        body = entry.get("body")
        if not body:
            return None
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                return {"content": {"text/plain": {"schema": {"type": "string"}}}}
        if isinstance(body, dict):
            return {
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                k: {"type": "string", "example": v}
                                for k, v in body.items()
                            },
                        }
                    }
                }
            }
        return None
