"""Tests for test-case-design skill context loading (Batch 124).

Verifies the authoritative output requirements are wired into the system prompt:
- functional kind loads 功能测试输出用例要求.md (7 份功能用例文档)
- api kind loads 接口测试输出用例要求.md (接口测试.xmind)
Both still include SKILL.md.
"""
from __future__ import annotations

from pathlib import Path

from app.services import ai_service


def _make_skill_dir(tmp_path: Path) -> Path:
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# SKILL.md\n核心原则", encoding="utf-8")
    (skill_dir / "case-template.md").write_text("# 模板\n用例编号", encoding="utf-8")
    (skill_dir / "functional-checklist.md").write_text("# 功能检查点 v2\n主结构", encoding="utf-8")
    (skill_dir / "api-checklist.md").write_text("# 接口检查点 v2\n五分类", encoding="utf-8")
    return skill_dir


def _make_standards_dir(tmp_path: Path) -> Path:
    # ai_service 的 standards_dir = workspace_root / "tests" / "test-case-standards"
    standards = tmp_path / "tests" / "test-case-standards"
    standards.mkdir(parents=True)
    (standards / "功能测试输出用例要求.md").write_text(
        "# 功能测试输出用例要求（重新整理版）\n深度用例补充层", encoding="utf-8"
    )
    (standards / "接口测试输出用例要求.md").write_text(
        "# 接口测试输出用例要求（重新整理版）\n五分类框架", encoding="utf-8"
    )
    (standards / "接口测试考虑点【辅助作用】.md").write_text(
        "# 接口测试考虑点【辅助作用】\n辅助", encoding="utf-8"
    )
    return standards


def test_functional_kind_loads_authoritative_requirements(monkeypatch, tmp_path):
    skill_dir = _make_skill_dir(tmp_path)
    _make_standards_dir(tmp_path)

    monkeypatch.setattr(ai_service, "_skill_dir", lambda: skill_dir)
    monkeypatch.setattr(ai_service, "_resolve_workspace_root", lambda: tmp_path)

    ctx = ai_service._load_skill_context_for("functional")

    assert "功能测试输出用例要求（重新整理版）" in ctx
    assert "深度用例补充层" in ctx
    assert "核心原则" in ctx
    assert "功能检查点 v2" in ctx


def test_api_kind_loads_authoritative_requirements(monkeypatch, tmp_path):
    skill_dir = _make_skill_dir(tmp_path)
    _make_standards_dir(tmp_path)

    monkeypatch.setattr(ai_service, "_skill_dir", lambda: skill_dir)
    monkeypatch.setattr(ai_service, "_resolve_workspace_root", lambda: tmp_path)

    ctx = ai_service._load_skill_context_for("api")

    assert "接口测试输出用例要求（重新整理版）" in ctx
    assert "五分类框架" in ctx
    assert "接口检查点 v2" in ctx
    assert "核心原则" in ctx


def test_skill_dir_preferred_over_standards_fallback(monkeypatch, tmp_path):
    skill_dir = _make_skill_dir(tmp_path)
    _make_standards_dir(tmp_path)
    # 权威文件同时放 skill 目录（优先）与规范中心
    (skill_dir / "功能测试输出用例要求.md").write_text(
        "# 功能测试输出用例要求（skill 内）", encoding="utf-8"
    )
    (skill_dir / "接口测试输出用例要求.md").write_text(
        "# 接口测试输出用例要求（skill 内）", encoding="utf-8"
    )

    monkeypatch.setattr(ai_service, "_skill_dir", lambda: skill_dir)
    monkeypatch.setattr(ai_service, "_resolve_workspace_root", lambda: tmp_path)

    fctx = ai_service._load_skill_context_for("functional")
    actx = ai_service._load_skill_context_for("api")

    assert "（skill 内）" in fctx
    assert "（skill 内）" in actx
    assert "功能测试输出用例要求（重新整理版）" not in fctx
