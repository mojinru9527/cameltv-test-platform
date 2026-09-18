"""Batch 258 / B1-3 — OCR 命令去 shell，关闭审计基线 S3。

原实现：`template.replace("{image}", str(path))` 后 `subprocess(..., shell=True)`。
路径含空格/分号时命令变形；改后模板用哨兵占位 → `shlex.split` → 回填真实值，
分词与插值解耦，路径始终是**单一 argv 元素**，且不再经过 shell。
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import app
from app.services.lanhu_evidence import local_ocr_provider as ocr

DEFAULT_TEMPLATE = '{python} -m app.services.lanhu_evidence.rapidocr_cli --image "{image}"'


class TestBuildCommand:
    """模板 → argv 数组的解析契约。"""

    def test_default_template_parses_into_argv(self):
        image = Path("shots") / "shot.png"
        argv = ocr.build_command(DEFAULT_TEMPLATE, image_path=image, python_executable="/usr/bin/python3")
        assert argv == [
            "/usr/bin/python3",
            "-m",
            "app.services.lanhu_evidence.rapidocr_cli",
            "--image",
            str(image),
        ]

    def test_image_path_with_space_is_a_single_argument(self):
        image = Path("my screenshots") / "a b.png"
        argv = ocr.build_command(DEFAULT_TEMPLATE, image_path=image, python_executable="/usr/bin/python3")
        assert argv[-1] == str(image)
        assert argv.count(str(image)) == 1
        assert len(argv) == 5  # 路径没有被空格切成多个元素

    def test_image_path_with_shell_metacharacters_is_not_split(self):
        nasty = Path("a;rm -rf") / "b.png"
        argv = ocr.build_command(DEFAULT_TEMPLATE, image_path=nasty, python_executable="py")
        assert argv[-1] == str(nasty)
        assert len(argv) == 5

    def test_quoted_placeholder_style_is_supported(self):
        """不带引号的模板同样可用（引号只是为用户书写习惯保留）。"""
        image = Path("a b.png")
        argv = ocr.build_command(
            "{python} -m mod --image {image}", image_path=image, python_executable="python"
        )
        assert argv == ["python", "-m", "mod", "--image", str(image)]

    def test_extra_flags_are_preserved(self):
        image = Path("x.png")
        argv = ocr.build_command(
            "{python} -m mod --json --image {image} --lang ch",
            image_path=image,
            python_executable="python",
        )
        assert argv == ["python", "-m", "mod", "--json", "--image", str(image), "--lang", "ch"]


class TestRecognizeDoesNotUseShell:
    def _install_runner(self, monkeypatch, captured: dict, stdout: str, enabled: bool):
        def _runner(args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs
            return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")

        monkeypatch.setattr(ocr.settings, "heavy_task_budget_enabled", enabled)
        monkeypatch.setattr(ocr, "run_supervised", _runner)
        monkeypatch.setattr(ocr.subprocess, "run", _runner)

    def test_argv_is_a_list_and_shell_is_not_enabled(self, monkeypatch):
        captured: dict = {}
        self._install_runner(monkeypatch, captured, json.dumps({"text": "hello", "confidence": 0.9}), True)
        monkeypatch.setattr(ocr.settings, "lanhu_ocr_command", DEFAULT_TEMPLATE)

        image = Path("a b.png")
        result = ocr.LocalCommandOcrProvider().recognize(image)

        assert result.status == "success"
        assert result.blocks[0].text == "hello"
        assert isinstance(captured["args"], list)
        assert captured["args"][-1] == str(image)
        assert captured["kwargs"].get("shell", False) is False

    def test_fallback_subprocess_run_path_is_also_shell_free(self, monkeypatch):
        captured: dict = {}
        self._install_runner(monkeypatch, captured, json.dumps({"text": "x", "confidence": 0.5}), False)
        monkeypatch.setattr(ocr.settings, "lanhu_ocr_command", DEFAULT_TEMPLATE)

        ocr.LocalCommandOcrProvider().recognize(Path("/tmp/y.png"))

        assert isinstance(captured["args"], list)
        assert captured["kwargs"].get("shell", False) is False

    def test_unconfigured_command_returns_unavailable(self, monkeypatch):
        monkeypatch.setattr(ocr.settings, "lanhu_ocr_command", "")
        assert ocr.LocalCommandOcrProvider().recognize(Path("/tmp/z.png")).status == "unavailable"


class TestNoShellTrueAnywhereInApp:
    """升级为可执行校验（bug-guard 规则 3）：app/ 下不允许再出现 shell=True。"""

    def test_no_shell_true_in_app_sources(self):
        app_root = Path(app.__file__).parent
        offenders = [
            str(path.relative_to(app_root))
            for path in app_root.rglob("*.py")
            if "shell=True" in path.read_text(encoding="utf-8", errors="replace")
        ]
        assert offenders == [], f"app/ 下仍存在 shell=True: {offenders}"
