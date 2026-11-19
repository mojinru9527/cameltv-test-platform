"""V16-014 验收：A5 Change Impact 证据化与 UNKNOWN 语义。"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.aiqe.services.change_impact import ImpactError, analyze_change_impact

BASE = "a" * 40
HEAD = "b" * 40


def _diff(file: str, added: list[str]) -> str:
    lines = [
        f"diff --git a/{file} b/{file}",
        f"--- a/{file}",
        f"+++ b/{file}",
        "@@ -1,1 +1,10 @@",
        "-old",
    ]
    lines.extend(f"+{line}" for line in added)
    return "\n".join(lines) + "\n"


def test_route_and_permission_change_has_structural_evidence():
    result = analyze_change_impact(
        base_sha=BASE,
        head_sha=HEAD,
        changed_files=["app/api/orders.py"],
        diff_text=_diff(
            "app/api/orders.py",
            [
                '@router.post("/orders")',
                "def create_order():",
                '    require_permission("order:create")',
            ],
        ),
    )
    assert result["status"] == "OK"
    assert any(item["kind"] == "route" and item["detail"] == "/orders" for item in result["evidence"])
    assert any(item["kind"] == "symbol" and item["detail"] == "create_order" for item in result["evidence"])
    assert result["classifications"]["CONTRACT"]
    assert result["classifications"]["RISK"]
    assert result["impacted_areas"] == ["api", "auth"]
    assert result["forced_suites"] == ["auth-suite", "smoke-suite"]


def test_migration_change_is_data_evidence():
    result = analyze_change_impact(
        base_sha=BASE,
        head_sha=HEAD,
        changed_files=["alembic/versions/123_add_status.py"],
        diff_text=_diff(
            "alembic/versions/123_add_status.py",
            ['    op.add_column("orders", sa.Column("status", sa.String()))'],
        ),
    )
    assert result["status"] == "OK"
    assert result["classifications"]["DATA"] == ["alembic/versions/123_add_status.py:orders"]
    assert "data" in result["impacted_areas"]


def test_ui_route_change_classified():
    result = analyze_change_impact(
        base_sha=BASE,
        head_sha=HEAD,
        changed_files=["frontend/src/pages/live.tsx"],
        diff_text=_diff("frontend/src/pages/live.tsx", ['const path = "/live/room/123";']),
    )
    assert result["status"] == "OK"
    assert result["classifications"]["UI"] == ["frontend/src/pages/live.tsx:/live/room/123"]
    assert "ui" in result["impacted_areas"]


def test_unsupported_file_forces_unknown_and_broad_regression():
    result = analyze_change_impact(
        base_sha=BASE,
        head_sha=HEAD,
        changed_files=["proto/orders.proto"],
        diff_text=_diff("proto/orders.proto", ["message Order {}"]),
    )
    assert result["status"] == "UNKNOWN"
    assert result["reason"].startswith("UNSUPPORTED_FILE_TYPES")
    assert result["broad_regression_required"] is True
    assert {"auth-suite", "api-suite", "ui-suite", "data-suite", "smoke-suite"}.issubset(
        set(result["candidate_suites"])
    )


def test_missing_diff_is_unknown_not_no_impact():
    result = analyze_change_impact(
        base_sha=BASE,
        head_sha=HEAD,
        changed_files=["app/api/orders.py"],
        diff_text="",
    )
    assert result["status"] == "UNKNOWN"
    assert result["reason"] == "NO_DIFF_BASELINE"
    assert result["broad_regression_required"] is True


def test_invalid_shas_and_empty_files_rejected():
    with pytest.raises(ImpactError):
        analyze_change_impact(base_sha="abc", head_sha=HEAD, changed_files=["a.py"])
    with pytest.raises(ImpactError):
        analyze_change_impact(base_sha=BASE, head_sha=BASE, changed_files=["a.py"])
    with pytest.raises(ImpactError):
        analyze_change_impact(base_sha=BASE, head_sha=HEAD, changed_files=[])


def test_checksum_is_deterministic_and_versioned():
    kwargs = dict(
        base_sha=BASE,
        head_sha=HEAD,
        changed_files=["app/api/orders.py"],
        diff_text=_diff("app/api/orders.py", ['@router.get("/health")']),
    )
    first = analyze_change_impact(**kwargs)
    second = analyze_change_impact(**kwargs)
    assert first["checksum"] == second["checksum"]
    assert first["algorithm_version"] == "V16-014.1"
    assert first["rule_version"] == "V16-014.1"
    assert first["diff_hash"].startswith("sha256:")
    changed = analyze_change_impact(
        **{**kwargs, "diff_text": _diff("app/api/orders.py", ['@router.get("/other")'])}
    )
    assert changed["checksum"] != first["checksum"]


def test_transitive_dependency_evidence(tmp_path: Path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    (tmp_path / "pkg" / "b.py").write_text("from pkg.a import f\n", encoding="utf-8")
    result = analyze_change_impact(
        base_sha=BASE,
        head_sha=HEAD,
        changed_files=["pkg/a.py"],
        diff_text=_diff("pkg/a.py", ["def f():", "    return 2"]),
        repo_root=tmp_path,
    )
    assert any(
        item["kind"] == "dependency" and item["file"] == "pkg/b.py"
        for item in result["evidence"]
    )
    assert result["classifications"]["TRANSITIVE"] == ["pkg/b.py"]
