"""Batch 259 / B2-4 — 本地对象存储路径收敛（关闭审计基线 S4）。

原实现 `normpath(join(base_dir, rel))` 只做字符串归一，".." 可以逃出 base。
改后：`resolve()` + `is_relative_to(base)`，写法与 `app/api/v1/lanhu_evidence_assets.py`
的下载收敛保持一致（同一仓库只留一种收敛写法）。
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.integrations.object_storage.base import StorageError
from app.integrations.object_storage.local import LocalStorage


@pytest.fixture
def storage(tmp_path) -> LocalStorage:
    return LocalStorage(str(tmp_path / "objects"))


class TestTraversalIsRejected:
    @pytest.mark.parametrize(
        "uri",
        [
            "../escape.json",
            "../../etc/passwd",
            "project/../../escape.json",
            "..\\..\\windows\\win.ini",
            "project/1/../../../etc/passwd",
            ".",
            "",
            "   ",
        ],
    )
    def test_put_rejects_escaping_uri(self, storage, uri):
        with pytest.raises(StorageError):
            storage.put(uri, b"x", "application/octet-stream")

    @pytest.mark.parametrize("uri", ["../escape.json", "../../etc/passwd", "a/../../b"])
    def test_read_paths_reject_escaping_uri(self, storage, uri):
        for operation in (storage.get, storage.delete):
            with pytest.raises(StorageError):
                operation(uri)

    def test_exists_rejects_escaping_uri(self, storage):
        with pytest.raises(StorageError):
            storage.exists("../escape.json")

    def test_no_file_is_written_outside_base(self, storage, tmp_path):
        outside = tmp_path / "escape.json"
        with pytest.raises(StorageError):
            storage.put("../escape.json", b"pwned", "application/json")
        assert not outside.exists(), "逃逸写入竟然成功了"


class TestNormalUsageStillWorks:
    def test_put_get_exists_delete_roundtrip(self, storage, tmp_path):
        uri = "project/1/mission/2/run/3/report.json"
        meta = storage.put(uri, b'{"ok":true}', "application/json")
        assert meta["size_bytes"] == len(b'{"ok":true}')
        assert storage.exists(uri) is True
        assert storage.get(uri) == b'{"ok":true}'
        assert (tmp_path / "objects" / "project/1/mission/2/run/3/report.json").exists()
        storage.delete(uri)
        assert storage.exists(uri) is False

    def test_leading_slash_is_treated_as_relative(self, storage):
        """历史 URI 常以 `/project/...` 形式传入，收敛后仍应可用（base 内）。"""
        uri = "/project/9/run/1/a.txt"
        storage.put(uri, b"ok", "text/plain")
        assert storage.get(uri) == b"ok"

    def test_nested_directories_are_created(self, storage):
        storage.put("a/b/c/d.txt", b"x", "text/plain")
        assert storage.get("a/b/c/d.txt") == b"x"


class TestSymlinkEscape:
    """符号链接逃逸：resolve() 会跟随符号链接，因此必须也被拦住。"""

    def test_symlinked_directory_cannot_escape(self, storage, tmp_path):
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        link = Path(storage.base_dir) / "link"
        link.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.symlink(outside_dir, link, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("当前环境不允许创建符号链接（Windows 需开发者模式/管理员）")
        with pytest.raises(StorageError):
            storage.put("link/pwned.json", b"x", "application/json")
        assert not (outside_dir / "pwned.json").exists()
