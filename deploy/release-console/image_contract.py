"""C249-5：沿用旧镜像 / 打补丁镜像前的**可执行**核对。

背景（Batch 248 runner 热修事故）：runner target 在本机不可构建时，发布改用
"复用已验证镜像 / 打补丁镜像"。此时镜像里的转发面（``RUNNER_ENDPOINTS``）或
``alembic/versions`` 一旦与当前配置不一致，就会出现"容器能起、任务全挂 / 迁移不可用"
的隐形故障——而这类故障在发布日志里看不出来。

这里把核对固化为纯函数（本模块）+ 一键脚本（``scripts/ops/verify-reused-image.ps1``，
在容器内跑同一个模块），保证"沿用镜像前先核对"不是一句口头 checklist。
"""
from __future__ import annotations

import ast
import json

RUNNER_ENDPOINTS_FILE = "app/core/execution_dispatch.py"
RUNNER_ENDPOINTS_NAME = "RUNNER_ENDPOINTS"

# 镜像内必须存在的路径（相对 /app）；沿用时逐项核对
REQUIRED_IMAGE_PATHS: dict[str, tuple[str, ...]] = {
    "backend": ("alembic", "alembic/versions", "alembic.ini"),
    "runner": ("alembic", "alembic/versions", "alembic.ini", RUNNER_ENDPOINTS_FILE),
    "api": ("alembic", "alembic/versions", "alembic.ini"),
    "ai-gateway": (),
}


def required_paths(part: str) -> tuple[str, ...]:
    """镜像内必须存在的路径清单；未知部件直接报错（fail-closed）。"""
    try:
        return REQUIRED_IMAGE_PATHS[part]
    except KeyError:
        raise ValueError(f"unknown image part: {part!r}") from None


def _literal(node: ast.AST) -> object:
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError) as exc:  # pragma: no cover - 由调用方转成业务异常
        raise ValueError("RUNNER_ENDPOINTS 必须是字面量，无法静态核对") from exc


def parse_runner_endpoints(source: str) -> dict[str, list[str]]:
    """AST 解析 ``RUNNER_ENDPOINTS = {module: {endpoint, ...}}``（不用正则）。"""
    for node in ast.parse(source).body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == RUNNER_ENDPOINTS_NAME for t in node.targets):
            continue
        if not isinstance(node.value, ast.Dict):
            raise ValueError(f"{RUNNER_ENDPOINTS_NAME} 不是字面量 dict")
        parsed: dict[str, list[str]] = {}
        for key, value in zip(node.value.keys, node.value.values):
            module = _literal(key)
            names = _literal(value)
            if not isinstance(module, str) or not isinstance(names, (set, list, tuple)):
                raise ValueError(f"{RUNNER_ENDPOINTS_NAME} 结构不符合预期：{module!r}")
            parsed[module] = sorted(str(name) for name in names)
        return parsed
    raise ValueError(f"未找到 {RUNNER_ENDPOINTS_NAME} 定义")


def contract_diff(
    repo_contract: dict[str, list[str]], image_contract: dict[str, list[str]]
) -> dict[str, list[str]]:
    """返回**镜像缺失**的转发面：module -> 缺失的 endpoint 名。"""
    missing: dict[str, list[str]] = {}
    for module, endpoints in repo_contract.items():
        have = set(image_contract.get(module, ()))
        gaps = sorted(set(endpoints) - have)
        if gaps:
            missing[module] = gaps
    return missing


def verify_image(
    *,
    root: str,
    part: str,
    repo_source: str,
    exists: dict[str, bool] | None = None,
    image_source: str | None = None,
) -> dict:
    """核对报告（在容器内执行时只传前三个参数，其余由容器自行探测）。"""
    if exists is None or image_source is None:  # pragma: no cover - 容器内路径
        raise ValueError("exists/image_source 必须由容器内探测提供")
    missing_paths = [path for path in required_paths(part) if not exists.get(path)]
    image_contract: dict[str, list[str]] = {}
    contract_error = None
    if image_source is not None:
        try:
            image_contract = parse_runner_endpoints(image_source)
        except ValueError as exc:
            contract_error = str(exc)
    missing_endpoints = contract_diff(parse_runner_endpoints(repo_source), image_contract)
    ok = not missing_paths and not missing_endpoints and contract_error is None
    return {
        "ok": ok,
        "part": part,
        "root": root,
        "missing_paths": missing_paths,
        "missing_endpoints": missing_endpoints,
        "contract_error": contract_error,
        "image_endpoint_modules": sorted(image_contract),
    }


def collect_image_facts(root: str, part: str) -> dict:  # pragma: no cover - 容器内执行
    """容器内探测：路径存在性 + 镜像里的 RUNNER_ENDPOINTS 源码。"""
    from pathlib import Path

    base = Path(root)
    paths = sorted({p for paths in REQUIRED_IMAGE_PATHS.values() for p in paths})
    module = base / RUNNER_ENDPOINTS_FILE
    return {
        "exists": {path: (base / path).exists() for path in paths},
        "image_source": module.read_text(encoding="utf-8") if module.exists() else None,
    }


def probe_script(*, root: str, part: str, repo_source: str) -> str:  # pragma: no cover - 由脚本调用
    """生成容器内执行的自包含脚本（供 ``docker run -i … python -`` 使用）。"""
    import base64
    from pathlib import Path

    module_b64 = base64.b64encode(Path(__file__).read_bytes()).decode("ascii")
    payload = json.dumps({"root": root, "part": part, "repo_source": repo_source})
    payload_b64 = base64.b64encode(payload.encode("utf-8")).decode("ascii")
    return (
        "import base64, json\n"
        f"ns = {{'__name__': 'image_contract_probe'}}\n"
        f"exec(base64.b64decode('{module_b64}'), ns)\n"
        f"payload = json.loads(base64.b64decode('{payload_b64}').decode('utf-8'))\n"
        "facts = ns['collect_image_facts'](payload['root'], payload['part'])\n"
        "report = ns['verify_image'](root=payload['root'], part=payload['part'],\n"
        "                            repo_source=payload['repo_source'], **facts)\n"
        "print(json.dumps(report))\n"
    )
