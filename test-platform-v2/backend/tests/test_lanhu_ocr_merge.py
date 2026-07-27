"""OCR provider 与 OCR/DOM 合并测试。"""
from __future__ import annotations


def test_mock_ocr_provider_returns_blocks(tmp_path, monkeypatch):
    from app.services.lanhu_evidence.ocr_provider import get_ocr_provider

    monkeypatch.setattr("app.core.config.settings.lanhu_ocr_provider", "mock")
    image = tmp_path / "page.png"
    image.write_bytes(b"fake")

    result = get_ocr_provider().recognize(image)

    assert result.status == "success"
    assert result.blocks[0].text
    assert "page.png" in result.blocks[0].text


def test_local_provider_unavailable_when_command_missing(tmp_path, monkeypatch):
    from app.services.lanhu_evidence.local_ocr_provider import LocalCommandOcrProvider

    monkeypatch.setattr("app.core.config.settings.lanhu_ocr_command", "")
    image = tmp_path / "page.png"
    image.write_bytes(b"fake")

    result = LocalCommandOcrProvider().recognize(image)
    assert result.status == "unavailable"


def test_parse_command_output_reads_json_lines():
    from app.services.lanhu_evidence.local_ocr_provider import parse_command_output

    blocks = parse_command_output(
        '{"text":"matchId 必填","confidence":0.96,"bbox":[0,0,100,20]}\n'
        "not-json-line\n"
        '{"text":"分钟数必填","confidence":0.9,"bbox":[0,20,100,40]}\n'
    )
    assert len(blocks) == 2
    assert blocks[0].text == "matchId 必填"
    assert blocks[1].order_index == 2


def test_merge_prefers_non_empty_ocr_and_preserves_dom():
    from app.services.lanhu_evidence.merge_service import merge_page_text

    result = merge_page_text(
        page_name="比赛推送",
        dom_text="接口 /ee/test/matchpush",
        ocr_text="比赛推送\nmatchId 必填\n分钟数必填",
    )

    assert "matchId 必填" in result.merged_text
    assert "/ee/test/matchpush" in result.merged_text
    assert result.quality["ocr_chars"] > 0
    assert result.quality["status"] == "success"


def test_merge_marks_low_confidence_when_ocr_empty_and_dom_short():
    from app.services.lanhu_evidence.merge_service import merge_page_text

    result = merge_page_text(page_name="空页面", dom_text="", ocr_text="")

    assert result.quality["status"] == "needs_review"
    assert result.quality["has_ocr"] is False
    assert result.quality["has_dom"] is False

