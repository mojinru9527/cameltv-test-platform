"""OCR provider 与 OCR/DOM 合并测试。"""
from __future__ import annotations


def test_sanitize_evidence_text_removes_xml_invalid_chars():
    """NUL/控制字符剥离，保留 \\n \\t \\r 与正常文本（docx 导出防失败）。"""
    from app.services.lanhu_evidence.merge_service import sanitize_evidence_text

    dirty = "赛事回放\x00详情\u0001展示\n第二行\t缩进\r\n"
    cleaned = sanitize_evidence_text(dirty)
    assert "\x00" not in cleaned
    assert "\u0001" not in cleaned
    assert "赛事回放详情展示" in cleaned
    assert "\n" in cleaned
    assert "\t" in cleaned


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

def test_local_provider_keeps_low_confidence_blocks(tmp_path, monkeypatch):
    """低置信度文本块不再被过滤（避免小字/模糊字缺失，batch-145）。"""
    import subprocess

    from app.services.lanhu_evidence.local_ocr_provider import LocalCommandOcrProvider

    monkeypatch.setattr(
        "app.core.config.settings.lanhu_ocr_command",
        'python -m app.services.lanhu_evidence.rapidocr_cli --image "{image}"',
    )
    image = tmp_path / "page.png"
    image.write_bytes(b"fake")

    class FakeResult:
        returncode = 0
        stdout = (
            '{"text":"清晰大字","confidence":0.98,"bbox":[0,0,100,20]}\n'
            '{"text":"模糊小字","confidence":0.42,"bbox":[0,20,100,40]}\n'
        )
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: FakeResult())

    result = LocalCommandOcrProvider().recognize(image)
    assert result.status == "success"
    assert len(result.blocks) == 2
    assert any(b.text == "模糊小字" for b in result.blocks)
    assert any(b.confidence < 0.5 for b in result.blocks)


def test_rapidocr_cli_bbox_normalizes_quad():
    """4 点框 → [x1,y1,x2,y2] 整数框（batch-145）。"""
    from app.services.lanhu_evidence.rapidocr_cli import _bbox_from_points

    points = [[22.0, 29.0], [275.0, 29.0], [275.0, 58.0], [22.0, 58.0]]
    assert _bbox_from_points(points) == [22, 29, 275, 58]


def test_rapidocr_cli_main_outputs_json_lines(monkeypatch, capsys, tmp_path):
    """CLI 输出逐行 JSON，兼容 parse_command_output（batch-145）。"""
    from app.services.lanhu_evidence import rapidocr_cli

    image = tmp_path / "page.png"
    image.write_bytes(b"fake")
    monkeypatch.setattr(
        rapidocr_cli,
        "recognize_image",
        lambda path: [
            {"text": "赛事回放", "confidence": 0.99, "bbox": [0, 0, 100, 20]},
            {"text": "低置信度小字", "confidence": 0.4, "bbox": [0, 20, 100, 40]},
        ],
    )
    code = rapidocr_cli.main(["--image", str(image)])
    assert code == 0
    out = capsys.readouterr().out
    assert '"text": "\u8d5b\u4e8b\u56de\u653e"' in out
    assert '"text": "\u4f4e\u7f6e\u4fe1\u5ea6\u5c0f\u5b57"' in out


def test_rapidocr_cli_main_fails_on_missing_image(capsys):
    """图片不存在 → 非零退出 + stderr 提示（batch-145）。"""
    from app.services.lanhu_evidence.rapidocr_cli import main

    code = main(["--image", "not-exist.png"])
    assert code == 2
    assert "图片不存在" in capsys.readouterr().err


def test_config_defaults_builtin_ocr_and_dpr():
    """默认配置：内置 rapidocr CLI + 截图 DPR 2.0（batch-145）。"""
    from app.core.config import settings

    assert "rapidocr_cli" in settings.lanhu_ocr_command
    assert "{image}" in settings.lanhu_ocr_command
    assert settings.lanhu_capture_device_scale_factor == 2.0
