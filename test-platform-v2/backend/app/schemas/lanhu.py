"""蓝湖 Provider Schema —— 标准化提取结果 LanhuExtractResult。

供需求生成、知识中心 Raw Source、Wiki 编译统一消费。extraction_status 表达提取结果，
永不以异常向调用方传播失败（见 services/external/lanhu_provider.extract）。
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class LanhuPage(BaseModel):
    page_id: str = ""
    name: str = ""
    folder: str = ""
    content_md: str = ""


class LanhuExtractResult(BaseModel):
    source_type: str = "lanhu"
    source_ref: str = ""                 # 原始链接
    doc_id: str = ""
    version_id: str = ""
    page_id: str = ""
    document_name: str = ""
    module_name: str = ""                # 顶层文件夹/模块
    page_name: str = ""
    client_scope: list[str] = Field(default_factory=list)   # app/pc/web
    changelog: dict = Field(default_factory=dict)
    pages: list[LanhuPage] = Field(default_factory=list)
    content_md: str = ""                 # 提取到的结构化文本
    content_hash: str = ""               # SHA-256(content)
    immutable_version: str = ""          # docId:versionId:pageId 或 content_hash
    # success/partial/image_only/auth_failed/permission_denied/invalid_url/failed
    extraction_status: str = "failed"
    extraction_summary: str = ""
