"""交互增强层运行时接入守卫（cameltv-qa-skill-pack v1.1.0 适配）。

证明「复制 Skill 文件」之外，生成链路真实加载了增强层：
- functional: interaction-checklist.md + bug-pattern-digest.md
- api: api-interaction-checklist.md + bug-pattern-digest.md
并证明仓库内真实 Skill 资产存在且缺陷模式库符合 schema 与覆盖判定口径。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services import ai_service

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL_DIR = REPO_ROOT / ".claude" / "skills" / "test-case-design"
AUGMENTER_DIR = REPO_ROOT / ".claude" / "skills" / "interaction-case-augmenter"
REF_DIR = AUGMENTER_DIR / "references"


def _make_dirs(tmp_path: Path) -> tuple[Path, Path]:
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# SKILL\n核心原则", encoding="utf-8")
    (skill_dir / "case-template.md").write_text("# 模板", encoding="utf-8")
    (skill_dir / "functional-checklist.md").write_text("# 功能检查点", encoding="utf-8")
    (skill_dir / "api-checklist.md").write_text("# 接口检查点", encoding="utf-8")
    (skill_dir / "interaction-checklist.md").write_text("# 交互增强清单\nCOVERED_PARTIAL", encoding="utf-8")
    (skill_dir / "api-interaction-checklist.md").write_text("# 接口交互增强清单\nBP-021", encoding="utf-8")
    (skill_dir / "bug-pattern-digest.md").write_text("# 历史缺陷模式摘要\nCAMEL-BP-001", encoding="utf-8")
    standards = tmp_path / "tests" / "test-case-standards"
    standards.mkdir(parents=True)
    (standards / "功能测试输出用例要求.md").write_text("# 功能输出要求", encoding="utf-8")
    (standards / "接口测试输出用例要求.md").write_text("# 接口输出要求", encoding="utf-8")
    return skill_dir, standards


def test_functional_context_includes_interaction_layer(monkeypatch, tmp_path):
    skill_dir, _ = _make_dirs(tmp_path)
    monkeypatch.setattr(ai_service, "_skill_dir", lambda: skill_dir)
    monkeypatch.setattr(ai_service, "_resolve_workspace_root", lambda: tmp_path)

    ctx = ai_service._load_skill_context_for("functional")

    assert "交互增强清单" in ctx
    assert "COVERED_PARTIAL" in ctx
    assert "历史缺陷模式摘要" in ctx
    assert "CAMEL-BP-001" in ctx


def test_api_context_includes_interaction_layer(monkeypatch, tmp_path):
    skill_dir, _ = _make_dirs(tmp_path)
    monkeypatch.setattr(ai_service, "_skill_dir", lambda: skill_dir)
    monkeypatch.setattr(ai_service, "_resolve_workspace_root", lambda: tmp_path)

    ctx = ai_service._load_skill_context_for("api")

    assert "接口交互增强清单" in ctx
    assert "BP-021" in ctx
    assert "CAMEL-BP-001" in ctx


def test_missing_interaction_files_degrade_without_crash(monkeypatch, tmp_path):
    """增强层文件缺失时只能退化，不得让生成链路报错。"""
    skill_dir, _ = _make_dirs(tmp_path)
    (skill_dir / "interaction-checklist.md").unlink()
    (skill_dir / "bug-pattern-digest.md").unlink()
    monkeypatch.setattr(ai_service, "_skill_dir", lambda: skill_dir)
    monkeypatch.setattr(ai_service, "_resolve_workspace_root", lambda: tmp_path)

    ctx = ai_service._load_skill_context_for("functional")
    assert "核心原则" in ctx  # 基座仍在
    assert "交互增强清单" not in ctx


@pytest.mark.parametrize(
    "relative",
    [
        ".claude/skills/test-case-design/interaction-checklist.md",
        ".claude/skills/test-case-design/api-interaction-checklist.md",
        ".claude/skills/test-case-design/bug-pattern-digest.md",
        ".claude/skills/interaction-case-augmenter/SKILL.md",
        ".claude/skills/interaction-case-augmenter/references/universal-interaction-checklist.md",
        ".claude/skills/interaction-case-augmenter/references/historical-bug-pattern-library.json",
        ".claude/skills/interaction-case-augmenter/references/bug-pattern-coverage.csv",
        ".claude/skills/interaction-case-augmenter/references/historical-bug-pattern.schema.json",
        ".claude/skills/bug-pattern-curator/SKILL.md",
        "tests/test-case-standards/interaction-testing/interaction-methodology.md",
        "tests/test-case-standards/interaction-testing/platform-profiles.md",
        "tests/test-case-standards/interaction-testing/role-permission-coverage.md",
        "tests/test-case-standards/interaction-testing/admin-and-consumer-interaction.md",
    ],
)
def test_repo_interaction_assets_exist(relative: str):
    path = REPO_ROOT / relative
    assert path.is_file(), f"missing interaction asset: {relative}"
    assert path.stat().st_size > 0


def test_bug_pattern_library_matches_schema_and_policy():
    """缺陷模式库必须满足 schema，且覆盖判定与动作一一对应。"""
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((REF_DIR / "historical-bug-pattern.schema.json").read_text(encoding="utf-8"))
    library = json.loads((REF_DIR / "historical-bug-pattern-library.json").read_text(encoding="utf-8"))

    patterns = library["patterns"]
    assert patterns, "bug pattern library must not be empty after real defect import"

    action_for = {
        "strong": "skip",
        "partial": "enhance-existing",
        "none": "add-minimal-case",
        "unknown": "confirm",
    }
    for pattern in patterns:
        jsonschema.validate(pattern, schema)
        assert pattern["generation_action"] == action_for[pattern["coverage_strength"]], pattern["pattern_id"]
        assert pattern["detection_point"] and pattern["trigger_signature"] and pattern["test_oracle"], pattern["pattern_id"]
        if pattern["coverage_strength"] in {"strong", "partial"}:
            assert pattern["existing_test_ids"], f"{pattern['pattern_id']} 判覆盖但无用例 ID"
        if pattern["coverage_strength"] == "none":
            assert not pattern["existing_test_ids"], f"{pattern['pattern_id']} 判无覆盖却关联了用例"

    ids = [p["pattern_id"] for p in patterns]
    assert len(ids) == len(set(ids)), "pattern_id 必须唯一"


def test_bug_pattern_digest_stays_compact():
    """摘要注入 LLM prompt，必须保持轻量，避免挤占上下文。"""
    digest = (SKILL_DIR / "bug-pattern-digest.md").read_text(encoding="utf-8")
    assert len(digest) < 16_000, f"bug-pattern-digest.md 过大: {len(digest)} chars"
    assert "CAMEL-BP-" in digest
