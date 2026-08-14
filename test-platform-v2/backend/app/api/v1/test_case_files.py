"""测试用例 API 路由（Xmind/Excel 导入导出） — /api/v1/test-cases/*

Batch 181（FIX-173-P2-10）路由拆分：原 test_case.py 中的导入导出端点
（/export/xmind、/import/xmind、/export/excel、/import/excel）拆分至此。
端点函数体逐字移动，仅调整 import。
"""
from __future__ import annotations

import os
import shutil
import tempfile
from io import BytesIO

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.base_service import transaction
from app.core.db import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.exceptions import APIException
from app.schemas.common import R
from app.services import test_case_service
from app.services.excel_service import cases_to_excel_bytes, excel_bytes_to_cases
from app.services.xmind_service import cases_to_xmind_bytes, xmind_bytes_to_cases

router = APIRouter(prefix="/test-cases", tags=["测试用例-导入导出"])


# ── Xmind 导入导出 ──────────────────────────────────

@router.get("/export/xmind", summary="导出用例为 Xmind")
def export_xmind(
    domain: str = "",
    module: str = "",
    surface: str = "",
    taxonomy_domain: str = "",
    taxonomy_module: str = "",
    taxonomy_direct: bool = False,
    positive_negative: str = "",
    current: CurrentUser = Depends(require_permission("testcase:list")),
    db: Session = Depends(get_db),
):
    """导出当前项目用例为 Xmind 文件（域→模块→用例树形结构）。"""
    items, _ = test_case_service.list_cases(
        db, project_id=current.project_id or 0,
        domain=domain, module=module, surface=surface,
        taxonomy_domain=taxonomy_domain, taxonomy_module=taxonomy_module,
        taxonomy_direct=taxonomy_direct,
        positive_negative=positive_negative, page=1, page_size=10000,
    )
    buf = cases_to_xmind_bytes(items, root_title=f"测试用例-项目{current.project_id}")
    return StreamingResponse(
        BytesIO(buf.getvalue()),  # type: ignore[arg-type]
        media_type="application/vnd.xmind.workbook",
        headers={"Content-Disposition": "attachment; filename=test-cases.xmind"},
    )


@router.post("/import/xmind", response_model=R[dict], summary="从 Xmind 导入用例")
def import_xmind(
    req: Request,
    file: UploadFile = File(...),
    current: CurrentUser = Depends(require_permission("testcase:create")),
    db: Session = Depends(get_db),
):
    """解析 Xmind 文件，批量创建用例。"""
    if not file.filename or not file.filename.endswith(".xmind"):
        return R(code=1, msg="请上传 .xmind 文件")

    # P1-S6a: Content-Length 前置检查，避免读取超大文件 (max 10 MB)
    content_length = req.headers.get("content-length")
    if content_length:
        cl = int(content_length)
        max_bytes = 10 * 1024 * 1024
        if cl > max_bytes:
            raise APIException(
                f"上传文件超过限制 (max: 10 MB, got: {cl / (1024*1024):.1f} MB)",
                code=413,
            )

    # P1-S6d: 流式写入临时文件，zipfile 直接从磁盘读取，避免全量加载到内存
    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xmind") as tmp:
            shutil.copyfileobj(file.file, tmp, length=64 * 1024)
            tmp_path = tmp.name
        cases = xmind_bytes_to_cases(tmp_path)
    finally:
        if tmp_path:
            os.unlink(tmp_path)
    if not cases:
        return R(code=1, msg="未能从 Xmind 文件中解析出用例")

    imported = 0
    with transaction(db):
        for c in cases:
            c["project_id"] = current.project_id or 0
            c["source"] = "xmind_import"
            row = test_case_service.create_case(db, c)
            if row:
                imported += 1

    return R.ok({"imported": imported, "total": len(cases)})


# ── Excel 导入导出 ──

@router.get("/export/excel", summary="导出用例为 Excel")
def export_excel(
    domain: str = "",
    module: str = "",
    surface: str = "",
    taxonomy_domain: str = "",
    taxonomy_module: str = "",
    taxonomy_direct: bool = False,
    positive_negative: str = "",
    current: CurrentUser = Depends(require_permission("testcase:list")),
    db: Session = Depends(get_db),
):
    """导出当前项目用例为 Excel 文件（.xlsx）。"""
    items, _ = test_case_service.list_cases(
        db, project_id=current.project_id or 0,
        domain=domain, module=module, surface=surface,
        taxonomy_domain=taxonomy_domain, taxonomy_module=taxonomy_module,
        taxonomy_direct=taxonomy_direct,
        positive_negative=positive_negative, page=1, page_size=10000,
    )
    buf = cases_to_excel_bytes(items)
    return StreamingResponse(
        BytesIO(buf),  # type: ignore[arg-type]
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=test-cases.xlsx"},
    )


@router.post("/import/excel", response_model=R[dict], summary="从 Excel 导入用例")
def import_excel(
    req: Request,
    file: UploadFile = File(...),
    current: CurrentUser = Depends(require_permission("testcase:create")),
    db: Session = Depends(get_db),
):
    """解析 Excel 文件，批量创建用例。"""
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        return R(code=1, msg="请上传 .xlsx 或 .xls 文件")

    # Content-Length check (max 10 MB)
    content_length = req.headers.get("content-length")
    if content_length:
        cl = int(content_length)
        max_bytes = 10 * 1024 * 1024
        if cl > max_bytes:
            raise APIException(
                f"上传文件超过限制 (max: 10 MB, got: {cl / (1024*1024):.1f} MB)",
                code=413,
            )

    contents = file.file.read()
    cases = excel_bytes_to_cases(contents)
    if not cases:
        return R(code=1, msg="未能从 Excel 文件中解析出用例（请确保包含「用例标题」列）")

    imported = 0
    with transaction(db):
        for c in cases:
            c["project_id"] = current.project_id or 0
            row = test_case_service.create_case(db, c)
            if row:
                imported += 1

    return R.ok({"imported": imported, "total": len(cases)})
