"""Batch 186 / C182-2：`scripts/backfill-domain-naming-b182.py` 单元测试。

覆盖：
- `normalize_domain` 映射规则与前端 `groupDomainLabel` 口径一致（平台前缀保留 /
  `体育-运营后台-*` 保留 / 裸域补前缀 / 空值不修改）+ 幂等；
- `collect_changed` 只读聚合（条数、去重值数、映射清单、软删排除）；
- `apply_changes` 写入（软删行不写、幂等、无变更短路）；
- `load_database_url` 取值优先级（环境变量 > backend/.env）+ 相对路径解析 +
  `:memory:` 不解析。

脚本模块通过 importlib 按文件加载（脚本本身不依赖 backend 包路径即可导入）。
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from app.models.test_case import TestCase as CaseORM

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "backfill-domain-naming-b182.py"
)


@pytest.fixture(scope="module")
def backfill_script():
    spec = importlib.util.spec_from_file_location(
        "backfill_domain_naming_b182", SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _seed(session, rows: list[dict]) -> None:
    for row in rows:
        session.add(CaseORM(**row))
    session.commit()


# ── normalize_domain：映射规则（与 frontend/src/utils/domainNaming.ts 对齐）──


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # 裸域 → 用户端/{裸域名}
        ("UGC", "用户端/UGC"),
        ("广告", "用户端/广告"),
        ("UGC内容管理", "用户端/UGC内容管理"),
        ("WEB-第三方社媒引导移除", "用户端/WEB-第三方社媒引导移除"),
        ("体育数据-篮球", "用户端/体育数据-篮球"),
        ("首页", "用户端/首页"),
        ("   UGC  ", "用户端/UGC"),
        # 平台前缀直接保留（平台名本身 / 斜杠 / 连字符变体）
        ("用户端", "用户端"),
        ("运营后台", "运营后台"),
        ("接口测试", "接口测试"),
        ("用户端/首页", "用户端/首页"),
        ("运营后台-热门比赛配置", "运营后台-热门比赛配置"),
        ("接口测试/登录", "接口测试/登录"),
        (" 用户端/首页 ", "用户端/首页"),
        # 体育-运营后台-* 仅展示归组，库值不修改
        ("体育-运营后台-功能", "体育-运营后台-功能"),
        ("体育-运营后台", "体育-运营后台"),
        # 空值/空白 → 不修改
        ("", ""),
        ("   ", "   "),
    ],
)
def test_normalize_domain_rules(backfill_script, raw, expected) -> None:
    assert backfill_script.normalize_domain(raw) == expected


def test_normalize_domain_idempotent(backfill_script) -> None:
    for value in [
        "用户端/UGC",
        "用户端/首页",
        "运营后台/xx",
        "运营后台-热门比赛配置",
        "接口测试",
        "体育-运营后台-功能",
    ]:
        once = backfill_script.normalize_domain(value)
        assert backfill_script.normalize_domain(once) == once


# ── collect_changed：只读聚合 ──


def test_collect_changed_mapping_and_counts(backfill_script, db_session) -> None:
    _seed(db_session, [
        {"domain": "UGC"},
        {"domain": "UGC"},
        {"domain": "广告"},
        {"domain": "用户端/首页"},
        {"domain": "运营后台-热门比赛配置"},
        {"domain": "体育-运营后台-功能"},
        {"domain": ""},
    ])
    total, distinct, changed = backfill_script.collect_changed(db_session)
    assert total == 7
    assert distinct == 6
    by_src = {src: (dst, cnt) for src, dst, cnt in changed}
    assert by_src == {"UGC": ("用户端/UGC", 2), "广告": ("用户端/广告", 1)}
    # 已归一/平台前缀/体育-运营后台/空值不得出现在映射中
    for untouched in ("用户端/首页", "运营后台-热门比赛配置", "体育-运营后台-功能", ""):
        assert untouched not in by_src


def test_collect_changed_ignores_soft_deleted(backfill_script, db_session) -> None:
    _seed(db_session, [
        {"domain": "UGC"},
        {"domain": "UGC", "is_deleted": True},
        {"domain": "广告", "is_deleted": True},
    ])
    total, _, changed = backfill_script.collect_changed(db_session)
    assert total == 1
    assert changed == [("UGC", "用户端/UGC", 1)]


def test_collect_changed_empty_db(backfill_script, db_session) -> None:
    total, distinct, changed = backfill_script.collect_changed(db_session)
    assert (total, distinct, changed) == (0, 0, [])


# ── apply_changes：写入 ──


def test_apply_writes_and_keeps_soft_deleted(backfill_script, db_session) -> None:
    _seed(db_session, [
        {"domain": "UGC"},
        {"domain": "广告", "is_deleted": True},
        {"domain": "用户端/首页"},
    ])
    _, _, changed = backfill_script.collect_changed(db_session)
    written = backfill_script.apply_changes(db_session, changed)
    assert written == 1  # 软删行不写
    by_domain = {c.domain for c in db_session.query(CaseORM).all()}
    assert "用户端/UGC" in by_domain
    assert "广告" in by_domain  # 软删行保持原值
    assert "用户端/首页" in by_domain
    # 复核口径：原裸域值清零
    leftover = (
        db_session.query(CaseORM)
        .filter(CaseORM.is_deleted.is_(False), CaseORM.domain.in_(["UGC"]))
        .count()
    )
    assert leftover == 0


def test_apply_is_idempotent(backfill_script, db_session) -> None:
    _seed(db_session, [{"domain": "UGC"}, {"domain": "广告"}])
    _, _, changed = backfill_script.collect_changed(db_session)
    assert backfill_script.apply_changes(db_session, changed) == 2
    # 再次 collect → 无变更；再次 apply → 0 行
    _, _, changed2 = backfill_script.collect_changed(db_session)
    assert changed2 == []
    assert backfill_script.apply_changes(db_session, changed2) == 0
    values = sorted(c.domain for c in db_session.query(CaseORM).all())
    assert values == ["用户端/UGC", "用户端/广告"]


def test_apply_no_changes_short_circuit(backfill_script, db_session) -> None:
    _seed(db_session, [{"domain": "用户端/首页"}, {"domain": "体育-运营后台-功能"}])
    _, _, changed = backfill_script.collect_changed(db_session)
    assert changed == []
    assert backfill_script.apply_changes(db_session, changed) == 0
    assert db_session.query(CaseORM).count() == 2


# ── load_database_url：取值优先级与路径解析 ──


def test_load_database_url_env_priority(backfill_script, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
    assert backfill_script.load_database_url() == "postgresql://u:p@h/db"


def test_load_database_url_from_env_file(
    backfill_script, monkeypatch, tmp_path
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(backfill_script, "BACKEND_DIR", tmp_path)
    (tmp_path / ".env").write_text(
        "OTHER=1\nDATABASE_URL=sqlite:///./data/x.db\n", encoding="utf-8"
    )
    url = backfill_script.load_database_url()
    # 相对路径解析为 backend 目录下的绝对路径（任意 cwd 运行不建错目录）
    assert url.startswith("sqlite:///")
    assert url.endswith("/data/x.db")
    assert "sqlite:///./" not in url


def test_load_database_url_in_memory_not_resolved(backfill_script, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    assert backfill_script.load_database_url() == "sqlite:///:memory:"


def test_load_database_url_windows_abs_not_resolved(
    backfill_script, monkeypatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///F:/data/x.db")
    assert backfill_script.load_database_url() == "sqlite:///F:/data/x.db"


def test_load_database_url_missing_raises(
    backfill_script, monkeypatch, tmp_path
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(backfill_script, "BACKEND_DIR", tmp_path)  # 无 .env
    with pytest.raises(SystemExit, match="DATABASE_URL"):
        backfill_script.load_database_url()
