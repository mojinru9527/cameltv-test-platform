# P0/P1 Reliability and Security Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Lanhu evidence imports trustworthy and recoverable, eliminate the confirmed Agent queue database-lock failure, close cross-project access paths, and make UI/API automation artifacts and CRUD lifecycle deterministic.

**Architecture:** Formal Lanhu import becomes a gated state machine: capture evidence first, calculate an auditable quality report, require OCR-or-human-review coverage for every page, then permit downstream Requirement/RAG/Wiki import. Evidence jobs move from request-bound `BackgroundTasks` to the existing persistent scheduler worker, with heartbeat-based stale-job recovery. Cross-project operations derive the project exclusively from `CurrentUser`; resource lookups must scope by `project_id` in the database query.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Alembic, SQLite WAL with PostgreSQL compatibility, APScheduler, Playwright, python-docx, pytest, React/TypeScript.

---

## 0. Non-Negotiable Behaviour

The following contract is the release boundary. Do not weaken it for convenience.

| Area | Required outcome |
| --- | --- |
| Evidence completion | `success` means every discovered page has at least one screenshot, non-truncated capture, non-empty merged text, and either successful OCR or an explicit human approval. |
| Formal import | Requirement, Knowledge, and Wiki import is allowed only for a job whose quality report has `import_ready=true`. `success_with_warnings` returns HTTP 409. |
| Capture failure | A job with zero screenshots must be `failed`, not `success_with_warnings`, and it must create neither Word/JSON nor downstream records. |
| Restart recovery | A `running` job without a heartbeat for more than 10 minutes becomes `failed` with `worker_lost`; retry creates a fresh attempt and never mixes old assets with new assets. |
| Project isolation | A caller cannot read, generate from, update, delete, import, or lint another project through a path, body, or query value. |
| Artifact isolation | A UI run only reports artifacts written under that run's own `storage/ui-runs/{run_id}` directory. |

## 1. File Structure

- Modify: `backend/app/models/lanhu_evidence.py`
  - Add immutable attempt linkage, requested options, heartbeat, and page review/capture quality fields.
- Create: `backend/alembic/versions/20260714_lanhu_evidence_quality_recovery.py`
  - Add columns and indexes without destructive migration.
- Create: `backend/alembic/versions/20260714_lanhu_evidence_pg_reconcile.py`
  - Reconcile composite indexes skipped by historical auto-create deployments and set PostgreSQL server defaults for non-null quality/recovery columns.
- Modify: `backend/app/schemas/lanhu_evidence.py`
  - Expose quality, page review, asset download, and effective job options.
- Modify: `backend/app/services/lanhu_evidence/job_runner.py`
  - Calculate strict quality, update heartbeat, honor request options, register Word/JSON assets, and run auto-import only after the quality gate.
- Modify: `backend/app/services/lanhu_evidence/screenshot_service.py`
  - Return `truncated` and capture diagnostics when max segments prevents full coverage.
- Create: `backend/app/services/lanhu_evidence/worker.py`
  - Atomically claim pending jobs, recover stale jobs, and run capture in an isolated session.
- Modify: `backend/app/services/task_worker.py`
  - Poll one evidence job per configured evidence worker slot.
- Modify: `backend/app/api/v1/lanhu_evidence.py`
  - Stop using `BackgroundTasks`, add page review, strict import response, and asset-backed document download.
- Modify: `backend/app/services/knowledge/agent_queue.py`
  - Use one caller-owned transaction for enqueue and retry transient SQLite locking before returning a controlled API error.
- Modify: `backend/app/api/v1/agent.py`
  - Pass the request session to the enqueue service and map exhausted lock retries to HTTP 503.
- Modify: `backend/app/services/playwright_executor.py`
  - Use a thread semaphore and remove all shared-directory artifact copying.
- Modify: `backend/app/api/v1/apitest.py`
  - Scope generated endpoint assets by the current project and add deletion routes.
- Modify: `backend/app/api/v1/wiki.py`
  - Permit `project_id_override` only for a super administrator.
- Modify: `backend/app/seed.py`
  - Add `lanhu_evidence:review` permission.
- Modify: `frontend/src/api/lanhuEvidence.ts`
  - Add page-review and asset DTOs.
- Modify: `frontend/src/pages/knowledge/components/LanhuEvidenceJobDrawer.tsx`
  - Show import readiness and per-page review actions; download by asset endpoint rather than physical paths.
- Tests: `backend/tests/test_lanhu_evidence_import.py`, `backend/tests/test_lanhu_screenshot_service.py`, `backend/tests/test_postgres_migration_reconcile.py`, `backend/tests/test_agent_permissions.py`, `backend/tests/test_apitest_project_isolation.py`, `backend/tests/test_playwright_executor.py`, `backend/tests/test_wiki_api.py`, `frontend/src/pages/knowledge/components/__tests__/LanhuEvidenceJobDrawer.test.tsx`.

## 2. Delivery Order

1. P0-A: Evidence quality gate and import block.
2. P0-B: Persistent evidence worker and stale-job recovery.
3. P0-C: Agent queue write reliability.
4. P1-A: UI artifact isolation and real concurrency cap.
5. P1-B: API asset project isolation and delete lifecycle.
6. P1-C: Wiki cross-project lint authorization.
7. P1-D: Frontend contract and release verification.

### Task 1: Persist Evidence Quality and Request Options

**Files:**
- Modify: `backend/app/models/lanhu_evidence.py`
- Create: `backend/alembic/versions/20260714_lanhu_evidence_quality_recovery.py`
- Create: `backend/alembic/versions/20260714_lanhu_evidence_pg_reconcile.py`
- Modify: `backend/app/schemas/lanhu_evidence.py`
- Test: `backend/tests/test_lanhu_evidence_models.py`
- Test: `backend/tests/test_postgres_migration_reconcile.py`

- [x] **Step 1: Write failing model tests**

```python
def test_evidence_job_persists_requested_options_and_heartbeat(db_session):
    from app.models.lanhu_evidence import LanhuEvidenceJob

    job = LanhuEvidenceJob(
        project_id=1,
        source_url="https://lanhuapp.com/x?docId=d",
        requested_options_json='{"capture_all_pages":false,"include_word":false}',
        attempt_no=1,
    )
    db_session.add(job)
    db_session.commit()
    assert job.attempt_no == 1
    assert "include_word" in job.requested_options_json
    assert job.heartbeat_at is None


def test_evidence_page_requires_explicit_review_for_ocr_waiver(db_session):
    from app.models.lanhu_evidence import LanhuEvidencePage

    page = LanhuEvidencePage(job_id=1, project_id=1, page_id="p1")
    db_session.add(page)
    db_session.commit()
    assert page.review_status == "pending"
    assert page.capture_truncated is False
```

- [x] **Step 2: Run the focused test**

Run: `cd backend && pytest tests/test_lanhu_evidence_models.py -q`

Expected: failure because the new columns do not exist.

- [x] **Step 3: Add the model fields and migration**

Add these fields to `LanhuEvidenceJob`:

```python
parent_job_id: Mapped[int | None] = mapped_column(default=None, index=True)
attempt_no: Mapped[int] = mapped_column(default=1)
requested_options_json: Mapped[str] = mapped_column(Text, default="{}")
import_result_json: Mapped[str] = mapped_column(Text, default="{}")
heartbeat_at: Mapped[datetime | None] = mapped_column(default=None, index=True)
```

Add these fields to `LanhuEvidencePage`:

```python
capture_truncated: Mapped[bool] = mapped_column(default=False)
review_status: Mapped[str] = mapped_column(default="pending", index=True)
reviewer_id: Mapped[int] = mapped_column(default=0)
review_comment: Mapped[str] = mapped_column(Text, default="")
reviewed_at: Mapped[datetime | None] = mapped_column(default=None)
```

The migration must add the columns using `batch_alter_table` for SQLite and create these indexes:

```python
op.create_index("ix_lanhu_evidence_job_status_heartbeat", "lanhu_evidence_job", ["status", "heartbeat_at"])
op.create_index("ix_lanhu_evidence_page_job_review", "lanhu_evidence_page", ["job_id", "review_status"])
```

- [x] **Step 4: Expose safe DTO fields**

Add to `LanhuEvidenceJobOut`: `attempt_no`, `parent_job_id`, `import_result_json`, `heartbeat_at`. Add to `LanhuEvidencePageOut`: `capture_truncated`, `review_status`, `review_comment`, `reviewed_at`.

Do not expose absolute file paths in response schemas.

- [x] **Step 5: Run migration and tests**

Run:

```bash
cd backend
alembic upgrade head
pytest tests/test_lanhu_evidence_models.py -q
```

Expected: migration succeeds and all model tests pass.

- [x] **Step 6: Commit**

```bash
git add backend/app/models/lanhu_evidence.py backend/app/schemas/lanhu_evidence.py backend/alembic/versions/20260714_lanhu_evidence_quality_recovery.py backend/tests/test_lanhu_evidence_models.py
git commit -m "feat: persist lanhu evidence quality and recovery state"
```

### Task 2: Enforce Evidence Quality Before Export or Import

**Files:**
- Create: `backend/app/services/lanhu_evidence/quality_service.py`
- Modify: `backend/app/services/lanhu_evidence/job_runner.py`
- Modify: `backend/app/api/v1/lanhu_evidence.py`
- Modify: `backend/app/services/lanhu_evidence/import_service.py`
- Test: `backend/tests/test_lanhu_evidence_import.py`

- [x] **Step 1: Write the failing quality tests**

```python
def test_quality_is_not_import_ready_when_any_page_has_no_ocr_or_review():
    from app.services.lanhu_evidence.quality_service import evaluate_job_quality

    report = evaluate_job_quality([
        {"capture_status": "success", "segment_count": 1, "capture_truncated": False,
         "merged_text": "x" * 50, "ocr_status": "success", "review_status": "pending"},
        {"capture_status": "success", "segment_count": 1, "capture_truncated": False,
         "merged_text": "x" * 50, "ocr_status": "unavailable", "review_status": "pending"},
    ])

    assert report["complete"] is False
    assert report["import_ready"] is False
    assert report["pages_missing_ocr_review"] == [1]


def test_import_rejects_warning_job(client, auth_headers, db_session):
    from app.models.lanhu_evidence import LanhuEvidenceJob
    job = LanhuEvidenceJob(project_id=1, status="success_with_warnings", quality_json='{"import_ready":false}')
    db_session.add(job)
    db_session.commit()
    response = client.post(f"/api/v1/lanhu-evidence/jobs/{job.id}/import", headers=auth_headers, json={"import_to_requirement": True})
    assert response.status_code == 409
```

- [x] **Step 2: Implement one pure quality evaluator**

Create `quality_service.py` with this contract:

```python
def evaluate_job_quality(pages: list[dict]) -> dict:
    missing_capture = []
    truncated = []
    missing_text = []
    missing_ocr_review = []
    for index, page in enumerate(pages):
        if page["capture_status"] != "success" or int(page["segment_count"]) < 1:
            missing_capture.append(index)
        if page.get("capture_truncated"):
            truncated.append(index)
        if not str(page.get("merged_text") or "").strip():
            missing_text.append(index)
        if page.get("ocr_status") != "success" and page.get("review_status") != "approved":
            missing_ocr_review.append(index)
    complete = bool(pages) and not (missing_capture or truncated or missing_text or missing_ocr_review)
    return {
        "page_count": len(pages),
        "complete": complete,
        "import_ready": complete,
        "pages_missing_capture": missing_capture,
        "pages_truncated": truncated,
        "pages_missing_text": missing_text,
        "pages_missing_ocr_review": missing_ocr_review,
    }
```

- [x] **Step 3: Make runner honor actual request options**

At creation, serialize all `LanhuEvidenceCreateRequest` fields into `requested_options_json`. In `job_runner`, load them once:

```python
options = json.loads(job.requested_options_json or "{}")
capture_all_pages = bool(options.get("capture_all_pages", True))
include_word = bool(options.get("include_word", True))
include_json = bool(options.get("include_json", True))
```

Pass `capture_all_pages` to discovery. Export Word only when `include_word`; export JSON only when `include_json`. Do not run any configured auto-import until `quality["import_ready"]` is true.

- [x] **Step 4: Change state outcomes and import guard**

Use this exact result mapping after page processing:

```python
quality = evaluate_job_quality(page_dicts)
job.quality_json = json.dumps(quality, ensure_ascii=False)
if quality["complete"]:
    job.status = "success"
elif job.captured_pages == 0:
    job.status = "failed"
    job.error_message = "No Lanhu page screenshot was captured"
else:
    job.status = "success_with_warnings"
```

In `import_job`, parse `quality_json` and require both `job.status == "success"` and `quality["import_ready"] is True`; otherwise raise `APIException` with both application code and HTTP status set to 409. `import_to_requirement`, `import_to_knowledge`, and `import_to_wiki` must all enter through `import_service._load_job_and_pages`, which calls `import_service._ensure_import_ready` before returning page data. `import_service.execute_requested_imports` is the only dispatcher and executes exactly the three persisted request flags that are true.

- [x] **Step 5: Add page-review endpoint**

Add `POST /api/v1/lanhu-evidence/pages/{page_id}/review` with body:

```python
class LanhuEvidencePageReviewRequest(BaseModel):
    approved: bool
    comment: str = Field(min_length=3, max_length=1000)
```

Require `lanhu_evidence:review`, scope the page by `current.project_id`, and only allow approval for pages with a screenshot and non-empty merged text. Set `review_status`, `reviewer_id`, `review_comment`, and `reviewed_at`. Re-evaluate the parent job quality after every review.

- [x] **Step 6: Run tests**

Run:

```bash
cd backend
pytest tests/test_lanhu_evidence_import.py tests/test_lanhu_ocr_merge.py -q
```

Expected: warning jobs cannot import; OCR-unavailable pages require recorded human approval; zero-capture jobs fail.

- [x] **Step 7: Commit**

```bash
git add backend/app/services/lanhu_evidence/quality_service.py backend/app/services/lanhu_evidence/job_runner.py backend/app/services/lanhu_evidence/import_service.py backend/app/api/v1/lanhu_evidence.py backend/tests/test_lanhu_evidence_import.py
git commit -m "fix: gate lanhu imports on verified evidence quality"
```

### Task 3: Detect Scroll Truncation and Register Export Assets

**Files:**
- Modify: `backend/app/services/lanhu_evidence/screenshot_service.py`
- Modify: `backend/app/services/lanhu_evidence/job_runner.py`
- Modify: `backend/app/api/v1/lanhu_evidence.py`
- Test: `backend/tests/test_lanhu_screenshot_service.py`
- Test: `backend/tests/test_lanhu_evidence_import.py`

- [x] **Step 1: Write failing truncation and asset tests**

```python
def test_capture_marks_truncated_when_max_segments_cannot_reach_last_position():
    from app.services.lanhu_evidence.screenshot_service import capture_plan
    plan = capture_plan(scroll_height=10000, viewport_height=1000, step_ratio=0.85, max_segments=3)
    assert plan.truncated is True
    assert plan.positions == [0, 850, 1700]


def test_runner_registers_word_and_json_assets(db_session, monkeypatch, tmp_path):
    from app.models.lanhu_evidence import LanhuEvidenceAsset

    job_id = _run_mocked_job(
        db_session,
        monkeypatch,
        tmp_path,
        options='{"capture_all_pages": true, "include_word": true, "include_json": true}',
    )
    assets = db_session.query(LanhuEvidenceAsset).filter_by(job_id=job_id).all()
    assert {"screenshot", "word", "json"} <= {asset.asset_type for asset in assets}
    assert all(not asset.relative_path.startswith("/") for asset in assets)
```

- [x] **Step 2: Return a capture plan with truncation state**

Replace the bare list helper with:

```python
@dataclass(frozen=True)
class CapturePlan:
    positions: list[int]
    truncated: bool

def capture_plan(scroll_height: int, viewport_height: int, step_ratio: float, max_segments: int) -> CapturePlan:
    positions = compute_scroll_positions(scroll_height, viewport_height, step_ratio, max_segments)
    last_required = max(0, scroll_height - viewport_height)
    return CapturePlan(positions=positions, truncated=positions[-1] < last_required)
```

Store `CapturePlan.truncated` in `CaptureResult`, then set `row.capture_truncated = cap.truncated` in the runner. A duplicate screenshot stop is not complete unless its final scroll position equals `last_required`.

- [x] **Step 3: Create Word and JSON asset records**

After each successful export, call a local runner helper:

```python
def register_job_asset(db, job, path: Path, asset_type: str, mime_type: str) -> LanhuEvidenceAsset:
    asset = LanhuEvidenceAsset(
        job_id=job.id, page_id=None, project_id=job.project_id,
        asset_type=asset_type, file_path=str(path),
        relative_path=str(path.relative_to(Path(job.storage_dir))),
        mime_type=mime_type, sha256=_sha256_file(path),
    )
    db.add(asset)
    return asset
```

Use `asset_type="word"` / MIME `application/vnd.openxmlformats-officedocument.wordprocessingml.document` and `asset_type="json"` / MIME `application/json`.

- [x] **Step 4: Keep document download within asset authorization**

Do not return `word_path` or `json_path` to the browser. Add `GET /jobs/{job_id}/assets` returning `LanhuEvidenceAssetOut` items. The existing `GET /assets/{asset_id}` project-and-path guard is the only download route.

- [x] **Step 5: Run tests and commit**

Run:

```bash
cd backend
pytest tests/test_lanhu_screenshot_service.py tests/test_lanhu_evidence_import.py -q
```

Commit:

```bash
git add backend/app/services/lanhu_evidence/screenshot_service.py backend/app/services/lanhu_evidence/job_runner.py backend/app/api/v1/lanhu_evidence.py backend/tests/test_lanhu_screenshot_service.py backend/tests/test_lanhu_evidence_import.py
git commit -m "fix: detect truncated lanhu captures and register exports"
```

### Task 4: Replace Evidence BackgroundTasks with Recoverable Worker Execution

**Files:**
- Create: `backend/app/services/lanhu_evidence/worker.py`
- Modify: `backend/app/services/lanhu_evidence/job_runner.py`
- Modify: `backend/app/services/task_worker.py`
- Modify: `backend/app/api/v1/lanhu_evidence.py`
- Modify: `backend/app/core/config.py`
- Test: `backend/tests/test_lanhu_evidence_worker.py`

- [x] **Step 1: Write failing worker tests**

```python
def test_claim_next_job_marks_only_one_pending_job_running(db_session):
    from app.services.lanhu_evidence.worker import claim_next_job
    first = evidence_job_factory(status="pending")
    evidence_job_factory(status="pending")
    claimed = claim_next_job(db_session)
    assert claimed.id == first.id
    assert claimed.status == "running"
    assert claimed.heartbeat_at is not None


def test_recover_stale_job_marks_failed_with_worker_lost(db_session):
    from app.services.lanhu_evidence.worker import recover_stale_jobs
    job = evidence_job_factory(status="running", heartbeat_at=datetime.now() - timedelta(minutes=11))
    assert recover_stale_jobs(db_session, stale_after_seconds=600) == 1
    db_session.refresh(job)
    assert job.status == "failed"
    assert job.error_message == "worker_lost"
```

- [x] **Step 2: Implement atomic claim and stale recovery**

`worker.py` must provide these exact contracts:

- `recover_stale_jobs(db: Session, stale_after_seconds: int) -> int` atomically changes every stale `running` row to `failed/done`, records `error_message="worker_lost"` and `finished_at`, commits, and returns the affected-row count.
- `claim_next_job(db: Session) -> LanhuEvidenceJob | None` conditionally changes only the oldest `pending` row to `running/discovering`, sets `heartbeat_at` and `started_at`, commits, and returns the claimed row only when the conditional update affects one row.
- `poll_and_execute_evidence_jobs() -> None` recovers stale rows first, acquires the bounded worker semaphore without blocking, claims one job using an isolated session, and releases the semaphore only after `run_job_in_new_session(job_id, project_id)` exits.

For SQLite, claim by conditional update, then reload the record:

```python
candidate = db.scalar(select(LanhuEvidenceJob.id).where(LanhuEvidenceJob.status == "pending").order_by(LanhuEvidenceJob.id).limit(1))
if candidate is None:
    return None
updated = db.execute(update(LanhuEvidenceJob).where(
    LanhuEvidenceJob.id == candidate,
    LanhuEvidenceJob.status == "pending",
).values(status="running", stage="discovering", heartbeat_at=datetime.now(), started_at=datetime.now()))
db.commit()
return db.get(LanhuEvidenceJob, candidate) if updated.rowcount == 1 else None
```

The runner must refresh `heartbeat_at` after discovery and after each page commit. It must not overwrite a status already set to `cancelled`.

- [x] **Step 3: Use the existing scheduled worker**

Add settings:

```python
lanhu_evidence_worker_enabled: bool = True
lanhu_evidence_max_concurrent: int = 1
lanhu_evidence_stale_after_seconds: int = 600
```

In `task_worker.poll_and_execute`, invoke `poll_and_execute_evidence_jobs()` once per poll. Use `threading.Semaphore(settings.lanhu_evidence_max_concurrent)`; acquire without blocking and release only after the run thread ends.

Remove `BackgroundTasks` from create/retry endpoints. They only persist a pending job and return HTTP 200.

- [x] **Step 4: Make retry immutable**

`POST /jobs/{job_id}/retry` must create a new pending `LanhuEvidenceJob` with:

```python
parent_job_id=old.id
attempt_no=old.attempt_no + 1
storage_dir=str(storage_base / str(new_job.id) / f"attempt-{new_job.attempt_no}")
```

It must not alter the original job, pages, assets, or exported evidence. Return the new job DTO.

- [x] **Step 5: Run tests and commit**

Run:

```bash
cd backend
pytest tests/test_lanhu_evidence_worker.py tests/test_lanhu_evidence_import.py -q
```

Commit:

```bash
git add backend/app/services/lanhu_evidence/worker.py backend/app/services/lanhu_evidence/job_runner.py backend/app/services/task_worker.py backend/app/api/v1/lanhu_evidence.py backend/app/core/config.py backend/tests/test_lanhu_evidence_worker.py
git commit -m "fix: run lanhu evidence jobs through recoverable worker"
```

### Task 5: Make Agent Queue Enqueue Transaction-Safe

**Files:**
- Modify: `backend/app/services/knowledge/agent_queue.py`
- Modify: `backend/app/api/v1/agent.py`
- Test: `backend/tests/test_agent_permissions.py`
- Test: `backend/tests/test_agent_queue_locking.py`

- [x] **Step 1: Write lock-retry tests**

```python
def test_enqueue_uses_caller_session_without_second_writer(db_session):
    from app.services.knowledge.agent_queue import enqueue
    item = enqueue(db_session, project_id=1, agent_type="case_generation", operator_id=1)
    db_session.commit()
    assert item.id > 0


def test_enqueue_retries_locked_operation_then_succeeds(monkeypatch, db_session):
    from sqlalchemy.exc import OperationalError
    from app.services.knowledge.agent_queue import enqueue
    commits = {"count": 0}
    original = db_session.commit
    def commit_once_locked():
        commits["count"] += 1
        if commits["count"] == 1:
            raise OperationalError("insert", {}, Exception("database is locked"))
        return original()
    monkeypatch.setattr(db_session, "commit", commit_once_locked)
    assert enqueue(db_session, project_id=1, agent_type="case_generation").status == "pending"
```

- [x] **Step 2: Change enqueue ownership and retry semantics**

Replace the internal `SessionLocal()` allocation with:

```python
class QueueWriteBusy(RuntimeError):
    pass

def enqueue(db: Session, project_id: int, agent_type: str, *, trigger_type="manual", user_input="", params=None, operator_id=0, priority=None) -> AgentQueueItem:
    for attempt in range(3):
        try:
            item = AgentQueueItem(
                project_id=project_id,
                agent_type=agent_type,
                trigger_type=trigger_type,
                priority=priority,
                input_json=json.dumps(
                    {"user_input": user_input, "params": params or {}},
                    ensure_ascii=False,
                ),
                status="pending",
                operator_id=operator_id,
            )
            db.add(item)
            db.flush()
            return item
        except OperationalError as exc:
            db.rollback()
            if "database is locked" not in str(exc).lower() or attempt == 2:
                raise QueueWriteBusy("agent queue is temporarily busy") from exc
            time.sleep(0.05 * (2 ** attempt))
```

The request handler commits once after `enqueue` succeeds. Do not call `ensure_processor_running()` before the queue row has been committed.

- [x] **Step 3: Return a controlled API response**

In `trigger_agent`, catch `QueueWriteBusy` and return `APIException(code=503, http_status=503, msg="Agent queue is temporarily busy; retry shortly")`. This prevents a raw SQL stack trace and HTTP 500.

- [x] **Step 4: Run tests and commit**

Run:

```bash
cd backend
pytest tests/test_agent_permissions.py tests/test_agent_queue_locking.py -q
```

Expected: all Agent permission tests pass repeatedly in a loop.

```bash
for ($i = 0; $i -lt 5; $i++) { .\.venv\Scripts\python.exe -m pytest tests/test_agent_permissions.py -q; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
```

Commit:

```bash
git add backend/app/services/knowledge/agent_queue.py backend/app/api/v1/agent.py backend/tests/test_agent_permissions.py backend/tests/test_agent_queue_locking.py
git commit -m "fix: make agent queue writes resilient to sqlite locks"
```

### Task 6: Isolate UI Automation Artifacts and Apply the Concurrency Limit

**Files:**
- Modify: `backend/app/services/playwright_executor.py`
- Test: `backend/tests/test_playwright_executor.py`

- [x] **Step 1: Write failing isolation tests**

```python
def test_executor_does_not_copy_shared_test_results(tmp_path, monkeypatch):
    from app.services.playwright_executor import _collect_artifacts
    run_dir = tmp_path / "run"
    shared_dir = tmp_path / "test-results"
    run_dir.mkdir()
    shared_dir.mkdir()
    (shared_dir / "foreign.png").write_bytes(b"foreign")
    assert _collect_artifacts(run_dir, "*.png") == []


def test_executor_uses_thread_semaphore(monkeypatch):
    from app.services import playwright_executor
    assert hasattr(playwright_executor, "_semaphore")
    assert playwright_executor._semaphore.__class__.__name__ == "Semaphore"
```

- [x] **Step 2: Replace unused async semaphore**

Replace `asyncio.Semaphore` with `threading.BoundedSemaphore(MAX_CONCURRENT)`. Acquire at the top of `run_playwright_test`; if acquisition fails within zero seconds, set the run back to `pending` and return `{ "status": "pending" }`. Release in a `finally` block.

- [x] **Step 3: Remove shared-directory scanning**

Delete both legacy call sites and the `_copy_artifacts_to_run_dir` helper itself. Pass Playwright an isolated output directory only:

```python
cmd = [npx, "playwright", "test", test_spec, "--project", browser,
       "--reporter", "json", "--output", str(artifact_dir)]
env["PLAYWRIGHT_JSON_OUTPUT_NAME"] = str(artifact_dir / "report.json")
```

All screenshots, video, trace, JSON, and HTML reported to the API must be discovered from `artifact_dir` only.

- [x] **Step 4: Run tests and commit**

Run:

```bash
cd backend
pytest tests/test_playwright_executor.py -q
```

Commit:

```bash
git add backend/app/services/playwright_executor.py backend/tests/test_playwright_executor.py
git commit -m "fix: isolate playwright artifacts per ui run"
```

### Task 7: Close API Asset Isolation and CRUD Lifecycle

**Files:**
- Modify: `backend/app/api/v1/apitest.py`
- Test: `backend/tests/test_apitest_project_isolation.py`

- [x] **Step 1: Write cross-project generation and delete tests**

```python
def test_generate_cases_rejects_endpoint_from_other_project(client, auth_headers, db_session):
    endpoint = ApiEndpoint(project_id=999, method="GET", path="/private")
    db_session.add(endpoint)
    db_session.commit()
    response = client.post("/api/v1/apitest/cases/generate", headers=auth_headers, json={"endpoint_id": endpoint.id})
    assert response.status_code == 404


def test_delete_service_scoped_to_current_project(client, auth_headers, db_session):
    service = ApiService(project_id=999, name="other")
    db_session.add(service)
    db_session.commit()
    response = client.delete(f"/api/v1/apitest/services/{service.id}", headers=auth_headers)
    assert response.status_code == 404
```

- [x] **Step 2: Scope reads in generation routes**

Replace both `db.get(ApiEndpoint, endpoint_id)` reads with:

```python
ep = db.query(ApiEndpoint).filter(
    ApiEndpoint.id == endpoint_id,
    ApiEndpoint.project_id == pid,
).first()
if ep is None:
    raise HTTPException(404, "API endpoint not found")
```

Do this for `/cases/generate` and every item in `/cases/batch-generate`.

- [x] **Step 3: Add scoped delete endpoints**

Add `DELETE /services/{service_id}` and `DELETE /endpoints/{endpoint_id}`, both requiring `apitest:manage`. For service deletion, reject with HTTP 409 when endpoints still reference the service. For endpoint deletion, reject with HTTP 409 when generated test cases reference `endpoint_id`. Neither route may delete a record from another project.

- [x] **Step 4: Run tests and commit**

Run:

```bash
cd backend
pytest tests/test_apitest_project_isolation.py tests/test_apitest_assets.py tests/test_apitest_generation.py -q
```

Commit:

```bash
git add backend/app/api/v1/apitest.py backend/tests/test_apitest_project_isolation.py backend/tests/test_apitest_assets.py
git commit -m "fix: scope api asset generation and add safe delete routes"
```

### Task 8: Restrict Wiki Lint Override and Deliver the UI Contract

**Files:**
- Modify: `backend/app/api/v1/wiki.py`
- Modify: `frontend/src/api/lanhuEvidence.ts`
- Modify: `frontend/src/pages/knowledge/components/LanhuEvidenceJobDrawer.tsx`
- Create: `frontend/src/pages/knowledge/components/__tests__/LanhuEvidenceJobDrawer.test.tsx`
- Test: `backend/tests/test_wiki_api.py`

- [x] **Step 1: Write override authorization tests**

```python
def test_wiki_lint_rejects_project_override_for_non_superuser(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.wiki_lint_enabled", True)
    response = client.post("/api/v1/wiki/lint", headers=auth_headers, json={"project_id_override": 999})
    assert response.status_code == 403
```

- [x] **Step 2: Enforce the override rule**

Use this guard before selecting `pid`:

```python
if body.project_id_override and body.project_id_override != (current.project_id or 0) and not current.is_super:
    raise APIException(code=403, msg="Only a super administrator may override project scope", http_status=403)
pid = body.project_id_override or (current.project_id or 0)
```

- [x] **Step 3: Update frontend evidence drawer**

Add API functions for `GET /jobs/{id}/assets` and page review. In the drawer:

```tsx
const importReady = quality.import_ready === true
const canReview = page.capture_status === 'success' && page.merged_text.trim().length > 0
```

Display `Not importable` when `importReady` is false. Show the lists `pages_missing_capture`, `pages_truncated`, and `pages_missing_ocr_review`. Do not render `word_path` or `json_path`; render download links using the returned asset IDs. Provide an approval dialog requiring a comment before posting page review.

- [x] **Step 4: Run checks and commit**

Run:

```bash
cd backend
pytest tests/test_wiki_api.py -q
cd ../frontend
npm test -- LanhuEvidenceJobDrawer
npm run typecheck
npm run build
```

Commit:

```bash
git add backend/app/api/v1/wiki.py backend/tests/test_wiki_api.py frontend/src/api/lanhuEvidence.ts frontend/src/pages/knowledge/components/LanhuEvidenceJobDrawer.tsx frontend/src/pages/knowledge/components/__tests__/LanhuEvidenceJobDrawer.test.tsx
git commit -m "fix: restrict wiki lint scope and expose evidence quality"
```

## 3. Release Verification

### Automated Gate

Run:

```bash
cd backend
pytest \
  tests/test_lanhu_evidence_models.py \
  tests/test_lanhu_evidence_worker.py \
  tests/test_lanhu_page_discovery.py \
  tests/test_lanhu_screenshot_service.py \
  tests/test_lanhu_ocr_merge.py \
  tests/test_lanhu_word_export.py \
  tests/test_lanhu_evidence_import.py \
  tests/test_postgres_migration_reconcile.py \
  tests/test_agent_permissions.py \
  tests/test_agent_queue_locking.py \
  tests/test_playwright_executor.py \
  tests/test_apitest_project_isolation.py \
  tests/test_apitest_assets.py \
  tests/test_apitest_generation.py \
  tests/test_wiki_api.py -q
```

Expected: all tests pass. Run `tests/test_agent_permissions.py` five consecutive times to detect SQLite writer flakiness.

### Manual Lanhu Acceptance

Use the user-provided Lanhu URL with `pageId=e7710ad1545b4c0184e11bde462d9c6a`.

- [x] Create a job with `capture_all_pages=true`, Word/JSON enabled, and all downstream imports enabled.
- [x] Confirm that a job with every page captured but OCR unavailable ends `success_with_warnings`, `import_ready=false`, and cannot import. The release run covered all 101 pages and the import API returned HTTP 409 before review.
- [x] Approve each OCR-unavailable page with an auditable comment, then confirm `import_ready=true` only if no page is missing capture, text, or scroll coverage.
- [x] Confirm the target page has more than one screenshot segment and no `capture_truncated=true`.
- [x] Download Word and JSON using asset IDs. Verify Word chapter count and JSON page count both equal discovered page count.
- [x] Stop the worker while another job is `running`; after 10 minutes or a lowered test threshold, confirm it becomes `failed/worker_lost`. Retry it and confirm a new job ID and a new attempt directory are created.
- [x] Start two UI runs that produce different screenshots; each run's artifact API must list only its own files.

### PostgreSQL Staging Migration Acceptance

Use the staging secret manager to inject `DATABASE_URL` for the PostgreSQL staging database. Keep `LANHU_EVIDENCE_WORKER_ENABLED=false` until every check below passes.

- [x] Apply the complete migration chain and verify the active and declared heads:

```bash
cd backend
alembic upgrade head
alembic current
alembic heads
```

Expected: `alembic upgrade head` exits with status 0; both head commands report `20260714_lanhu_pg_reconcile (head)` and no second head.

- [x] Inspect the PostgreSQL schema and verify the recovery and quality columns and indexes:

```sql
SELECT column_name
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('lanhu_evidence_job', 'lanhu_evidence_page')
  AND column_name IN (
    'parent_job_id', 'attempt_no', 'requested_options_json',
    'import_result_json', 'heartbeat_at', 'capture_truncated',
    'review_status', 'reviewer_id', 'review_comment', 'reviewed_at'
  )
ORDER BY column_name;

SELECT indexname
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname IN (
    'ix_lanhu_evidence_job_status_heartbeat',
    'ix_lanhu_evidence_page_job_review'
  )
ORDER BY indexname;
```

Expected: the first query returns all ten named columns and the second returns both named indexes.

- [x] Restart the staging backend with `LANHU_EVIDENCE_WORKER_ENABLED=true`, verify `/health`, create one pending evidence job, and confirm exactly one worker claims it without a PostgreSQL type, default, or transaction error.

### Release Acceptance Record — 2026-07-14

- PostgreSQL 16 staging upgraded incrementally and from a second empty database to the single `20260714_lanhu_pg_reconcile` head. Re-running `upgrade head` was idempotent; all ten quality/recovery columns, required indexes, and seven PostgreSQL server defaults were present.
- Final Lanhu evidence job `#4` (`attempt_no=4`) finished `success/done`: 101 discovered, 101 captured, zero failed, zero truncated, zero empty-text pages, and 101 explicit human OCR approvals. The quality report was `complete=true` and `import_ready=true` with every blocker list empty.
- The pre-review job returned HTTP 409 from the formal import endpoint. After the final approval, automatic Requirement, Knowledge, and Wiki imports each created a project-scoped record.
- Asset-ID downloads produced 164 screenshots, one Word document, and one JSON document. Downloaded hashes matched their asset rows; Word contained 101 Heading 1 chapters and JSON contained 101 pages.
- The supplied target page had three screenshot segments and `capture_truncated=false`.
- Worker termination was recovered as `worker_lost`; every retry received a new job ID and immutable attempt directory.
- Two concurrent UI acceptance runs produced `release-a.png` and `release-b.png` respectively. Each artifact API returned only its own screenshot plus its own report files; cross-run screenshot counts were zero.

## 4. Rollout and Rollback

- Deploy migration before enabling the evidence worker.
- Set `LANHU_EVIDENCE_WORKER_ENABLED=false` during schema deployment, then enable after the automated gate passes.
- Existing `success` evidence jobs are historical. Mark their `quality_json.import_ready=false` with a one-off migration script when `ocr_pages < total_pages`; do not delete their files.
- If a quality-gate defect blocks an urgent import, use page review approval with a written reason. Do not change the status directly in SQL.
- Roll back application code by disabling `LANHU_EVIDENCE_WORKER_ENABLED`; do not downgrade the migration because existing review and heartbeat data is backward-compatible.

## 5. Definition of Done

- No job with missing screenshots, truncated scroll capture, missing merged text, or unreviewed OCR absence can be imported into Requirement/RAG/Wiki.
- Every Word/JSON is represented by a project-scoped asset row and downloadable without disclosing server file paths.
- An interrupted evidence job reaches a terminal state and retry never reuses its old evidence directory.
- `/api/v1/agents/run/{agent_type}` never emits a raw SQLite lock 500; temporary writer contention returns a controlled 503 after retries.
- UI artifacts cannot be copied from `tests/playwright/test-results` or any other shared path.
- API endpoint case generation cannot read another project's endpoint, and API services/endpoints have safe project-scoped delete routes.
- Wiki lint project override is super-admin-only.
- The provided Lanhu URL passes through the quality gate with an auditable explanation for every page that needs human OCR review.
