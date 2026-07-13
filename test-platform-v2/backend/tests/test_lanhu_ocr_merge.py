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
