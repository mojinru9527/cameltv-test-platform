"""证据包 Word/JSON 导出测试。"""
from __future__ import annotations

import json


def test_word_export_contains_page_titles_and_text(tmp_path):
    from app.services.lanhu_evidence.word_export_service import WordPage, export_word

    out = tmp_path / "lanhu.docx"
    export_word(
        output_path=out,
        title="蓝湖证据包",
        source_url="https://lanhuapp.com/x",
        pages=[
            WordPage(
                page_name="比赛推送",
                page_path="App/赛事/比赛推送",
                screenshots=[],
                merged_text="matchId 必填",
                quality={"status": "success"},
            )
        ],
    )

    assert out.exists()
    from docx import Document

    doc = Document(str(out))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "比赛推送" in text
    assert "matchId 必填" in text


def test_json_export_contains_source_refs(tmp_path):
    from app.services.lanhu_evidence.json_export_service import export_json

    out = tmp_path / "lanhu.json"
    export_json(
        output_path=out,
        job={
            "job_id": 1,
            "source_url": "https://lanhuapp.com/x",
            "doc_id": "d",
            "version_id": "v",
        },
        pages=[{
            "page_id": "p1",
            "page_name": "比赛推送",
            "page_path": "App/赛事/比赛推送",
            "merged_text": "matchId 必填",
            "screenshots": ["pages/p1/segment-001.png"],
            "quality": {"status": "success"},
        }],
    )

    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["doc_id"] == "d"
    assert data["page_count"] == 1
    assert data["pages"][0]["source_refs"]["page_id"] == "p1"
    assert data["pages"][0]["source_refs"]["version_id"] == "v"
