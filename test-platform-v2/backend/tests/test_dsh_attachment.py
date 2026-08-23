"""DSH 图片附件（Batch fix）回归测试。

覆盖：
- save_upload：魔数校验（PNG 通过/非图片拒绝）、大小上限、空文件
- resolve_images：合法 file_id 复制进工作区、非法/缺失跳过
- image_hint：提示文本格式
- run_dsh_task 集成：images 落工作区 + 任务文本追加提示（node 路径 mock subprocess）
"""
from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import patch

import pytest

from app.core.config import settings
from app.services.dsh import dsh_attachment_service as att
from app.services.dsh.dsh_runner import run_dsh_task

PNG = b"\x89PNG\r\n\x1a\n" + b"fake-png-body" * 10
JPEG = b"\xff\xd8\xff\xe0" + b"fake-jpeg-body" * 10
BIG = b"\x89PNG\r\n\x1a\n" + b"x" * (att.MAX_IMAGE_BYTES + 1)


class TestSaveUpload:
    def test_png_saved(self, tmp_path):
        with patch.object(settings, "dsh_session_root", str(tmp_path / "sess")):
            r = att.save_upload(PNG, "界面截图.png", "image/png")
        assert re.fullmatch(r"[0-9a-f]{32}", r["file_id"])
        assert r["filename"] == "界面截图.png"
        assert (tmp_path / "sess" / "uploads" / r["file_id"] / "界面截图.png").exists()

    def test_jpeg_saved(self, tmp_path):
        with patch.object(settings, "dsh_session_root", str(tmp_path / "sess")):
            r = att.save_upload(JPEG, "a.jpg", "image/jpeg")
        assert r["bytes"] == len(JPEG)

    def test_non_image_rejected(self, tmp_path):
        with patch.object(settings, "dsh_session_root", str(tmp_path / "sess")):
            with pytest.raises(ValueError, match="仅支持"):
                att.save_upload(b"plain text not an image", "t.txt", "text/plain")

    def test_too_large_rejected(self, tmp_path):
        with patch.object(settings, "dsh_session_root", str(tmp_path / "sess")):
            with pytest.raises(ValueError, match="超过大小上限"):
                att.save_upload(BIG, "big.png", "image/png")

    def test_empty_rejected(self, tmp_path):
        with patch.object(settings, "dsh_session_root", str(tmp_path / "sess")):
            with pytest.raises(ValueError, match="为空"):
                att.save_upload(b"", "e.png", "image/png")


class TestResolveImages:
    def test_copy_into_workspace(self, tmp_path):
        with patch.object(settings, "dsh_session_root", str(tmp_path / "sess")):
            fid = att.save_upload(PNG, "shot.png", "image/png")["file_id"]
            ws = tmp_path / "ws-abc"
            paths = att.resolve_images([fid], ws)
        assert len(paths) == 1
        p = Path(paths[0])
        assert p.parent == ws / "attachments"
        assert p.read_bytes() == PNG

    def test_invalid_and_missing_skipped(self, tmp_path):
        with patch.object(settings, "dsh_session_root", str(tmp_path / "sess")):
            paths = att.resolve_images(["not-a-valid-id"], tmp_path / "ws")
        assert paths == []


class TestImageHint:
    def test_hint_mentions_read_image(self):
        hint = att.image_hint(["/ws/attachments/a.png"])
        assert "read_image" in hint
        assert "/ws/attachments/a.png" in hint

    def test_empty_hint(self):
        assert att.image_hint([]) == ""


class TestRunnerIntegration:
    def test_images_appended_to_task_text(self, tmp_path, monkeypatch):
        """node 路径：images 复制到工作区并在任务文本末尾追加提示。"""
        with patch.object(settings, "dsh_session_root", str(tmp_path / "sess")), \
                patch.object(settings, "dsh_runtime", "node"), \
                patch.object(settings, "dsh_enabled", True), \
                patch.object(settings, "dsh_api_key", "test-key"), \
                patch.object(settings, "dsh_model", "deepseek-v4-flash"):
            fid = att.save_upload(PNG, "shot.png", "image/png")["file_id"]
            fake_entry = tmp_path / "bin.js"
            fake_entry.write_text("// fake")  # 让 runtime_available 通过
            monkeypatch.setattr(settings, "dsh_harness_path", str(fake_entry))

            captured = {}

            def fake_run(cmd, **kwargs):
                captured["cmd"] = cmd
                captured["env"] = kwargs.get("env", {})
                return type("P", (), {"returncode": 0, "stdout": "ok", "stderr": ""})()

            monkeypatch.setattr("app.services.dsh.dsh_runner.subprocess.run", fake_run)
            result = run_dsh_task("看这张截图", images=[fid])

        assert result.exit_code == 0
        task_arg = captured["cmd"][-1]
        assert "read_image" in task_arg
        assert "shot.png" in task_arg
        assert captured["env"]["DSH_MODEL"] == settings.dsh_model
