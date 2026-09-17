"""C249-7：控制面镜像必须把 app 依赖的本地模块全部拷进去。

历史事故（Batch 249）：Dockerfile 显式列举 COPY 文件，新增的 ``migrations.py``
没被拷进镜像 → 控制面 import 失败起不来（"恢复平面"自锁，只能靠 SSH 救）。
本测试按 **import 图**校验覆盖，因此无论 Dockerfile 用通配还是显式列表都能守住。
"""
import ast
import fnmatch
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "Dockerfile"
ENTRYPOINT = "app"


def copy_sources(dockerfile_text: str) -> list[str]:
    """Return the source paths of every ``COPY`` instruction in the Dockerfile."""
    sources: list[str] = []
    for raw in dockerfile_text.splitlines():
        line = raw.strip()
        if not line.upper().startswith("COPY"):
            continue
        parts = [p for p in line.split()[1:] if not p.startswith("--")]
        if len(parts) >= 2:  # 最后一个参数是目标路径
            sources.extend(parts[:-1])
    return sources


def local_imports(path: pathlib.Path) -> set[str]:
    """Top-level module names imported by ``path`` (level == 0 的相对导入忽略)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names.add(node.module.split(".")[0])
    return names


def reachable_modules(root: pathlib.Path, entrypoint: str) -> set[str]:
    """BFS over the local import graph starting at ``entrypoint``."""
    local = {p.stem for p in root.glob("*.py")}
    needed, frontier = set(), [entrypoint]
    while frontier:
        name = frontier.pop()
        if name in needed:
            continue
        needed.add(name)
        path = root / f"{name}.py"
        if path.exists():
            frontier.extend(local_imports(path) & local)
    return needed


class DockerfileCopyGuardTests(unittest.TestCase):
    def test_every_module_reachable_from_app_is_copied(self):
        patterns = copy_sources(DOCKERFILE.read_text(encoding="utf-8"))
        self.assertTrue(patterns, "Dockerfile 里没有可识别的 COPY 指令")

        missing = [
            f"{name}.py"
            for name in sorted(reachable_modules(ROOT, ENTRYPOINT))
            if not any(fnmatch.fnmatch(f"{name}.py", pattern) for pattern in patterns)
        ]
        self.assertEqual(missing, [], f"这些模块没进镜像（控制面会 import 失败）：{missing}")

    def test_guard_would_catch_the_batch249_incident(self):
        """把 COPY 换回 Batch 249 的显式列表，守卫必须报出 migrations.py。"""
        regressed = "COPY app.py tencent_executor.py capacity.py release_artifacts.py ./"
        patterns = copy_sources(regressed)
        missing = [
            f"{name}.py"
            for name in sorted(reachable_modules(ROOT, ENTRYPOINT))
            if not any(fnmatch.fnmatch(f"{name}.py", pattern) for pattern in patterns)
        ]
        self.assertIn("migrations.py", missing)


if __name__ == "__main__":
    unittest.main()
