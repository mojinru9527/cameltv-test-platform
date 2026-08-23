"""DSH 任务图片附件（Batch fix）—— 上传存储 + 执行时落任务工作区。

页面功能对齐 DSH web 输入框：用户可粘贴/拖拽/选择图片随任务提交；
上传存 `{session_root}/uploads/{file_id}/{原始文件名}`，任务执行时
resolve 到隔离工作区 `{workspace}/attachments/`，runner 在任务文本末尾
追加提示（可调用 read_image 工具查看），视觉模型即可看图。
"""
from __future__ import annotations

import re
import shutil
import uuid
from pathlib import Path

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10MB
_FILE_ID_RE = re.compile(r"^[0-9a-f]{32}$")

# 魔数校验：PNG/JPEG/WebP/GIF（read_image 支持的媒体类型）
_MAGIC: dict[str, tuple[bytes, int]] = {
    "image/png": (b"\x89PNG\r\n\x1a\n", 0),
    "image/jpeg": (b"\xff\xd8\xff", 0),
    "image/webp": (b"WEBP", 8),
    "image/gif": (b"GIF8", 0),
}


def _uploads_root() -> Path:
    """上传根目录（与 DSH 会话根同源：{session_root}/uploads）。"""
    from app.services.dsh.dsh_runner import _session_root

    return _session_root() / "uploads"


def _content_type_of(data: bytes) -> str | None:
    for media, (magic, offset) in _MAGIC.items():
        if len(data) >= offset + len(magic):
            if data[offset:offset + len(magic)] == magic:
                return media
    return None


def save_upload(data: bytes, filename: str = "", content_type: str = "") -> dict:
    """校验并保存一张上传图片，返回 {file_id, filename, bytes}。

    校验：大小 ≤10MB + 魔数（PNG/JPEG/WebP/GIF）。不过关抛 ValueError（转业务 400）。
    """
    if not data:
        raise ValueError("上传文件为空")
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(
            f"图片超过大小上限（10MB，当前 {round(len(data) / 1024 / 1024, 1)}MB）"
        )
    if _content_type_of(data) is None:
        raise ValueError("仅支持 PNG/JPEG/WebP/GIF 图片")
    safe_name = Path(filename or "image.bin").name or "image.bin"
    file_id = uuid.uuid4().hex
    target = _uploads_root() / file_id
    target.mkdir(parents=True, exist_ok=True)
    (target / safe_name).write_bytes(data)
    return {"file_id": file_id, "filename": safe_name, "bytes": len(data)}


def resolve_images(file_ids: list[str], workspace: Path) -> list[str]:
    """把上传的图片文件复制进任务隔离工作区，返回工作区内绝对路径列表。

    跳过缺失/非法 file_id（不阻断任务）；原文件保留在 uploads 供复用。
    """
    if not file_ids:
        return []
    workspace_mk = workspace / "attachments"
    resolved: list[str] = []
    for file_id in file_ids:
        if not isinstance(file_id, str) or not _FILE_ID_RE.fullmatch(file_id):
            continue
        src_dir = _uploads_root() / file_id
        if not src_dir.is_dir():
            continue
        for src in src_dir.iterdir():
            if not src.is_file():
                continue
            try:
                workspace_mk.mkdir(parents=True, exist_ok=True)
                dst = workspace_mk / src.name
                shutil.copy2(src, dst)
                resolved.append(str(dst))
            except OSError:
                continue
    return resolved


def image_hint(paths: list[str]) -> str:
    """追加到任务文本的提示（模型可通过 read_image 工具查看附件）。"""
    if not paths:
        return ""
    return (
        "\n\n[平台附件图片] 用户的 DSH 任务附带以下图片，"
        "如与任务相关请调用 read_image 工具查看：\n"
        + "\n".join(f"- {p}" for p in paths)
    )
