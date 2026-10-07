"""前端 API 契约对账（只读，按需运行）。

后端某批把模块删除或改为只读后，前端若仍声明调用这些端点，页面在运行时
会拿到 404/405（typecheck 抓不到，因为它只检查模块是否存在）。

做法：从 `frontend/src/api/*.ts` 抽取请求路径，与后端路由基线
（`backend/tests/fixtures/route_inventory.json`）逐条比对（含方法）。

用法（任意 cwd）：
    python scripts/ci/check_frontend_api_contract.py
退出码 0 = 全部匹配；1 = 存在失效端点（附文件:行号）。基线过期时先重建：
    python -m pytest test-platform-v2/backend/tests/test_route_inventory.py 会提示漂移。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_API = REPO_ROOT / "test-platform-v2/frontend/src/api"
INVENTORY = REPO_ROOT / "test-platform-v2/backend/tests/fixtures/route_inventory.json"

# 形如 http.get(`/foo/${id}/bar?x=1`) / api.post('/foo', ...) / request('GET', '/foo')
CALL = re.compile(
    r"""\.(get|post|put|patch|delete)\(\s*[`'"]([^`'"]+)[`'"]""",
    re.IGNORECASE,
)
# 直接使用 http 客户端的其它写法：http('GET', '/x') / request('POST', '/x')
CALL_ALT = re.compile(
    r"""(?:request|http|client)\(\s*['"](GET|POST|PUT|PATCH|DELETE)['"]\s*,\s*[`'"]([^`'"]+)[`'"]""",
    re.IGNORECASE,
)
SKIP_PREFIX = ("http://", "https://", "/internal/", "/assets/", "/health")


def normalize(raw: str) -> str | None:
    path = raw.split("?")[0].strip()
    if not path.startswith("/") or path.startswith(SKIP_PREFIX):
        return None
    # 模板占位 `${...}` → 单段通配
    path = re.sub(r"\$\{[^}]+\}", ":param", path)
    path = re.sub(r"/+$", "", path) or "/"
    return path


def strip_api_prefix(path: str) -> str:
    """前端路径相对 baseURL（/api/v1），后端路径含前缀——统一去掉后比较。"""
    return re.sub(r"^/api/v\d+", "", path) or "/"


def matches(front: str, backend: str) -> bool:
    front_parts = [p for p in front.split("/") if p]
    back_parts = [p for p in backend.split("/") if p]
    if len(front_parts) != len(back_parts):
        return False
    for f, b in zip(front_parts, back_parts):
        if f == ":param":
            continue
        if b.startswith("{") and b.endswith("}"):
            continue
        if f != b:
            return False
    return True


def main() -> int:
    spec = json.loads(INVENTORY.read_text(encoding="utf-8"))
    routes = [(strip_api_prefix(r["path"]), r["method"].upper()) for r in spec["routes"]]

    calls: list[tuple[str, int, str, str]] = []
    for path in sorted(FRONTEND_API.glob("*.ts")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith(("//", "*", "/*")):
                continue
            for regex in (CALL, CALL_ALT):
                for match in regex.finditer(line):
                    method, raw = match.group(1).upper(), match.group(2)
                    normalized = normalize(raw)
                    if normalized:
                        calls.append((path.name, lineno, method, normalized))

    unmatched: list[str] = []
    for name, lineno, method, path in calls:
        if not any(m == method and matches(path, b) for b, m in routes):
            # 允许方法不匹配但路径存在（如后端 POST 改 GET）——单独标注
            paths_only = [b for b, _ in routes if matches(path, b)]
            if paths_only:
                unmatched.append(
                    f"{name}:{lineno} {method} {path} → 路径存在但方法不匹配（后端: "
                    f"{sorted({m for b, m in routes if b in paths_only})}）"
                )
            else:
                unmatched.append(f"{name}:{lineno} {method} {path} → 后端已无此路径")

    print(f"前端 api/*.ts 请求点 {len(calls)} 个；后端路由基线 {len(routes)} 条")
    if unmatched:
        for line in unmatched:
            print("FAIL", line)
    else:
        print("OK   所有前端请求点都能在后端路由基线中匹配到（含方法）")
    print("FRONTEND_API_CONTRACT=" + ("FAIL" if unmatched else "PASS"))
    return 1 if unmatched else 0


if __name__ == "__main__":
    raise SystemExit(main())

