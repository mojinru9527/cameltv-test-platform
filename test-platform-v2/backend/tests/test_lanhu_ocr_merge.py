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
    """低置信度文本块不再被过滤（避免小字/模糊字缺失，batch-247）。"""
    import subprocess

    from app.services.lanhu_evidence.local_ocr_provider import LocalCommandOcrProvider

    monkeypatch.setattr(
        "app.core.config.settings.lanhu_ocr_command",
        '{python} -m app.services.lanhu_evidence.rapidocr_cli --image "{image}"',
    )
    image = tmp_path / "page.png"
    image.write_bytes(b"fake")

    class FakeResult:
        returncode = 0
        stderr = ""
        stdout = '{"text":"低置信度小字","confidence":0.42,"bbox":[0,0,100,20]}\n'

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: FakeResult())

    result = LocalCommandOcrProvider().recognize(image)

    assert result.status == "success"
    assert len(result.blocks) == 1
    assert result.blocks[0].confidence == 0.42
    assert result.blocks[0].text == "低置信度小字"


def test_local_provider_uses_current_python_interpreter(tmp_path, monkeypatch):
    """命令模板中的 {python} 必须替换为当前解释器，避免 Windows venv 未激活。"""
    import subprocess
    import sys

    from app.services.lanhu_evidence.local_ocr_provider import LocalCommandOcrProvider

    monkeypatch.setattr(
        "app.core.config.settings.lanhu_ocr_command",
        '{python} -m app.services.lanhu_evidence.rapidocr_cli --image "{image}"',
    )
    image = tmp_path / "page.png"
    image.write_bytes(b"fake")
    captured: dict[str, object] = {}

    class FakeResult:
        returncode = 0
        stderr = ""
        stdout = ""

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return FakeResult()

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = LocalCommandOcrProvider().recognize(image)

    assert result.status == "success"
    # Batch 258 / B1-3：命令由「shell 字符串」改为 argv 数组，断言随之改为成员判断。
    assert isinstance(captured["command"], list)
    assert sys.executable in captured["command"]
    assert str(image) in captured["command"]
    assert captured["kwargs"]["shell"] is False
    assert captured["kwargs"]["encoding"] == "utf-8"


def test_rapidocr_cli_bbox_normalizes_quad():
    """4 点框 → [x1,y1,x2,y2] 整数框（batch-247）。"""
    from app.services.lanhu_evidence.rapidocr_cli import _bbox_from_points

    points = [[22.0, 29.0], [275.0, 29.0], [275.0, 58.0], [22.0, 58.0]]
    assert _bbox_from_points(points) == [22, 29, 275, 58]


def test_rapidocr_cli_main_outputs_json_lines(monkeypatch, capsys, tmp_path):
    """CLI 输出逐行 JSON，兼容 parse_command_output（batch-247）。"""
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

    assert rapidocr_cli.main(["--image", str(image)]) == 0

    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert len(lines) == 2
    assert '"赛事回放"' in lines[0]
    assert '"低置信度小字"' in lines[1]
