"""M5 / TA-029：A5 Change Impact Agent（13 号 §19 TA-029）。

PR diff → 候选回归并集（强制 suite 不得漏选）：
- 公共权限/登录（auth/login/permission/rbac/token/session）变化 → 强制 auth + smoke；
- 其它域按文件路径归类（live/payment/admin/api…）；
- 无命中 → 默认 smoke（保守）。
"""
from __future__ import annotations

import re

from pydantic import BaseModel, Field, ValidationError

from app.aiqe.agents.base import AgentSchemaError, BaseAgent

AREA_RULES: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    (
        "auth",
        ("auth", "login", "permission", "rbac", "token", "session"),
        ("auth-suite", "smoke-suite"),
    ),
    ("payment", ("payment", "order", "billing"), ("payment-suite", "smoke-suite")),
    ("live", ("live", "stream", "player", "room"), ("live-suite",)),
    ("admin", ("admin", "console"), ("admin-suite",)),
    ("api", ("api/", "schemas/"), ("api-suite",)),
)
FORCED_AREAS = frozenset({"auth"})
DEFAULT_SUITES = ("smoke-suite",)


def _normalize(files: list[str]) -> list[str]:
    return [re.sub(r"\\", "/", str(path)).lower() for path in files]


def compute_impact(files: list[str]) -> dict:
    paths = _normalize(files)
    areas: list[str] = []
    suites: list[str] = []
    forced: list[str] = []
    for area, needles, area_suites in AREA_RULES:
        if any(needle in path for path in paths for needle in needles):
            areas.append(area)
            suites.extend(area_suites)
            if area in FORCED_AREAS:
                forced.extend(area_suites)
    if not areas:
        areas = ["unknown"]
        suites = list(DEFAULT_SUITES)
    return {
        "impacted_areas": sorted(set(areas)),
        "candidate_suites": sorted(set(suites)),
        "forced_suites": sorted(set(forced)),
    }


class ChangeImpactResult(BaseModel):
    impacted_areas: list[str] = Field(min_length=1)
    candidate_suites: list[str] = Field(min_length=1)
    forced_suites: list[str] = Field(default_factory=list)
    rationale: str = ""


class ChangeImpactAgent(BaseAgent):
    key = "A5"
    model = "deepseek-chat"
    system_prompt = (
        "你是变更影响分析 Agent。基于 PR diff 文件列表输出严格 JSON："
        '{"impacted_areas":[str],"candidate_suites":[str],"forced_suites":[str],"rationale":str}。'
        "公共权限/登录变化必须包含 auth-suite 与 smoke-suite；不得漏选强制 suite。"
    )

    def __init__(self, llm, *, model: str | None = None) -> None:
        super().__init__(llm, model=model)
        self._expected: dict | None = None

    def analyze(self, files: list[str]) -> dict:
        if not files:
            raise AgentSchemaError("PR diff 文件列表不能为空")
        self._expected = compute_impact(files)
        return self.run(str({"files": files, "rule_baseline": self._expected}))

    def validate(self, data: dict) -> dict:
        try:
            result = ChangeImpactResult.model_validate(data)
        except ValidationError as exc:
            raise AgentSchemaError(f"变更影响 schema 校验失败: {exc}") from exc

        expected = self._expected or {}
        forced = set(expected.get("forced_suites") or [])
        if not forced.issubset(result.forced_suites):
            raise AgentSchemaError(f"漏选强制 suite: {sorted(forced - set(result.forced_suites))}")
        if not forced.issubset(result.candidate_suites):
            raise AgentSchemaError("候选回归并集必须包含强制 suite")
        if not set(expected.get("impacted_areas") or []).issubset(result.impacted_areas):
            raise AgentSchemaError("公共权限/登录变化不得漏选影响域")
        return result.model_dump()
