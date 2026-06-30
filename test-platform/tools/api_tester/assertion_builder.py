"""断言代码生成器：根据 EndpointSpec 生成 Playwright 测试断言。

生成的断言覆盖:
  - 状态码校验
  - JSON 字段存在性校验
  - Schema 类型校验
  - DB/Redis 副作用断言（可选，通过 sidecar 端点）
"""
from __future__ import annotations

from tools.api_tester.swagger_parser import EndpointSpec


class AssertionBuilder:
    """根据接口定义生成 Playwright 断言代码块。"""

    def build(self, endpoint: EndpointSpec) -> str:
        """为单个接口生成完整的断言代码块。"""
        lines: list[str] = []

        # 1. 状态码断言
        expected_status = self._get_expected_status(endpoint)
        lines.append(f"  // 状态码校验")
        lines.append(f"  expect(response.status()).toBe({expected_status});")
        lines.append("")

        # 2. 成功时 JSON 字段断言
        if expected_status == 200:
            lines.append(f"  const body = await response.json();")
            lines.append(f"  // 返回值校验")

            # 从 responses 推断期望字段
            expected_fields = self._extract_fields_from_responses(endpoint)
            if expected_fields:
                for field in expected_fields:
                    lines.append(f"  expect(body).toHaveProperty('{field}');")
            else:
                # 通用检查
                lines.append(f"  expect(body).toBeDefined();")
                lines.append(f"  // TODO: 补充业务字段断言（从 swagger responses schema 生成）")

            lines.append("")

        # 3. Schema 校验（如果有 schema 定义）
        schema_block = self._build_schema_check(endpoint)
        if schema_block:
            lines.append(f"  // Schema 校验")
            lines.append(schema_block)
            lines.append("")

        # 4. DB 校验占位（需要额外配置）
        lines.append(f"  // DB/Redis 校验：调用 sidecar 验证数据落库")
        lines.append(f"  // const dbCheck = await request.get('/api/_test/verify-{endpoint.tags[0] if endpoint.tags else 'db'}');")
        lines.append(f"  // expect(dbCheck.status()).toBe(200);")

        return "\n".join(lines)

    def _get_expected_status(self, endpoint: EndpointSpec) -> int:
        """推断期望的 HTTP 状态码。"""
        for status_str in endpoint.responses:
            try:
                return int(status_str)
            except ValueError:
                continue
        return 200  # 默认 200

    def _extract_fields_from_responses(self, endpoint: EndpointSpec) -> list[str]:
        """从 OpenAPI responses 中提取字段名。"""
        fields = []
        for status_str, resp_detail in endpoint.responses.items():
            if not status_str.startswith("2"):
                continue
            if not isinstance(resp_detail, dict):
                continue
            content = resp_detail.get("content", {})
            json_schema = content.get("application/json", {})
            schema = json_schema.get("schema", {})
            props = schema.get("properties", {})
            if isinstance(props, dict):
                fields.extend(props.keys())
            break  # 只用第一个 2xx response
        return fields[:10]  # 最多 10 个字段

    def _build_schema_check(self, endpoint: EndpointSpec) -> str:
        """生成 JSON Schema 校验代码（使用 zod）。"""
        # 简化版：不生成完整 schema，只做类型检查占位
        fields = self._extract_fields_from_responses(endpoint)
        if not fields:
            return ""
        # 仅校验字段存在性，不臆断类型（避免生成的断言因类型猜错而误报失败）
        checks = []
        for f in fields[:5]:
            checks.append(f"  expect(body.{f}).toBeDefined();  // TODO: 按 swagger schema 补类型断言")
        return "\n".join(checks)
