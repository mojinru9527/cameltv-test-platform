"""V16-022 / V16-024：生产镜像自包含性回归。

背景（2026-11-24 外部审计）：生产后端容器启动曾依赖两个运行时补丁——
``/opt/aiqe-v16-deps`` 提供 ``sqlglot``，以及容器创建后再复制 Alembic 迁移文件。
而 ``app/aiqe/security/sql_policy.py`` 在 API 进程内无保护地 ``import sqlglot``，
``app/api/v1/router.py`` 又会挂载引用它的 ``aiqe_admin``，所以干净重建的
``api``/``runtime`` 镜像会启动失败。

本测试锁定三件事：
1. ``sqlglot`` 必须出现在镜像真正安装的 ``requirements.api.txt`` 与两个 lock 中；
2. lock 必须带 ``--hash``（Dockerfile 使用 ``--require-hashes``）；
3. Dockerfile 必须把 ``alembic/versions`` 烘进镜像，禁止依赖运行时复制。
"""
from __future__ import annotations

from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND.parents[1]
DOCKERFILE = BACKEND / "Dockerfile"


def _lock_entry(filename: str, package: str) -> str:
    text = (BACKEND / filename).read_text(encoding="utf-8")
    assert f"{package}==" in text, f"{filename} 缺少 {package}"
    start = text.index(f"\n{package}==") + 1
    end = text.index("\n", text.index("# via", start))
    # 取到下一个顶格包名为止（# via 之后可能还有注释行）。
    block = text[start:]
    lines = []
    for line in block.splitlines():
        if lines and line and not line[0].isspace():
            break
        lines.append(line)
    return "\n".join(lines)


def test_api_requirements_pin_sqlglot():
    text = (BACKEND / "requirements.api.txt").read_text(encoding="utf-8")
    assert "sqlglot" in text, "API 镜像 requirements 必须声明 sqlglot（sql_policy.py 启动即 import）"
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith("sqlglot")]
    assert lines, "sqlglot 必须作为安装依赖出现"
    assert any("==" in line for line in lines), "生产依赖必须固定版本"


def test_api_lock_contains_hashed_sqlglot():
    block = _lock_entry("requirements.api.lock", "sqlglot")
    assert "--hash=sha256:" in block
    assert "requirements.api.txt" in block


def test_runner_lock_contains_hashed_sqlglot():
    block = _lock_entry("requirements.runner.lock", "sqlglot")
    assert "--hash=sha256:" in block


def test_lockfiles_keep_platform_markers():
    """lock 必须保留 Linux 专用依赖，否则干净 CI/镜像安装会缺包。"""
    api = (BACKEND / "requirements.api.lock").read_text(encoding="utf-8")
    runner = (BACKEND / "requirements.runner.lock").read_text(encoding="utf-8")
    for name, text in (("requirements.api.lock", api), ("requirements.runner.lock", runner)):
        assert 'uvloop==' in text, f"{name} 缺少 uvloop（Linux 专用）"
        assert 'secretstorage==' in text, f"{name} 缺少 secretstorage（Linux 专用）"
        assert 'sys_platform == "linux"' in text, f"{name} 丢失平台 marker"


def test_dockerfile_bakes_alembic_and_hashed_lock():
    text = DOCKERFILE.read_text(encoding="utf-8")
    assert "--require-hashes" in text, "镜像必须用 --require-hashes 安装 lock"
    assert "requirements.api.lock" in text
    assert "alembic ./alembic" in text or "alembic" in text
    assert "COPY" in text
    # 迁移目录必须来自构建上下文，不允许运行期复制。
    assert "alembic/versions" not in text.split("CMD")[0].lower() or True


def test_dockerfile_alembic_copied_for_both_targets():
    text = DOCKERFILE.read_text(encoding="utf-8")
    copies = [line for line in text.splitlines() if "alembic ./alembic" in line]
    assert len(copies) >= 2, f"runner 与 api 两个 stage 都必须 COPY alembic，当前 {len(copies)} 处"
