"""FastAPI 依赖注入：?env=test|prod → RunContext。"""
from __future__ import annotations

from core import config_loader as cl
from core.models import RunContext


def get_context(env: str = "test") -> RunContext:
    """通过 v2 路径构建 RunContext（project + environment）。"""
    return cl.build_context_v2(env)


def get_available_environments() -> list[str]:
    return cl.list_environments_v2()
