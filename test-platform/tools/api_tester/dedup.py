"""接口去重器：按 (method, path) 去重，swagger 版优先。

去重规则（文档 §4 已确认）:
  - 同一 (method, path) 的接口，swagger 版本保留
  - UI 捕获版本仅在 swagger 未覆盖时作为补充
  - 去重结果记录日志，含冲突信息
"""
from __future__ import annotations

from tools.api_tester.swagger_parser import EndpointSpec


class Dedup:
    """按 (method, path) 去重，swagger 优先。"""

    def deduplicate(
        self,
        new_endpoints: list[EndpointSpec],
        existing_dir: str = "",
    ) -> list[EndpointSpec]:
        """
        去重逻辑：
          1. 构建现有 (method, path) 集合（从已有文件或传入列表）
          2. 对新接口去重：移除已存在的
          3. 按来源排序：swagger 在前，ui-capture 在后
          4. 相同 (method, path) 的冲突 → swagger 保留
        """
        seen: dict[str, EndpointSpec] = {}

        for ep in new_endpoints:
            key = self._make_key(ep)
            if key in seen:
                existing = seen[key]
                # swagger 版优先
                if ep.source == "swagger" and existing.source != "swagger":
                    seen[key] = ep
                # 如果两个都是 swagger 或两个都是 ui-capture，保留先来的
            else:
                seen[key] = ep

        return sorted(seen.values(), key=lambda e: (0 if e.source == "swagger" else 1, e.path))

    def get_conflicts(
        self,
        swagger_endpoints: list[EndpointSpec],
        capture_endpoints: list[EndpointSpec],
    ) -> list[dict]:
        """检查 swagger 和 UI 捕获之间的冲突（相同 key 的接口）。"""
        swagger_map = {self._make_key(e): e for e in swagger_endpoints}
        conflicts = []
        for ep in capture_endpoints:
            key = self._make_key(ep)
            if key in swagger_map:
                conflicts.append({
                    "key": key,
                    "swagger": swagger_map[key].summary,
                    "ui_capture": ep.summary,
                    "resolved": "swagger",
                })
        return conflicts

    @staticmethod
    def _make_key(ep: EndpointSpec) -> str:
        return f"{ep.method.upper()} {ep.path}"
