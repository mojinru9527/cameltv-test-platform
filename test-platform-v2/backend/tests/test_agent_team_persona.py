"""Batch 191 — 执行侧资产单测：persona 构建 + team.cordis.yml + agent-team profile 模板。"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.services.dsh.agent_team_persona import (
    _CONSTRAINTS,
    _FULL_MEMBERS,
    _LIGHT_MEMBERS,
    _STEPS,
    build_agent_team_persona,
)

_DSH_DIR = Path(__file__).resolve().parent.parent / "app" / "services" / "dsh"


class _CordisLoader(yaml.SafeLoader):
    """minimal/team cordis 含 !!js 表达式，注册构造器以便 YAML 解析。"""


def _js_constructor(loader, node):
    return loader.construct_scalar(node)


_CordisLoader.add_constructor("tag:yaml.org,2002:js", _js_constructor)


def _load_yaml(path: Path) -> list:
    with path.open(encoding="utf-8") as f:
        return yaml.load(f, Loader=_CordisLoader)


# ── persona ──

class TestBuildAgentTeamPersona:
    def test_full_members(self):
        p = build_agent_team_persona("为登录模块生成用例", "full")
        assert "为登录模块生成用例" in p  # 用户目标原文
        for name, role in _FULL_MEMBERS:
            assert f"{name}（{role}）" in p
        assert len(_FULL_MEMBERS) == 5
        assert "product" in p and "dev" in p and "qa" in p

    def test_light_members(self):
        p = build_agent_team_persona("轻量验收", "light")
        for name, role in _LIGHT_MEMBERS:
            assert f"{name}（{role}）" in p
        assert len(_LIGHT_MEMBERS) == 2
        assert "dev" not in p and "design" not in p and "pm" not in p

    def test_fixed_steps_present(self):
        """六固定步骤关键词齐备（建团队→加成员→建任务→认领→汇总→最终报告）。"""
        p = build_agent_team_persona("x", "full")
        for keyword in ("agent_teams_create", "agent_teams_add_member", "agent_teams_create_task",
                        "agent_teams_claim_task", "agent_teams_send_message", "最终报告"):
            assert keyword in p
        assert "【用户目标】" in p and "【批次模式】full" in p

    def test_constraints_present(self):
        p = build_agent_team_persona("x", "light")
        for c in _CONSTRAINTS:
            assert c in p

    def test_pure_function_no_io(self):
        """纯函数：两次调用相同输入产生相同输出（无状态）。"""
        a = build_agent_team_persona("目标", "full")
        b = build_agent_team_persona("目标", "full")
        assert a == b


# ── team.cordis.yml ──

class TestTeamCordis:
    def test_team_cordis_parses_and_extends_minimal(self):
        team = _load_yaml(_DSH_DIR / "team.cordis.yml")
        minimal = _load_yaml(_DSH_DIR / "minimal.cordis.yml")
        assert isinstance(team, list)
        assert len(team) == len(minimal) + 3, (
            "team.cordis.yml = minimal 全部行 + subagent / subagent-spawn-in-process / agent-teams "
            "3 行（C191-1：agent-teams 依赖 subagents 服务，minimal 不含提供者）"
        )
        ids = [d.get("id") for d in team]
        assert "agent-teams" in ids
        assert "subagent" in ids
        assert "subagent-spawn-in-process" in ids
        plugin = next(d for d in team if d.get("id") == "agent-teams")
        assert plugin["name"] == "@nanmicoder/dsh-agent-teams"
        assert plugin["config"]["stateDir"] == ".agent-teams"
        assert plugin["config"]["memberProvider"] == "spawn"
        spawn = next(d for d in team if d.get("id") == "subagent-spawn-in-process")
        assert spawn["name"] == "@deepseek-ai/dsh-subagent-spawn-in-process"
        assert spawn["config"]["providerName"] == "spawn"

    def test_minimal_rows_unchanged(self):
        team = _load_yaml(_DSH_DIR / "team.cordis.yml")
        minimal_ids = [d.get("id") for d in _load_yaml(_DSH_DIR / "minimal.cordis.yml")]
        team_ids = [d.get("id") for d in team]
        assert team_ids[: len(minimal_ids)] == minimal_ids


# ── agent-team profile 模板 ──

class TestAgentTeamProfileTemplate:
    def test_template_files_exist(self):
        tpl_dir = _DSH_DIR / "agent-team"
        assert (tpl_dir / "README.md").exists()
        assert (tpl_dir / "package.json.template").exists()
        assert (tpl_dir / "cordis.patch.yml.template").exists()

    def test_package_template_contains_plugin(self):
        raw = (_DSH_DIR / "agent-team" / "package.json.template").read_text(encoding="utf-8")
        assert '"@nanmicoder/dsh-agent-teams"' in raw
        assert '"@deepseek-ai/dsh-base"' in raw
        assert '"@deepseek-ai/dsh-headless"' in raw

    def test_cordis_patch_template_inserts_plugin(self):
        raw = (_DSH_DIR / "agent-team" / "cordis.patch.yml.template").read_text(encoding="utf-8")
        assert "agent-teams" in raw
        assert "@nanmicoder/dsh-agent-teams" in raw

    def test_readme_has_install_steps_and_harness_path_semantics(self):
        readme = (_DSH_DIR / "agent-team" / "README.md").read_text(encoding="utf-8")
        assert "dsh plugin --profile agent-team add @nanmicoder/dsh-agent-teams" in readme
        assert "DSH_HOME" in readme
        assert "DSH_TEAM_HARNESS_PATH" in readme
        assert "C:\\Users\\26029\\.dsh" in readme or "%USERPROFILE%" in readme
        assert "--dump-config" in readme