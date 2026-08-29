"""SourceRef validation tests (v331-remediation-2 C2 / V30-124 + V30-082).

Invalid Source Ref Acceptance = 0：golden 语料中 artifact_id>0 的引用必须可解
析到真实 SourceArtifact（否则语料自身就是脏的）；占位（<=0）语义按
``ai_ops.validate_source_refs`` 视为待补占位并跳过。
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base
from app.modules.aitde import mission as mission_pkg  # noqa: F401 registers models
from app.modules.aitde import sources as sources_pkg  # noqa: F401 registers models
from app.modules.aitde.ai_ops import service as ai_ops
from app.modules.aitde.sources.models import SourceArtifact

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "aitde" / "v3"
MANIFEST = json.loads((FIXTURE_DIR / "manifest.json").read_text(encoding="utf-8"))


def _db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _seed_artifacts(session, artifact_ids: set[int]) -> None:
    for aid in sorted(artifact_ids):
        session.add(SourceArtifact(id=aid, project_id=1, source_type="REQUIREMENT", name=f"a{aid}"))
    session.commit()


def _collect_positive_refs(node, acc: set[int]) -> None:
    if isinstance(node, dict):
        if "artifact_id" in node and isinstance(node["artifact_id"], int) and node["artifact_id"] > 0:
            acc.add(node["artifact_id"])
        for v in node.values():
            _collect_positive_refs(v, acc)
    elif isinstance(node, list):
        for v in node:
            _collect_positive_refs(v, acc)


def test_golden_source_refs_resolve_or_are_placeholders():
    """Golden 语料的引用全部可解析或为显式占位 → Invalid Source Ref Acceptance = 0。"""
    session = _db()
    positive: set[int] = set()
    for entry in MANIFEST["valid"]:
        payload = json.loads((FIXTURE_DIR / entry["file"]).read_text(encoding="utf-8"))
        _collect_positive_refs(payload, positive)
    _seed_artifacts(session, positive)
    for entry in MANIFEST["valid"]:
        payload = json.loads((FIXTURE_DIR / entry["file"]).read_text(encoding="utf-8"))
        # validate_source_refs 返回违规列表；占位(<=0)被跳过，正数必须存在
        assert ai_ops.validate_source_refs(session, _refs_of(payload)) == []


def test_invalid_fake_fragment_id_is_rejected():
    """invalid/fake_fragment_id：artifact 99999 不存在 → 必须被判违规。"""
    assert run_fake_fragment_scenario() == ["artifact_id=99999"]


def run_fake_fragment_scenario() -> list[str]:
    """Shared scenario (also used by test_ai_schema_validation's guard dispatch)."""
    session = _db()
    _seed_artifacts(session, {1})
    payload = json.loads(
        (FIXTURE_DIR / "invalid" / "fake_fragment_id.json").read_text(encoding="utf-8")
    )
    return ai_ops.validate_source_refs(session, _refs_of(payload))


def _refs_of(payload: dict) -> list[dict]:
    """从 payload 递归收集所有 source_refs 条目。"""
    refs: list[dict] = []

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "source_refs" and isinstance(v, list):
                    refs.extend(v)
                else:
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(payload)
    return refs
