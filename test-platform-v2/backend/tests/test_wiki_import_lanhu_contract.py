"""切片 7 (Phase P2 Task 7) —— 蓝湖 URL 解析、immutable_version 标准化、三层写入契约。

不触网：patch lanhu_provider._extract_lanhu_content 模拟提取；URL 参数使用
实施计划指定的真实 tid/pid/versionId/docId/pageId 值。
"""
from __future__ import annotations

import asyncio

import pytest

from app.services.external import lanhu_provider

# 实施计划 §0 中指定的蓝湖 URL（真实参数值）
LANHU_URL = (
    "https://lanhuapp.com/web/#/item/project/product"
    "?tid=6324825d-1614-4d73-bc4c-f05cdf0734c1"
    "&pid=cc8cfbd5-16d2-481f-828e-7eb424a91694"
    "&versionId=26af2885-b229-4971-881c-c9bda43492fd"
    "&docId=e6b5ce1e-0d25-4e22-a9e9-450283918b3b"
    "&docType=axure"
    "&image_id=e6b5ce1e-0d25-4e22-a9e9-450283918b3b"
    "&pageId=2b4c4235b036420787d3e856b5d133d7"
    "&corpId=null"
)


# ── URL 解析 ──

def test_lanhu_url_ids_are_preserved():
    """验证 parse_lanhu_ids 从实施计划指定的 URL 中正确提取三个参数。"""
    doc_id, version_id, page_id = lanhu_provider.parse_lanhu_ids(LANHU_URL)
    assert doc_id == "e6b5ce1e-0d25-4e22-a9e9-450283918b3b"
    assert version_id == "26af2885-b229-4971-881c-c9bda43492fd"
    assert page_id == "2b4c4235b036420787d3e856b5d133d7"


def test_parse_lanhu_ids_page_optional():
    """URL 不含 pageId 时返回空字符串（表示整文档导入）。"""
    url_no_page = (
        "https://lanhuapp.com/web/#/item/project/product"
        "?docId=doc-123&versionId=ver-456"
    )
    doc_id, version_id, page_id = lanhu_provider.parse_lanhu_ids(url_no_page)
    assert doc_id == "doc-123"
    assert version_id == "ver-456"
    assert page_id == ""


def test_parse_lanhu_ids_missing_all():
    """完全没有蓝湖参数时返回三个空字符串。"""
    assert lanhu_provider.parse_lanhu_ids(
        "https://lanhuapp.com/web/#/item/project/board"
    ) == ("", "", "")


# ── immutable_version 标准化 ──

def test_immutable_version_format():
    """验证 build_immutable_version 产生标准化的 lanhu:xxx:yyy:zzz 格式。"""
    v = lanhu_provider.build_immutable_version(
        "doc-123", "ver-456", "page-789",
    )
    assert v == "lanhu:doc-123:ver-456:page-789"


def test_immutable_version_without_page():
    """page_id 为 None 时省略末尾段。"""
    v2 = lanhu_provider.build_immutable_version("doc-123", "ver-456", None)
    assert v2 == "lanhu:doc-123:ver-456"


def test_immutable_version_matches_plan_expected():
    """验证实施计划中的期望值与本函数输出一致。"""
    doc_id = "e6b5ce1e-0d25-4e22-a9e9-450283918b3b"
    version_id = "26af2885-b229-4971-881c-c9bda43492fd"
    page_id = "2b4c4235b036420787d3e856b5d133d7"
    v = lanhu_provider.build_immutable_version(doc_id, version_id, page_id)
    expected = (
        "lanhu:e6b5ce1e-0d25-4e22-a9e9-450283918b3b"
        ":26af2885-b229-4971-881c-c9bda43492fd"
        ":2b4c4235b036420787d3e856b5d133d7"
    )
    assert v == expected


# ── extract() 集成 ──

def test_extract_uses_lanhu_prefix_immutable_version(monkeypatch):
    """验证 extract() 产出的 immutable_version 带有 lanhu: 前缀。"""
    async def _fake(url, auto_login=True):
        return {
            "content": "比赛推送功能\nmatchId 必填，integer 类型",
            "page_filtered": True, "folder_name": "赛事模块",
            "changelog": {}, "client_scope": ["app"],
        }

    monkeypatch.setattr(lanhu_provider, "_extract_lanhu_content", _fake)
    r = asyncio.run(lanhu_provider.extract(LANHU_URL))
    assert r.extraction_status == "success"
    assert r.immutable_version.startswith("lanhu:")
    assert r.doc_id == "e6b5ce1e-0d25-4e22-a9e9-450283918b3b"
    assert r.version_id == "26af2885-b229-4971-881c-c9bda43492fd"
    assert r.page_id == "2b4c4235b036420787d3e856b5d133d7"


def test_extract_partial_status(monkeypatch):
    """验证当内容中包含「无文本内容」提示时，状态为 partial。"""
    async def _fake(url, auto_login=True):
        return {
            "content": "比赛推送\n部分页面内容\n（3 页无文本内容）",
            "page_filtered": False, "folder_name": "赛事",
            "changelog": {}, "client_scope": [],
        }

    monkeypatch.setattr(lanhu_provider, "_extract_lanhu_content", _fake)
    r = asyncio.run(lanhu_provider.extract(LANHU_URL))
    assert r.extraction_status == "partial"


# ── 向后兼容 ──

def test_parse_url_ids_alias():
    """_parse_url_ids 作为 parse_lanhu_ids 的别名仍然可用。"""
    doc_id, version_id, page_id = lanhu_provider._parse_url_ids(LANHU_URL)
    assert doc_id == "e6b5ce1e-0d25-4e22-a9e9-450283918b3b"
    assert version_id == "26af2885-b229-4971-881c-c9bda43492fd"
    assert page_id == "2b4c4235b036420787d3e856b5d133d7"


# ── 三层写入覆盖率（不触网，仅验证函数可 import 且签名正确）──

def test_import_service_exports():
    """验证 import_service 模块可导入且 import_lanhu 签名存在。"""
    from app.services.wiki import import_service
    assert callable(import_service.import_lanhu)


def test_ingest_service_exports():
    """验证 ingest_service 模块可导入且 wiki 编译入口存在。"""
    from app.services.wiki import ingest_service
    assert callable(ingest_service.run_wiki_ingest_in_new_session)


def test_entity_service_exports():
    """验证 entity_service 模块可导入且图谱提取入口存在（供 extract_graph 使用）。"""
    from app.services.knowledge.entity_service import extract_and_build_graph_in_new_session
    assert callable(extract_and_build_graph_in_new_session)


def test_raw_source_service_exports():
    """验证 raw_source_service 可正常 import。"""
    from app.services.wiki import raw_source_service
    assert callable(raw_source_service.record_raw_source)
    assert callable(raw_source_service.list_raw_sources)
