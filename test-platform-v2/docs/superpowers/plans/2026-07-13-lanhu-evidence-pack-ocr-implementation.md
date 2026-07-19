# Lanhu Evidence Pack OCR Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reliable Lanhu requirement extraction pipeline that captures every requirement page, including scrollable pages, into an evidence pack, then produces Word + JSON + RAG/Wiki imports from the same verified source.

**Architecture:** Replace single-path Lanhu text extraction with a multi-source evidence pipeline: Lanhu page tree discovery -> scroll-aware screenshot capture -> OCR -> DOM text extraction -> merge and completeness validation -> Word/JSON artifacts -> requirement document/RAG/Wiki ingestion. Store immutable evidence files under `storage/lanhu-evidence/{job_id}` and database metadata in project-scoped tables so every generated requirement, chunk, and Wiki page can trace back to a screenshot and OCR block.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, python-docx, Playwright, Pillow, pluggable OCR provider interface, local OCR adapter, optional cloud OCR adapter, existing Lanhu MCP resources, existing Knowledge/RAG/Wiki services.

---

## 0. Product Decision

Use this target flow:

```text
Lanhu URL
-> Evidence Pack
-> Word + JSON
-> Requirement extraction / RAG / Wiki
```

Do not make Word the only truth source. Word is the human-readable review artifact. The evidence pack is the system truth source and must preserve:

- page tree metadata
- original Lanhu URL and `docId/versionId/pageId`
- one or more screenshots per page
- OCR text per screenshot segment
- DOM/MCP extracted text per page
- merged page text
- quality metrics
- Word path
- JSON path
- import target references

Long and scrollable pages are first-class requirements. The capture service must support:

- standard full-page screenshot when Playwright can capture all content
- viewport-step screenshots when the page uses custom scroll containers or Axure dynamic panels
- duplicate segment removal
- max segment guard to avoid infinite scrolling
- manual review status when page completeness is uncertain

---

## 1. File Structure

### Backend Models And Schemas

- Create: `test-platform-v2/backend/app/models/lanhu_evidence.py`
  - `LanhuEvidenceJob`: one import/capture job.
  - `LanhuEvidencePage`: one Lanhu page in the page tree.
  - `LanhuEvidenceAsset`: screenshot/Word/JSON/file assets.
  - `LanhuOcrBlock`: OCR output blocks.
- Create: `test-platform-v2/backend/app/schemas/lanhu_evidence.py`
  - request/response DTO for capture, job detail, page detail, asset download, import actions.
- Create: `test-platform-v2/backend/alembic/versions/20260713_lanhu_evidence_pack.py`
  - migration for new tables.

### Backend Services

- Create: `test-platform-v2/backend/app/services/lanhu_evidence/page_discovery.py`
  - parse Lanhu ids and page tree using existing `lanhu_provider`/`lanhu-mcp`.
- Create: `test-platform-v2/backend/app/services/lanhu_evidence/screenshot_service.py`
  - scroll-aware screenshot capture.
- Create: `test-platform-v2/backend/app/services/lanhu_evidence/ocr_provider.py`
  - provider interface and data models.
- Create: `test-platform-v2/backend/app/services/lanhu_evidence/local_ocr_provider.py`
  - local OCR adapter. Initial implementation can shell out to configured OCR command or return explicit `unavailable` status.
- Create: `test-platform-v2/backend/app/services/lanhu_evidence/merge_service.py`
  - merge OCR and DOM/MCP text.
- Create: `test-platform-v2/backend/app/services/lanhu_evidence/word_export_service.py`
  - generate `.docx` with screenshots and extracted text.
- Create: `test-platform-v2/backend/app/services/lanhu_evidence/json_export_service.py`
  - generate normalized requirement JSON.
- Create: `test-platform-v2/backend/app/services/lanhu_evidence/import_service.py`
  - import evidence Word/JSON into requirement/RAG/Wiki.
- Create: `test-platform-v2/backend/app/services/lanhu_evidence/job_runner.py`
  - async job orchestration, retry, cancel, status transition.
- Modify: `test-platform-v2/backend/app/services/external/lanhu_provider.py`
  - expose page tree and local Axure page URLs for screenshot capture.
- Modify: `test-platform-v2/backend/app/services/wiki/import_service.py`
  - accept evidence pack content as source.
- Modify: `test-platform-v2/backend/app/services/knowledge/ingest_service.py`
  - add evidence source metadata.
- Modify: `test-platform-v2/backend/app/services/requirement_service.py`
  - allow creating requirement document from generated Word/JSON artifacts.

### Backend API

- Create: `test-platform-v2/backend/app/api/v1/lanhu_evidence.py`
  - start capture job
  - get job detail
  - list pages
  - get page detail
  - download assets
  - import to requirement/RAG/Wiki
  - retry/cancel job
- Modify: `test-platform-v2/backend/app/main.py`
  - register route.
- Modify: `test-platform-v2/backend/app/core/config.py`
  - add evidence/OCR settings.
- Modify: `test-platform-v2/backend/app/seed.py`
  - add permissions.

### Frontend

- Create: `test-platform-v2/frontend/src/api/lanhuEvidence.ts`
- Create: `test-platform-v2/frontend/src/pages/knowledge/components/LanhuEvidenceDialog.tsx`
- Create: `test-platform-v2/frontend/src/pages/knowledge/components/LanhuEvidenceJobDrawer.tsx`
- Modify: `test-platform-v2/frontend/src/pages/knowledge/components/WikiImportDialog.tsx`
  - add option “使用证据包 OCR 导入”.
- Modify: `test-platform-v2/frontend/src/pages/requirement/index.tsx`
  - Lanhu tab should start evidence job instead of storing only raw URL.
- Modify: `test-platform-v2/frontend/src/types/index.ts`
  - add evidence DTOs.

### Tests

- Create: `test-platform-v2/backend/tests/test_lanhu_evidence_models.py`
- Create: `test-platform-v2/backend/tests/test_lanhu_page_discovery.py`
- Create: `test-platform-v2/backend/tests/test_lanhu_screenshot_service.py`
- Create: `test-platform-v2/backend/tests/test_lanhu_ocr_merge.py`
- Create: `test-platform-v2/backend/tests/test_lanhu_word_export.py`
- Create: `test-platform-v2/backend/tests/test_lanhu_evidence_import.py`
- Create: `test-platform-v2/frontend/src/pages/knowledge/components/__tests__/LanhuEvidenceDialog.test.tsx`

---

## 2. Configuration

Add to `test-platform-v2/backend/app/core/config.py`:

```python
# ── Lanhu Evidence Pack / OCR ──
lanhu_evidence_enabled: bool = False
lanhu_evidence_storage_dir: str = ""  # empty = backend/storage/lanhu-evidence
lanhu_capture_viewport_width: int = 1440
lanhu_capture_viewport_height: int = 1200
lanhu_capture_scroll_step_ratio: float = 0.85
lanhu_capture_max_segments_per_page: int = 30
lanhu_capture_wait_ms: int = 600
lanhu_ocr_provider: str = "local"  # local/cloud/mock
lanhu_ocr_command: str = ""        # optional command template, e.g. paddleocr --image {image}
lanhu_ocr_min_confidence: float = 0.60
lanhu_evidence_word_embed_screenshots: bool = True
lanhu_evidence_import_to_requirement: bool = True
lanhu_evidence_import_to_knowledge: bool = True
lanhu_evidence_import_to_wiki: bool = True
```

Rationale:

- Keep default off because capture + OCR can be expensive.
- Keep OCR provider pluggable because OCR engine choice may change.
- Use `mock` provider in deterministic unit tests.

---

## 3. Database Schema

### Task 1: Evidence Pack Tables

**Files:**
- Create: `test-platform-v2/backend/app/models/lanhu_evidence.py`
- Create: `test-platform-v2/backend/alembic/versions/20260713_lanhu_evidence_pack.py`
- Create: `test-platform-v2/backend/app/schemas/lanhu_evidence.py`
- Test: `test-platform-v2/backend/tests/test_lanhu_evidence_models.py`

- [ ] **Step 1: Write failing model tests**

```python
def test_evidence_job_model_roundtrip(db):
    from app.models.lanhu_evidence import LanhuEvidenceJob

    job = LanhuEvidenceJob(
        project_id=1,
        source_url="https://lanhuapp.com/web/#/item/project/product?docId=d&versionId=v&pageId=p",
        doc_id="d",
        version_id="v",
        root_page_id="p",
        status="pending",
        storage_dir="storage/lanhu-evidence/1",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    assert job.id > 0
    assert job.project_id == 1
    assert job.status == "pending"
```

```python
def test_page_asset_and_ocr_block_relationship_fields(db):
    from app.models.lanhu_evidence import LanhuEvidenceAsset, LanhuEvidencePage, LanhuOcrBlock

    page = LanhuEvidencePage(
        job_id=1,
        project_id=1,
        page_id="p1",
        page_name="比赛推送",
        page_path="赛事/App/比赛推送",
        capture_status="success",
    )
    db.add(page)
    db.flush()
    asset = LanhuEvidenceAsset(
        job_id=1,
        page_id=page.id,
        project_id=1,
        asset_type="screenshot",
        file_path="storage/lanhu-evidence/1/pages/p1/segment-001.png",
        sha256="abc",
    )
    db.add(asset)
    db.flush()
    block = LanhuOcrBlock(
        job_id=1,
        page_id=page.id,
        asset_id=asset.id,
        project_id=1,
        text="matchId 必填",
        confidence=0.96,
        bbox_json="[0,0,100,20]",
    )
    db.add(block)
    db.commit()
    assert block.asset_id == asset.id
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
cd test-platform-v2/backend
pytest tests/test_lanhu_evidence_models.py -q
```

Expected: fail with missing model/module.

- [ ] **Step 3: Create models**

Add:

```python
"""Lanhu evidence pack models."""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class LanhuEvidenceJob(Base, TimestampMixin):
    __tablename__ = "lanhu_evidence_job"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(index=True)
    source_url: Mapped[str] = mapped_column(Text, default="")
    doc_id: Mapped[str] = mapped_column(default="", index=True)
    version_id: Mapped[str] = mapped_column(default="", index=True)
    root_page_id: Mapped[str] = mapped_column(default="", index=True)
    document_name: Mapped[str] = mapped_column(default="")
    status: Mapped[str] = mapped_column(default="pending", index=True)
    stage: Mapped[str] = mapped_column(default="queued")
    total_pages: Mapped[int] = mapped_column(default=0)
    captured_pages: Mapped[int] = mapped_column(default=0)
    ocr_pages: Mapped[int] = mapped_column(default=0)
    failed_pages: Mapped[int] = mapped_column(default=0)
    word_path: Mapped[str] = mapped_column(default="")
    json_path: Mapped[str] = mapped_column(default="")
    storage_dir: Mapped[str] = mapped_column(default="")
    quality_json: Mapped[str] = mapped_column(Text, default="{}")
    error_message: Mapped[str] = mapped_column(Text, default="")
    cancel_requested: Mapped[bool] = mapped_column(default=False)
    creator_id: Mapped[int] = mapped_column(default=0)
    started_at: Mapped[datetime | None] = mapped_column(default=None)
    finished_at: Mapped[datetime | None] = mapped_column(default=None)


class LanhuEvidencePage(Base, TimestampMixin):
    __tablename__ = "lanhu_evidence_page"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(index=True)
    project_id: Mapped[int] = mapped_column(index=True)
    page_id: Mapped[str] = mapped_column(default="", index=True)
    page_name: Mapped[str] = mapped_column(default="")
    page_path: Mapped[str] = mapped_column(default="")
    folder: Mapped[str] = mapped_column(default="")
    order_index: Mapped[int] = mapped_column(default=0)
    page_url: Mapped[str] = mapped_column(Text, default="")
    local_url: Mapped[str] = mapped_column(Text, default="")
    capture_status: Mapped[str] = mapped_column(default="pending", index=True)
    ocr_status: Mapped[str] = mapped_column(default="pending", index=True)
    dom_text: Mapped[str] = mapped_column(Text, default="")
    ocr_text: Mapped[str] = mapped_column(Text, default="")
    merged_text: Mapped[str] = mapped_column(Text, default="")
    segment_count: Mapped[int] = mapped_column(default=0)
    quality_json: Mapped[str] = mapped_column(Text, default="{}")
    error_message: Mapped[str] = mapped_column(Text, default="")


class LanhuEvidenceAsset(Base, TimestampMixin):
    __tablename__ = "lanhu_evidence_asset"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(index=True)
    page_id: Mapped[int | None] = mapped_column(default=None, index=True)
    project_id: Mapped[int] = mapped_column(index=True)
    asset_type: Mapped[str] = mapped_column(default="", index=True)
    file_path: Mapped[str] = mapped_column(Text, default="")
    relative_path: Mapped[str] = mapped_column(Text, default="")
    mime_type: Mapped[str] = mapped_column(default="")
    width: Mapped[int] = mapped_column(default=0)
    height: Mapped[int] = mapped_column(default=0)
    scroll_top: Mapped[int] = mapped_column(default=0)
    viewport_height: Mapped[int] = mapped_column(default=0)
    sha256: Mapped[str] = mapped_column(default="", index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")


class LanhuOcrBlock(Base):
    __tablename__ = "lanhu_ocr_block"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(index=True)
    page_id: Mapped[int] = mapped_column(index=True)
    asset_id: Mapped[int] = mapped_column(index=True)
    project_id: Mapped[int] = mapped_column(index=True)
    text: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(default=0.0)
    bbox_json: Mapped[str] = mapped_column(Text, default="[]")
    order_index: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
```

- [ ] **Step 4: Add migration**

Migration creates the four tables and indexes on:

```text
lanhu_evidence_job(project_id, status)
lanhu_evidence_job(project_id, doc_id, version_id)
lanhu_evidence_page(job_id, order_index)
lanhu_evidence_page(project_id, page_id)
lanhu_evidence_asset(job_id, page_id, asset_type)
lanhu_ocr_block(job_id, page_id, asset_id)
```

- [ ] **Step 5: Add schemas**

Add DTOs:

```python
class LanhuEvidenceCreateRequest(BaseModel):
    url: str = Field(..., min_length=1)
    capture_all_pages: bool = True
    include_word: bool = True
    include_json: bool = True
    import_to_requirement: bool = False
    import_to_knowledge: bool = False
    import_to_wiki: bool = False


class LanhuEvidenceJobOut(BaseModel):
    id: int
    project_id: int
    source_url: str
    doc_id: str = ""
    version_id: str = ""
    root_page_id: str = ""
    status: str
    stage: str
    total_pages: int = 0
    captured_pages: int = 0
    ocr_pages: int = 0
    failed_pages: int = 0
    word_path: str = ""
    json_path: str = ""
    quality_json: str = "{}"
    error_message: str = ""
    created_at: datetime | None = None
    finished_at: datetime | None = None
    model_config = {"from_attributes": True}
```

- [ ] **Step 6: Run tests**

Run:

```bash
cd test-platform-v2/backend
pytest tests/test_lanhu_evidence_models.py -q
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add test-platform-v2/backend/app/models/lanhu_evidence.py test-platform-v2/backend/app/schemas/lanhu_evidence.py test-platform-v2/backend/alembic/versions/20260713_lanhu_evidence_pack.py test-platform-v2/backend/tests/test_lanhu_evidence_models.py
git commit -m "feat: add lanhu evidence pack models"
```

---

## 4. Page Discovery

### Task 2: Discover Full Lanhu Page Tree

**Files:**
- Create: `test-platform-v2/backend/app/services/lanhu_evidence/page_discovery.py`
- Modify: `test-platform-v2/backend/app/services/external/lanhu_provider.py`
- Test: `test-platform-v2/backend/tests/test_lanhu_page_discovery.py`

- [ ] **Step 1: Write failing tests**

```python
def test_parse_lanhu_url_ids():
    from app.services.lanhu_evidence.page_discovery import parse_lanhu_url

    parsed = parse_lanhu_url(
        "https://lanhuapp.com/web/#/item/project/product?"
        "tid=6324825d-1614-4d73-bc4c-f05cdf0734c1"
        "&pid=cc8cfbd5-16d2-481f-828e-7eb424a91694"
        "&versionId=26af2885-b229-4971-881c-c9bda43492fd"
        "&docId=e6b5ce1e-0d25-4e22-a9e9-450283918b3b"
        "&pageId=2b4c4235b036420787d3e856b5d133d7"
    )

    assert parsed.doc_id == "e6b5ce1e-0d25-4e22-a9e9-450283918b3b"
    assert parsed.version_id == "26af2885-b229-4971-881c-c9bda43492fd"
    assert parsed.page_id == "2b4c4235b036420787d3e856b5d133d7"
```

```python
def test_normalize_page_tree_preserves_order_and_path():
    from app.services.lanhu_evidence.page_discovery import normalize_pages

    pages = normalize_pages([
        {"id": "p1", "name": "更新日志", "path": "更新日志"},
        {"id": "p2", "name": "比赛推送", "path": "App/赛事/比赛推送"},
    ])

    assert pages[0].order_index == 0
    assert pages[1].page_id == "p2"
    assert pages[1].folder == "App/赛事"
```

- [ ] **Step 2: Implement parsing**

Use `urllib.parse` and support hash query URLs:

```python
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse


@dataclass
class LanhuUrlParts:
    url: str
    doc_id: str
    version_id: str
    page_id: str
    project_id: str
    team_id: str


def parse_lanhu_url(url: str) -> LanhuUrlParts:
    parsed = urlparse(url)
    raw = parsed.query
    if parsed.fragment and "?" in parsed.fragment:
        raw = parsed.fragment.split("?", 1)[1]
    qs = parse_qs(raw)
    def one(key: str) -> str:
        return (qs.get(key) or [""])[0]
    return LanhuUrlParts(
        url=url,
        doc_id=one("docId"),
        version_id=one("versionId"),
        page_id=one("pageId"),
        project_id=one("pid"),
        team_id=one("tid"),
    )
```

- [ ] **Step 3: Implement discovery output**

Define:

```python
@dataclass
class DiscoveredLanhuPage:
    page_id: str
    page_name: str
    page_path: str
    folder: str
    order_index: int
    page_url: str
    local_url: str = ""
```

`discover_pages(url, capture_all_pages=True)` should:

```text
1. Parse ids.
2. Use existing lanhu_provider / lanhu-mcp to download resources and get pages list.
3. If capture_all_pages=true, return all pages in sitemap order.
4. If false, return root page and its folder siblings.
5. Build page_url with original docId/versionId/pageId.
6. Build local_url if downloaded Axure html exists.
```

- [ ] **Step 4: Expose stable helper in lanhu_provider**

Add helper:

```python
async def get_lanhu_pages_for_evidence(url: str) -> dict:
    """Return downloaded resource_dir, doc metadata, and all pages for evidence capture."""
```

Return shape:

```json
{
  "status": "success",
  "resource_dir": "F:/CamelTv/test-platform-v2/backend/data/axure_extract_xxx",
  "document_name": "CamelTv 需求",
  "pages": [
    {"id": "p1", "name": "更新日志", "path": "更新日志", "filename": "更新日志.html"}
  ]
}
```

- [ ] **Step 5: Run tests**

Run:

```bash
cd test-platform-v2/backend
pytest tests/test_lanhu_page_discovery.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add test-platform-v2/backend/app/services/lanhu_evidence/page_discovery.py test-platform-v2/backend/app/services/external/lanhu_provider.py test-platform-v2/backend/tests/test_lanhu_page_discovery.py
git commit -m "feat: discover full lanhu page tree for evidence capture"
```

---

## 5. Scroll-Aware Screenshot Capture

### Task 3: Capture Full And Scrollable Pages

**Files:**
- Create: `test-platform-v2/backend/app/services/lanhu_evidence/screenshot_service.py`
- Test: `test-platform-v2/backend/tests/test_lanhu_screenshot_service.py`

- [ ] **Step 1: Write screenshot planning tests**

```python
def test_scroll_positions_cover_page_without_exceeding_limit():
    from app.services.lanhu_evidence.screenshot_service import compute_scroll_positions

    positions = compute_scroll_positions(
        scroll_height=3000,
        viewport_height=1000,
        step_ratio=0.85,
        max_segments=10,
    )

    assert positions[0] == 0
    assert positions[-1] >= 2000
    assert len(positions) <= 10
```

```python
def test_scroll_positions_for_short_page_is_single_segment():
    from app.services.lanhu_evidence.screenshot_service import compute_scroll_positions

    assert compute_scroll_positions(900, 1000, 0.85, 10) == [0]
```

- [ ] **Step 2: Implement scroll position calculation**

```python
def compute_scroll_positions(
    scroll_height: int,
    viewport_height: int,
    step_ratio: float,
    max_segments: int,
) -> list[int]:
    if scroll_height <= 0 or viewport_height <= 0:
        return [0]
    if scroll_height <= viewport_height:
        return [0]
    step = max(1, int(viewport_height * step_ratio))
    positions = [0]
    pos = 0
    while pos + viewport_height < scroll_height and len(positions) < max_segments:
        pos = min(pos + step, scroll_height - viewport_height)
        if pos != positions[-1]:
            positions.append(pos)
        else:
            break
    return positions
```

- [ ] **Step 3: Implement capture strategy**

Use Playwright:

```python
async def capture_page_segments(page_url: str, output_dir: Path, page_key: str) -> list[CaptureSegment]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": settings.lanhu_capture_viewport_width, "height": settings.lanhu_capture_viewport_height})
        await page.goto(page_url, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(settings.lanhu_capture_wait_ms)
        metrics = await page.evaluate("""() => ({
            scrollHeight: Math.max(document.body.scrollHeight, document.documentElement.scrollHeight),
            clientHeight: window.innerHeight,
            scrollWidth: Math.max(document.body.scrollWidth, document.documentElement.scrollWidth),
            clientWidth: window.innerWidth
        })""")
        positions = compute_scroll_positions(
            int(metrics["scrollHeight"]),
            int(metrics["clientHeight"]),
            settings.lanhu_capture_scroll_step_ratio,
            settings.lanhu_capture_max_segments_per_page,
        )
        segments = []
        for idx, top in enumerate(positions):
            await page.evaluate("(y) => window.scrollTo(0, y)", top)
            await page.wait_for_timeout(settings.lanhu_capture_wait_ms)
            path = output_dir / f"{page_key}-segment-{idx + 1:03d}.png"
            await page.screenshot(path=str(path), full_page=False)
            segments.append(CaptureSegment(path=path, scroll_top=top, viewport_height=int(metrics["clientHeight"])))
        await browser.close()
        return segments
```

- [ ] **Step 4: Capture inner scroll containers**

Some Axure pages scroll inside dynamic panels. Add detection:

```javascript
() => Array.from(document.querySelectorAll('*'))
  .filter(el => el.scrollHeight > el.clientHeight + 20)
  .map((el, idx) => ({
    index: idx,
    id: el.id || "",
    className: el.className || "",
    scrollHeight: el.scrollHeight,
    clientHeight: el.clientHeight
  }))
  .slice(0, 20)
```

If body scroll height is short but inner containers exist, capture the largest scroll container by scrolling it:

```python
await page.evaluate(
    """({selector, y}) => {
      const el = document.querySelector(selector);
      if (el) el.scrollTop = y;
    }""",
    {"selector": selector, "y": top},
)
```

Use `#id` selector when present; otherwise inject `data-evidence-scroll-target`.

- [ ] **Step 5: Avoid duplicate screenshots**

After each segment screenshot, compute SHA-256. If the new hash equals previous hash twice in a row, stop page capture and mark:

```json
{"duplicate_stop": true, "reason": "scroll position did not change visual content"}
```

- [ ] **Step 6: Run tests**

Run:

```bash
cd test-platform-v2/backend
pytest tests/test_lanhu_screenshot_service.py -q
```

Expected: pass deterministic planning tests. Browser capture is covered by manual smoke and optional integration test.

- [ ] **Step 7: Commit**

```bash
git add test-platform-v2/backend/app/services/lanhu_evidence/screenshot_service.py test-platform-v2/backend/tests/test_lanhu_screenshot_service.py
git commit -m "feat: capture scroll-aware lanhu page screenshots"
```

---

## 6. OCR Provider And Merge

### Task 4: OCR Provider Interface

**Files:**
- Create: `test-platform-v2/backend/app/services/lanhu_evidence/ocr_provider.py`
- Create: `test-platform-v2/backend/app/services/lanhu_evidence/local_ocr_provider.py`
- Test: `test-platform-v2/backend/tests/test_lanhu_ocr_merge.py`

- [ ] **Step 1: Write provider tests**

```python
def test_mock_ocr_provider_returns_blocks(tmp_path, monkeypatch):
    from app.services.lanhu_evidence.ocr_provider import get_ocr_provider

    monkeypatch.setattr("app.core.config.settings.lanhu_ocr_provider", "mock")
    image = tmp_path / "page.png"
    image.write_bytes(b"fake")

    result = get_ocr_provider().recognize(image)

    assert result.status == "success"
    assert result.blocks[0].text
```

- [ ] **Step 2: Define provider models**

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass
class OcrTextBlock:
    text: str
    confidence: float
    bbox: list[int]
    order_index: int


@dataclass
class OcrResult:
    status: str
    blocks: list[OcrTextBlock]
    raw_json: dict
    error_message: str = ""


class OcrProvider:
    def recognize(self, image_path: Path) -> OcrResult:
        raise NotImplementedError
```

- [ ] **Step 3: Implement mock/local providers**

Mock:

```python
class MockOcrProvider(OcrProvider):
    def recognize(self, image_path: Path) -> OcrResult:
        return OcrResult(
            status="success",
            blocks=[OcrTextBlock(text=f"MOCK OCR {image_path.name}", confidence=0.99, bbox=[0, 0, 100, 20], order_index=0)],
            raw_json={"provider": "mock"},
        )
```

Local command provider:

```python
class LocalCommandOcrProvider(OcrProvider):
    def recognize(self, image_path: Path) -> OcrResult:
        if not settings.lanhu_ocr_command:
            return OcrResult(status="unavailable", blocks=[], raw_json={}, error_message="lanhu_ocr_command 未配置")
        cmd = settings.lanhu_ocr_command.replace("{image}", str(image_path))
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            return OcrResult(status="failed", blocks=[], raw_json={"stderr": result.stderr}, error_message=result.stderr[:500])
        blocks = parse_command_output(result.stdout)
        return OcrResult(status="success", blocks=blocks, raw_json={"stdout": result.stdout[:2000]})
```

`parse_command_output` must support a simple JSON line format:

```json
{"text":"matchId 必填","confidence":0.96,"bbox":[0,0,100,20]}
```

- [ ] **Step 4: Add provider selector**

```python
def get_ocr_provider() -> OcrProvider:
    provider = settings.lanhu_ocr_provider.lower()
    if provider == "mock":
        return MockOcrProvider()
    if provider == "local":
        return LocalCommandOcrProvider()
    return LocalCommandOcrProvider()
```

- [ ] **Step 5: Run tests**

Run:

```bash
cd test-platform-v2/backend
pytest tests/test_lanhu_ocr_merge.py::test_mock_ocr_provider_returns_blocks -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add test-platform-v2/backend/app/services/lanhu_evidence/ocr_provider.py test-platform-v2/backend/app/services/lanhu_evidence/local_ocr_provider.py test-platform-v2/backend/tests/test_lanhu_ocr_merge.py
git commit -m "feat: add pluggable ocr provider for lanhu evidence"
```

### Task 5: Merge OCR And DOM Text

**Files:**
- Create: `test-platform-v2/backend/app/services/lanhu_evidence/merge_service.py`
- Test: `test-platform-v2/backend/tests/test_lanhu_ocr_merge.py`

- [ ] **Step 1: Write merge tests**

```python
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
```

```python
def test_merge_marks_low_confidence_when_ocr_empty_and_dom_short():
    from app.services.lanhu_evidence.merge_service import merge_page_text

    result = merge_page_text(page_name="空页面", dom_text="", ocr_text="")

    assert result.quality["status"] == "needs_review"
```

- [ ] **Step 2: Implement deterministic merge**

```python
@dataclass
class MergeResult:
    merged_text: str
    quality: dict


def merge_page_text(page_name: str, dom_text: str, ocr_text: str) -> MergeResult:
    dom = normalize_text(dom_text)
    ocr = normalize_text(ocr_text)
    parts = [f"# {page_name}"]
    if ocr:
        parts.extend(["", "## OCR识别文本", ocr])
    if dom and dom not in ocr:
        parts.extend(["", "## DOM/MCP文本", dom])
    merged = "\n".join(parts).strip()
    status = "success" if len(merged) >= 30 else "needs_review"
    return MergeResult(
        merged_text=merged,
        quality={
            "status": status,
            "ocr_chars": len(ocr),
            "dom_chars": len(dom),
            "merged_chars": len(merged),
            "has_ocr": bool(ocr),
            "has_dom": bool(dom),
        },
    )
```

No LLM is used in this merge step. LLM summarization happens later and never overwrites evidence.

- [ ] **Step 3: Run tests**

Run:

```bash
cd test-platform-v2/backend
pytest tests/test_lanhu_ocr_merge.py -q
```

Expected: pass.

- [ ] **Step 4: Commit**

```bash
git add test-platform-v2/backend/app/services/lanhu_evidence/merge_service.py test-platform-v2/backend/tests/test_lanhu_ocr_merge.py
git commit -m "feat: merge lanhu ocr and dom evidence text"
```

---

## 7. Word And JSON Artifacts

### Task 6: Generate Evidence Word Document

**Files:**
- Create: `test-platform-v2/backend/app/services/lanhu_evidence/word_export_service.py`
- Test: `test-platform-v2/backend/tests/test_lanhu_word_export.py`

- [ ] **Step 1: Write Word export test**

```python
def test_word_export_contains_page_titles_and_text(tmp_path):
    from app.services.lanhu_evidence.word_export_service import export_word, WordPage

    out = tmp_path / "lanhu.docx"
    export_word(
        output_path=out,
        title="蓝湖证据包",
        source_url="https://lanhuapp.com/x",
        pages=[
            WordPage(
                page_name="比赛推送",
                page_path="App/赛事/比赛推送",
                screenshots=[],
                merged_text="matchId 必填",
                quality={"status": "success"},
            )
        ],
    )

    assert out.exists()
    from docx import Document
    doc = Document(str(out))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "比赛推送" in text
    assert "matchId 必填" in text
```

- [ ] **Step 2: Implement Word export**

Use `python-docx`:

```python
@dataclass
class WordPage:
    page_name: str
    page_path: str
    screenshots: list[Path]
    merged_text: str
    quality: dict


def export_word(output_path: Path, title: str, source_url: str, pages: list[WordPage]) -> Path:
    doc = Document()
    doc.add_heading(title, level=0)
    doc.add_paragraph(f"来源链接：{source_url}")
    doc.add_paragraph(f"页面数量：{len(pages)}")
    for idx, page in enumerate(pages, start=1):
        doc.add_page_break()
        doc.add_heading(f"{idx}. {page.page_name}", level=1)
        doc.add_paragraph(f"路径：{page.page_path}")
        doc.add_paragraph(f"质量状态：{page.quality.get('status', '')}")
        for shot in page.screenshots:
            if shot.exists():
                doc.add_paragraph(f"截图：{shot.name}")
                doc.add_picture(str(shot), width=Inches(6.5))
        doc.add_heading("识别文本", level=2)
        for line in page.merged_text.splitlines():
            doc.add_paragraph(line)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    return output_path
```

- [ ] **Step 3: Run tests**

Run:

```bash
cd test-platform-v2/backend
pytest tests/test_lanhu_word_export.py -q
```

Expected: pass.

- [ ] **Step 4: Commit**

```bash
git add test-platform-v2/backend/app/services/lanhu_evidence/word_export_service.py test-platform-v2/backend/tests/test_lanhu_word_export.py
git commit -m "feat: export lanhu evidence pack to word"
```

### Task 7: Generate Normalized JSON

**Files:**
- Create: `test-platform-v2/backend/app/services/lanhu_evidence/json_export_service.py`
- Test: `test-platform-v2/backend/tests/test_lanhu_word_export.py`

- [ ] **Step 1: Write JSON export test**

```python
def test_json_export_contains_source_refs(tmp_path):
    from app.services.lanhu_evidence.json_export_service import export_json

    out = tmp_path / "lanhu.json"
    export_json(
        output_path=out,
        job={
            "job_id": 1,
            "source_url": "https://lanhuapp.com/x",
            "doc_id": "d",
            "version_id": "v",
        },
        pages=[{
            "page_id": "p1",
            "page_name": "比赛推送",
            "page_path": "App/赛事/比赛推送",
            "merged_text": "matchId 必填",
            "screenshots": ["pages/p1/segment-001.png"],
            "quality": {"status": "success"},
        }],
    )

    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["doc_id"] == "d"
    assert data["pages"][0]["source_refs"]["page_id"] == "p1"
```

- [ ] **Step 2: Implement JSON export**

Required shape:

```json
{
  "job_id": 1,
  "source_type": "lanhu_evidence_pack",
  "source_url": "...",
  "doc_id": "...",
  "version_id": "...",
  "page_count": 10,
  "pages": [
    {
      "page_id": "p1",
      "page_name": "比赛推送",
      "page_path": "App/赛事/比赛推送",
      "merged_text": "matchId 必填",
      "screenshots": ["pages/p1/segment-001.png"],
      "quality": {"status": "success"},
      "source_refs": {
        "doc_id": "...",
        "version_id": "...",
        "page_id": "p1"
      }
    }
  ]
}
```

- [ ] **Step 3: Run tests**

Run:

```bash
cd test-platform-v2/backend
pytest tests/test_lanhu_word_export.py -q
```

Expected: pass.

- [ ] **Step 4: Commit**

```bash
git add test-platform-v2/backend/app/services/lanhu_evidence/json_export_service.py test-platform-v2/backend/tests/test_lanhu_word_export.py
git commit -m "feat: export lanhu evidence pack to json"
```

---

## 8. Job Runner And API

### Task 8: Evidence Job Runner

**Files:**
- Create: `test-platform-v2/backend/app/services/lanhu_evidence/job_runner.py`
- Modify: `test-platform-v2/backend/app/services/lanhu_evidence/import_service.py`
- Test: `test-platform-v2/backend/tests/test_lanhu_evidence_import.py`

- [ ] **Step 1: Write runner transition test**

```python
def test_job_runner_marks_job_failed_when_discovery_fails(db, monkeypatch):
    from app.models.lanhu_evidence import LanhuEvidenceJob
    from app.services.lanhu_evidence.job_runner import run_job_in_new_session

    job = LanhuEvidenceJob(project_id=1, source_url="bad", status="pending", storage_dir="x")
    db.add(job)
    db.commit()

    monkeypatch.setattr(
        "app.services.lanhu_evidence.page_discovery.discover_pages",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("invalid url")),
    )

    run_job_in_new_session(job.id, project_id=1)
    db.refresh(job)

    assert job.status == "failed"
    assert "invalid url" in job.error_message
```

- [ ] **Step 2: Implement runner stages**

Stages:

```text
discovering
capturing
ocr
merging
exporting
importing
success
failed
cancelled
```

Runner algorithm:

```python
def run_job_in_new_session(job_id: int, project_id: int) -> None:
    db = SessionLocal()
    try:
        job = load_and_mark_running(db, job_id, project_id)
        pages = discover_pages(job.source_url, capture_all_pages=True)
        persist_pages(db, job, pages)
        for page in pages:
            check_cancelled(db, job)
            capture screenshots
            run OCR for each screenshot
            merge OCR + DOM text
            persist page assets and blocks
        export Word
        export JSON
        run optional imports
        mark success
    except Cancelled:
        mark cancelled
    except Exception as e:
        mark failed
    finally:
        db.close()
```

- [ ] **Step 3: Add completeness validation**

Job quality JSON must include:

```json
{
  "page_count": 10,
  "captured_pages": 10,
  "ocr_pages": 10,
  "failed_pages": 0,
  "pages_needing_review": [],
  "complete": true
}
```

If any page has no screenshot or no merged text, mark `complete=false` and keep job `success_with_warnings` instead of `success`.

- [ ] **Step 4: Run tests**

Run:

```bash
cd test-platform-v2/backend
pytest tests/test_lanhu_evidence_import.py -q
```

Expected: runner state tests pass.

- [ ] **Step 5: Commit**

```bash
git add test-platform-v2/backend/app/services/lanhu_evidence/job_runner.py test-platform-v2/backend/app/services/lanhu_evidence/import_service.py test-platform-v2/backend/tests/test_lanhu_evidence_import.py
git commit -m "feat: orchestrate lanhu evidence pack jobs"
```

### Task 9: Evidence API

**Files:**
- Create: `test-platform-v2/backend/app/api/v1/lanhu_evidence.py`
- Modify: `test-platform-v2/backend/app/main.py`
- Modify: `test-platform-v2/backend/app/seed.py`
- Test: `test-platform-v2/backend/tests/test_lanhu_evidence_import.py`

- [ ] **Step 1: Add permissions**

Add to seed:

```python
("lanhu_evidence:view", "查看蓝湖证据包", "button"),
("lanhu_evidence:run", "创建蓝湖证据包", "button"),
("lanhu_evidence:import", "导入蓝湖证据包", "button"),
```

Tester default:

```text
lanhu_evidence:view
lanhu_evidence:run
```

Admin:

```text
all three permissions
```

- [ ] **Step 2: Implement API**

Routes:

```http
POST /api/v1/lanhu-evidence/jobs
GET  /api/v1/lanhu-evidence/jobs
GET  /api/v1/lanhu-evidence/jobs/{job_id}
POST /api/v1/lanhu-evidence/jobs/{job_id}/cancel
POST /api/v1/lanhu-evidence/jobs/{job_id}/retry
GET  /api/v1/lanhu-evidence/jobs/{job_id}/pages
GET  /api/v1/lanhu-evidence/pages/{page_id}
GET  /api/v1/lanhu-evidence/assets/{asset_id}
POST /api/v1/lanhu-evidence/jobs/{job_id}/import
```

`POST /jobs`:

```python
@router.post("/jobs", response_model=R[LanhuEvidenceJobOut])
def create_job(
    body: LanhuEvidenceCreateRequest,
    background_tasks: BackgroundTasks,
    current: CurrentUser = Depends(require_permission("lanhu_evidence:run")),
    db: Session = Depends(get_db),
):
    if not settings.lanhu_evidence_enabled:
        raise APIException(code=503, msg="蓝湖证据包未启用（lanhu_evidence_enabled=False）", http_status=503)
    job = LanhuEvidenceJob(
        project_id=current.project_id or 0,
        source_url=body.url,
        status="pending",
        stage="queued",
        creator_id=current.user.id,
        storage_dir=resolve_job_storage_dir(),
    )
    db.add(job)
    db.commit()
    background_tasks.add_task(job_runner.run_job_in_new_session, job.id, current.project_id or 0)
    return R.ok(LanhuEvidenceJobOut.model_validate(job))
```

- [ ] **Step 3: Project isolation for asset download**

Asset download must verify:

```text
asset.project_id == current.project_id
resolved file path starts with job.storage_dir
```

- [ ] **Step 4: Register router**

In `main.py` include:

```python
from app.api.v1 import lanhu_evidence
app.include_router(lanhu_evidence.router, prefix="/api/v1")
```

- [ ] **Step 5: Run tests**

Run:

```bash
cd test-platform-v2/backend
pytest tests/test_lanhu_evidence_import.py -q
```

Expected: API creation, view, project isolation, and disabled switch tests pass.

- [ ] **Step 6: Commit**

```bash
git add test-platform-v2/backend/app/api/v1/lanhu_evidence.py test-platform-v2/backend/app/main.py test-platform-v2/backend/app/seed.py test-platform-v2/backend/tests/test_lanhu_evidence_import.py
git commit -m "feat: expose lanhu evidence pack api"
```

---

## 9. Import To Requirement / RAG / Wiki

### Task 10: Evidence Pack Import Service

**Files:**
- Create: `test-platform-v2/backend/app/services/lanhu_evidence/import_service.py`
- Modify: `test-platform-v2/backend/app/services/requirement_service.py`
- Modify: `test-platform-v2/backend/app/services/knowledge/ingest_service.py`
- Modify: `test-platform-v2/backend/app/services/wiki/import_service.py`
- Test: `test-platform-v2/backend/tests/test_lanhu_evidence_import.py`

- [ ] **Step 1: Write import tests**

```python
def test_import_evidence_to_requirement_creates_doc(db, evidence_job_factory):
    from app.services.lanhu_evidence.import_service import import_to_requirement

    job = evidence_job_factory(
        project_id=1,
        word_path="storage/lanhu-evidence/1/lanhu.docx",
        json_path="storage/lanhu-evidence/1/lanhu.json",
        status="success",
    )

    doc = import_to_requirement(db, project_id=1, job_id=job.id, creator_id=1)

    assert doc["file_type"] == "docx"
    assert "蓝湖证据包" in doc["title"]
```

```python
def test_import_evidence_to_knowledge_preserves_source_refs(db, evidence_job_with_pages):
    from app.services.lanhu_evidence.import_service import import_to_knowledge

    source_id = import_to_knowledge(db, project_id=1, job_id=evidence_job_with_pages.id)

    assert source_id is not None
```

- [ ] **Step 2: Import to requirement**

Behavior:

```text
1. Read job.word_path.
2. Parse docx with existing parse_docx.
3. Create RequirementDocument with file_type="docx".
4. source_ref should be original Lanhu URL.
5. metadata should include evidence_job_id and json_path.
```

- [ ] **Step 3: Import to RAG**

Use `source_service.record_source`:

```python
source_type="lanhu_evidence"
source_ref=job.source_url
title=f"蓝湖证据包 {job.document_name or job.doc_id}"
metadata={
  "evidence_job_id": job.id,
  "word_path": job.word_path,
  "json_path": job.json_path,
  "doc_id": job.doc_id,
  "version_id": job.version_id
}
```

Chunks should be page-scoped:

```text
chunk_type=requirement_page
title={page.page_path}
content={page.merged_text}
tags=["lanhu", "ocr", page.folder]
```

- [ ] **Step 4: Import to Wiki**

Create or reuse `WikiRawSource`:

```text
source_type=lanhu_evidence
source_ref=job.source_url
content_md=all page merged_text joined by page headings
immutable_version=lanhu-evidence:{doc_id}:{version_id}:{job_id}
metadata_json includes evidence_job_id, word_path, json_path
```

Then create `WikiIngestJob` when `wiki_enabled=true`.

- [ ] **Step 5: Run tests**

Run:

```bash
cd test-platform-v2/backend
pytest tests/test_lanhu_evidence_import.py -q
```

Expected: imports create project-scoped requirement, knowledge source/chunks, and raw source.

- [ ] **Step 6: Commit**

```bash
git add test-platform-v2/backend/app/services/lanhu_evidence/import_service.py test-platform-v2/backend/app/services/requirement_service.py test-platform-v2/backend/app/services/knowledge/ingest_service.py test-platform-v2/backend/app/services/wiki/import_service.py test-platform-v2/backend/tests/test_lanhu_evidence_import.py
git commit -m "feat: import lanhu evidence packs into requirement rag and wiki"
```

---

## 10. Frontend Workflow

### Task 11: Evidence Pack UI

**Files:**
- Create: `test-platform-v2/frontend/src/api/lanhuEvidence.ts`
- Create: `test-platform-v2/frontend/src/pages/knowledge/components/LanhuEvidenceDialog.tsx`
- Create: `test-platform-v2/frontend/src/pages/knowledge/components/LanhuEvidenceJobDrawer.tsx`
- Modify: `test-platform-v2/frontend/src/pages/knowledge/components/WikiImportDialog.tsx`
- Modify: `test-platform-v2/frontend/src/pages/requirement/index.tsx`
- Modify: `test-platform-v2/frontend/src/types/index.ts`
- Test: `test-platform-v2/frontend/src/pages/knowledge/components/__tests__/LanhuEvidenceDialog.test.tsx`

- [ ] **Step 1: Add API client**

```ts
export interface LanhuEvidenceCreateRequest {
  url: string
  capture_all_pages: boolean
  include_word: boolean
  include_json: boolean
  import_to_requirement: boolean
  import_to_knowledge: boolean
  import_to_wiki: boolean
}

export async function createLanhuEvidenceJob(body: LanhuEvidenceCreateRequest) {
  return api.post('/lanhu-evidence/jobs', body)
}

export async function fetchLanhuEvidenceJob(jobId: number) {
  return api.get(`/lanhu-evidence/jobs/${jobId}`)
}

export async function fetchLanhuEvidencePages(jobId: number) {
  return api.get(`/lanhu-evidence/jobs/${jobId}/pages`)
}
```

- [ ] **Step 2: Add dialog**

Dialog controls:

```text
Lanhu URL input
capture all pages switch default true
include Word switch default true
include JSON switch default true
import to requirement switch
import to RAG switch
import to Wiki switch
submit button
```

No marketing copy. Keep it operational.

- [ ] **Step 3: Add job drawer**

Drawer shows:

```text
status/stage
page counts
captured_pages / total_pages
ocr_pages / total_pages
failed_pages
quality complete flag
download Word
download JSON
page list with screenshot count and OCR status
retry/cancel actions
```

- [ ] **Step 4: Wire Knowledge Center**

In `WikiImportDialog`, add button:

```text
使用证据包 OCR 导入
```

This opens `LanhuEvidenceDialog` and pre-fills the current URL.

- [ ] **Step 5: Wire Requirement Upload Lanhu tab**

In `frontend/src/pages/requirement/index.tsx`, submitting a Lanhu URL should offer:

```text
快速链接导入
证据包 OCR 导入（推荐）
```

Default to evidence pack import when `lanhu_evidence_enabled=true`.

- [ ] **Step 6: Run frontend checks**

Run:

```bash
cd test-platform-v2/frontend
npm test -- LanhuEvidenceDialog
npm run typecheck
```

Expected: tests and typecheck pass.

- [ ] **Step 7: Commit**

```bash
git add test-platform-v2/frontend/src/api/lanhuEvidence.ts test-platform-v2/frontend/src/pages/knowledge/components/LanhuEvidenceDialog.tsx test-platform-v2/frontend/src/pages/knowledge/components/LanhuEvidenceJobDrawer.tsx test-platform-v2/frontend/src/pages/knowledge/components/WikiImportDialog.tsx test-platform-v2/frontend/src/pages/requirement/index.tsx test-platform-v2/frontend/src/types/index.ts test-platform-v2/frontend/src/pages/knowledge/components/__tests__/LanhuEvidenceDialog.test.tsx
git commit -m "feat: add lanhu evidence pack import UI"
```

---

## 11. Manual Acceptance

### Task 12: Real Lanhu Smoke

**Files:**
- Update: `test-platform-v2/docs/LLM-Wiki知识库差异对比能力落地方案.md`
- Update: `test-platform-v2/docs/RAG知识图谱与Agent持续学习能力落地执行文档.md`

- [ ] **Step 1: Prepare environment**

Set:

```bash
LANHU_EVIDENCE_ENABLED=true
LANHU_OCR_PROVIDER=mock
```

For real OCR, set:

```bash
LANHU_OCR_PROVIDER=local
LANHU_OCR_COMMAND="your-ocr-command --json {image}"
```

Expected OCR command output line format:

```json
{"text":"比赛推送","confidence":0.96,"bbox":[0,0,100,20]}
```

- [ ] **Step 2: Start backend and frontend**

```bash
cd test-platform-v2/backend
uvicorn app.main:app --reload

cd ../frontend
npm run dev
```

- [ ] **Step 3: Run evidence import with provided Lanhu URL**

Use:

```text
https://lanhuapp.com/web/#/item/project/product?tid=6324825d-1614-4d73-bc4c-f05cdf0734c1&pid=cc8cfbd5-16d2-481f-828e-7eb424a91694&versionId=26af2885-b229-4971-881c-c9bda43492fd&docId=e6b5ce1e-0d25-4e22-a9e9-450283918b3b&docType=axure&image_id=e6b5ce1e-0d25-4e22-a9e9-450283918b3b&pageId=2b4c4235b036420787d3e856b5d133d7&corpId=null
```

Options:

```text
capture_all_pages=true
include_word=true
include_json=true
import_to_requirement=true
import_to_knowledge=true
import_to_wiki=true
```

- [ ] **Step 4: Verify completeness**

Expected:

```text
job.status is success or success_with_warnings
job.total_pages > 0
job.captured_pages == job.total_pages
job.word_path exists
job.json_path exists
each page has at least one screenshot asset
scrollable pages have segment_count > 1
Word chapter count equals total_pages
JSON pages length equals total_pages
```

- [ ] **Step 5: Verify imports**

Expected:

```text
Requirement document created from evidence Word
KnowledgeSource source_type=lanhu_evidence exists
KnowledgeChunk rows are page-scoped
WikiRawSource source_type=lanhu_evidence exists
WikiIngestJob is created when wiki_enabled=true
```

- [ ] **Step 6: Update docs**

Document operational usage:

```text
证据包导入适用于正式需求沉淀。
原 lanhu-mcp 文本导入仅保留为快速预览/降级路径。
Word 用于人审，JSON/RAG/Wiki 使用证据包元数据作为追溯源。
```

- [ ] **Step 7: Commit**

```bash
git add test-platform-v2/docs/LLM-Wiki知识库差异对比能力落地方案.md test-platform-v2/docs/RAG知识图谱与Agent持续学习能力落地执行文档.md
git commit -m "docs: document lanhu evidence pack workflow"
```

---

## 12. Release Gates

Backend:

```bash
cd test-platform-v2/backend
pytest tests/test_lanhu_evidence_models.py tests/test_lanhu_page_discovery.py tests/test_lanhu_screenshot_service.py tests/test_lanhu_ocr_merge.py tests/test_lanhu_word_export.py tests/test_lanhu_evidence_import.py -q
```

Frontend:

```bash
cd test-platform-v2/frontend
npm test -- LanhuEvidenceDialog
npm run typecheck
npm run build
```

Manual:

```text
Use the provided Lanhu URL.
Run one evidence job.
Download Word.
Open Word and verify every discovered page has a chapter and screenshot.
Open JSON and verify every page has source_refs.doc_id/version_id/page_id.
Verify RAG/Wiki imports reference evidence_job_id.
```

---

## 13. Definition Of Done

- A Lanhu URL can start an evidence capture job without blocking the request.
- The job discovers the full Lanhu page tree, not only the input `pageId`.
- Each page has screenshot evidence.
- Scrollable pages are captured in multiple viewport segments when needed.
- OCR runs per screenshot segment through a provider interface.
- DOM/MCP text and OCR text are merged without losing raw evidence.
- Word output includes every page title, path, screenshots, merged text, and quality status.
- JSON output includes every page, screenshots, merged text, and source references.
- Import to requirement creates a normal requirement document from the generated Word.
- Import to RAG creates page-scoped chunks with evidence metadata.
- Import to Wiki creates `WikiRawSource` and can trigger Wiki compilation.
- Every generated requirement/chunk/Wiki source can trace back to `evidence_job_id`, page id, and screenshot asset.
- Jobs are project scoped, permission protected, cancellable, retryable, and auditable.
- Existing direct `lanhu-mcp` extraction remains available as a fast preview/degraded path, but formal RAG/Wiki/requirement ingestion uses the evidence pack path.
