# Batch 48 Acceptance Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 Batch 47 需求服务生产级验收发现的 21 个缺陷，补齐行为级自动化、迁移与供应链门禁，并把 Batch 47 的验收方法沉淀为可复用于其他模块的统一规则。

**Architecture:** 以 `origin/main@a68e492` 为实现基线，以 Batch 47 的 48 条已执行用例和 21 个缺陷为唯一回归清单。后端采用请求级事务边界、项目归属校验、数据库唯一约束和持久化审查记录；前端采用服务端分页/搜索、按需详情、可取消请求、非重叠轮询和响应式单列降级；验收规则落在 `tests/test-case-standards/`，历史报告与证据继续保存在 `work-logs/`。

**Tech Stack:** FastAPI、SQLAlchemy 2.0、Alembic、Pytest、React 18、TypeScript、Vite、Vitest、Testing Library、Playwright

**Execution result (2026-07-27):** 初始实现提交为
`d1f7e52be70757c14d4acc153dee17571773b931`；真实外部复测修复提交为
`4dc307ed481fdb9ba01f5b8f949aeed7aef24503`。最终后端全量为
812 通过、2 条默认跳过的真实 PG 集成用例（显式开启后 2/2 通过）；前端
29 文件/124 测试、typecheck、build、三视口 headed Playwright 和 high/critical
供应链门禁通过；真实 AI 完成 2 模块/15 功能点拆分并生成 13 条功能用例，
旧 PostgreSQL 隔离克隆从 `20260714_lanhu_pg_reconcile` 升至
`20260727_batch48_pg_parity` 且重复升级、数据保留和 metadata 检查通过，
真实 PG 并发得到 4 路 1 导入/3 跳过与 6 路 1×200/5×409。48 条复测为
45 通过、3 条真实蓝湖关键链路阻塞，最终结论 `NEEDS WORK`。下方复选框保留为原始实施步骤，不作为最终执行账本；
权威结果见 Batch 48 复测文档和 QA 报告。

---

## File map

**Backend behavior**

- Modify: `test-platform-v2/backend/app/api/v1/requirement.py` — upload/list/detail/extraction/generation/review/import/matching/audit transaction routes.
- Modify: `test-platform-v2/backend/app/services/requirement_service.py` — transaction-safe writes, review overlay, edited import, idempotent counters.
- Modify: `test-platform-v2/backend/app/services/test_case_service.py` — caller-controlled commit/flush.
- Modify: `test-platform-v2/backend/app/schemas/requirement.py` — import/review/match contracts and durable inheritance fields.
- Modify: `test-platform-v2/backend/app/models/requirement.py` — persisted API links.
- Modify: `test-platform-v2/backend/app/models/requirement_review.py` — review uniqueness and update timestamp semantics.
- Modify: `test-platform-v2/backend/app/models/test_case.py` — AI source index and uniqueness contract.
- Modify: `test-platform-v2/backend/app/api/v1/requirement_modules.py` — project isolation, lazy tree, relation validation, atomic audit writes.
- Modify: `test-platform-v2/backend/app/schemas/release_bundle.py` — relation type enum validation.
- Modify: `test-platform-v2/backend/app/models/requirement_module.py` — relation uniqueness.
- Modify: `test-platform-v2/backend/app/models/__init__.py` — register every migrated ORM model with Alembic metadata.
- Create: `test-platform-v2/backend/alembic/versions/20260727_batch48_requirement_acceptance.py` — additive old-database reconciliation and unique indexes.

**Backend tests**

- Create: `test-platform-v2/backend/tests/test_requirement_acceptance.py` — upload/detail/paging/extraction/coverage/match/audit behavior.
- Create: `test-platform-v2/backend/tests/test_requirement_review.py` — review/edit/import/transaction/idempotency behavior.
- Create: `test-platform-v2/backend/tests/test_requirement_modules_acceptance.py` — project isolation, lazy tree and admin-link rules.
- Create: `test-platform-v2/backend/tests/test_batch48_requirement_migration.py` — old-schema upgrade, repeatability and metadata contract.
- Modify: `test-platform-v2/backend/tests/test_requirement.py` — replace the assertion-free match test with a real behavior assertion.

**Frontend behavior**

- Modify: `test-platform-v2/frontend/src/api/requirement.ts` — detail, coverage, edited import, review/edit and match-confirm APIs with abort support.
- Modify: `test-platform-v2/frontend/src/api/lanhuEvidence.ts` — abortable polling and canonical asset URL/page data.
- Modify: `test-platform-v2/frontend/src/pages/requirement/index.tsx` — server paging/search, lazy detail, real coverage, correct actions, responsive layout and keyboard rows.
- Modify: `test-platform-v2/frontend/src/pages/requirement/AiResultModal.tsx` — send final edited cases.
- Modify: `test-platform-v2/frontend/src/pages/requirement/ReviewPage.tsx` — persistent edit/review/import flow and guarded selection.
- Modify: `test-platform-v2/frontend/src/pages/requirement/components/EvidenceTaskPanel.tsx` — non-overlapping cancelable polling with backoff.
- Modify: `test-platform-v2/frontend/src/hooks/useApi.ts` — Strict Mode-safe single effective initial request.
- Modify: `test-platform-v2/frontend/src/router/index.tsx` — register `/requirement/:id/review`.
- Modify: `test-platform-v2/frontend/package.json` and `package-lock.json` — remove high/critical dependency findings without unrelated framework migration.

**Frontend tests**

- Create: `test-platform-v2/frontend/src/api/__tests__/requirement.test.ts`.
- Create: `test-platform-v2/frontend/src/pages/requirement/__tests__/RequirementPage.test.tsx`.
- Create: `test-platform-v2/frontend/src/pages/requirement/__tests__/AiResultModal.test.tsx`.
- Create: `test-platform-v2/frontend/src/pages/requirement/__tests__/ReviewPage.test.tsx`.
- Create: `test-platform-v2/frontend/src/pages/requirement/components/__tests__/EvidenceTaskPanel.test.tsx`.
- Modify: `test-platform-v2/frontend/src/hooks/__tests__/useApi.test.ts`.
- Create: `test-platform-v2/frontend/e2e/requirement.acceptance.spec.ts`.

**Rules, reports and workflow**

- Import from Batch 47: `tests/test-cases/functional/BATCH47-测试平台需求服务-生产级验收.md`.
- Import from Batch 47: `work-logs/batch-47-需求服务生产级验收报告-2026-07-27.md`.
- Import from Batch 47: `work-logs/evidence/batch-47-requirement-service/*`.
- Create: `tests/test-cases/functional/BATCH48-测试平台需求服务-生产级复测.md`.
- Create: `tests/test-case-standards/生产级模块验收规则.md`.
- Create: `work-logs/batch-48-需求服务验收修复-qa-report.md`.
- Create: `work-logs/kanbans/DEV-batch-48-acceptance-fixes.md`.
- Modify: `tests/test-case-standards/CLAUDE.md`.
- Modify: `tests/test-cases/README.md`.
- Modify: `tests/test-cases/INDEX.md`.
- Modify: `docs/testing-strategy.md`.
- Modify: `AGENTS.md` — every Batch 48+ push requires an explicit “是否还有其他变动” confirmation.

### Task 1: Preserve Batch 47 evidence and write failing backend acceptance tests

- [ ] **Step 1: Import the Batch 47 evidence commit**

Run:

```powershell
git cherry-pick 0786fca
```

Expected: only the Batch 47 plan, 48-case asset, report, index update and three sanitized screenshots are added; no production code changes.

- [ ] **Step 2: Write upload, paging and detail failure tests**

Create `test-platform-v2/backend/tests/test_requirement_acceptance.py` with tests that:

```python
def test_upload_size_boundary_returns_413_without_side_effects(
    client, db_session, auth_headers
):
    too_large = b"x" * (20 * 1024 * 1024 + 1)
    response = client.post(
        "/api/v1/requirements/upload",
        files={"file": ("oversize.md", too_large, "text/markdown")},
        headers=auth_headers,
    )
    assert response.status_code == 413
    assert response.json()["code"] == 413
    assert db_session.query(RequirementDocument).count() == 0
    assert db_session.query(AuditLog).count() == 0


def test_list_uses_server_search_and_creator_name(
    client, db_session, auth_headers, admin_user
):
    db_session.add_all([
        RequirementDocument(
            project_id=1,
            creator_id=admin_user.id,
            title="only-on-page-2" if index == 0 else f"document-{index:03d}",
            source_ref=f"document-{index:03d}.md",
        )
        for index in range(101)
    ])
    db_session.commit()
    response = client.get(
        "/api/v1/requirements?page=1&page_size=10&keyword=only-on-page-2",
        headers=auth_headers,
    )
    payload = response.json()["data"]
    assert payload["total"] == 1
    assert payload["items"][0]["creator_name"] == admin_user.username


def test_detail_returns_content_only_inside_current_project(
    client, db_session, auth_headers
):
    own = RequirementDocument(project_id=1, title="own", content="full body")
    foreign = RequirementDocument(project_id=2, title="foreign", content="secret")
    db_session.add_all([own, foreign])
    db_session.commit()
    own_response = client.get(f"/api/v1/requirements/{own.id}", headers=auth_headers)
    other_project_response = client.get(
        f"/api/v1/requirements/{foreign.id}",
        headers=auth_headers,
    )
    assert own_response.json()["data"]["content"] == "full body"
    assert other_project_response.status_code == 404
```

Use real assertions for 20 MB-1, 20 MB, 20 MB+1, empty files, corrupt DOCX/XLSX, page 2, keyword and cross-project detail.

- [ ] **Step 3: Run the new tests and record the expected failures**

Run:

```powershell
python -m pytest tests/test_requirement_acceptance.py -q --tb=short
```

Expected before implementation: failures reproduce B47-DEF-002/003/008/009/012 and successful assertions prove the test harness itself works.

- [ ] **Step 4: Commit the red tests**

Run:

```powershell
git add test-platform-v2/backend/tests/test_requirement_acceptance.py
git commit -m "test(batch-48): reproduce requirement acceptance defects"
```

Expected: one local test-only commit; no push.

### Task 2: Fix document upload, detail, paging, extraction and coverage behavior

- [ ] **Step 1: Replace whole-file upload with a capped read and correct exception contract**

In `app/api/v1/requirement.py`, read at most one byte beyond the limit and raise:

```python
file_bytes = await file.read(_MAX_UPLOAD_BYTES + 1)
if len(file_bytes) > _MAX_UPLOAD_BYTES:
    raise APIException(code=413, msg="上传文件不能超过 20 MB", http_status=413)
if not file_bytes:
    raise APIException(code=400, msg="上传文件不能为空", http_status=400)
```

Wrap parser errors as HTTP/business 400 and guarantee no document, audit or background task is created.

- [ ] **Step 2: Batch-load creator names and add project-scoped detail**

In `list_requirements`, batch-fetch `User.id/username` for the page and construct `RequirementDocumentBrief` with `creator_name`. Add:

```python
@router.get("/{document_id}", response_model=R[RequirementDocumentOut])
def get_requirement_detail(
    document_id: int,
    current: CurrentUser = Depends(require_permission("requirement:upload")),
    db: Session = Depends(get_db),
):
    doc = requirement_service.get_requirement(db, document_id, current.project_id or 0)
    if not doc:
        raise not_found("需求文档")
    return R.ok(RequirementDocumentOut(**doc))
```

- [ ] **Step 3: Preserve extraction assessment and fix recovery semantics**

Parse the stored extraction and retain only its `overall_assessment`; never assign the whole JSON string. The frontend will start a new extraction only when the GET succeeds with no extraction; 403/500/timeouts must propagate.

- [ ] **Step 4: Add abortable detail and coverage API helpers**

In `frontend/src/api/requirement.ts`, add:

```ts
export function fetchRequirement(documentId: number, signal?: AbortSignal) {
  return api.get(`/requirements/${documentId}`, { signal }) as Promise<RequirementDocument>
}

export function fetchRequirementCoverage(documentId: number, signal?: AbortSignal) {
  return api.get(`/requirements/${documentId}/coverage`, { signal }) as Promise<RequirementCoverage>
}
```

- [ ] **Step 5: Run the document tests**

Run:

```powershell
python -m pytest tests/test_requirement_acceptance.py -q --tb=short
```

Expected: upload/detail/paging/extraction/coverage cases pass.

- [ ] **Step 6: Commit the document behavior**

Run:

```powershell
git add test-platform-v2/backend/app/api/v1/requirement.py test-platform-v2/backend/app/services/requirement_service.py test-platform-v2/frontend/src/api/requirement.ts test-platform-v2/backend/tests/test_requirement_acceptance.py
git commit -m "fix(batch-48): harden requirement document behavior"
```

### Task 3: Make review, edited import and repeated import durable and atomic

- [ ] **Step 1: Write failing review/import tests**

Create `test_requirement_review.py` with:

```python
def test_import_rolls_back_when_second_case_fails(
    client, db_session, auth_headers, monkeypatch
):
    document = RequirementDocument(
        project_id=1,
        title="atomic",
        ai_raw=json.dumps({
            "functional_cases": [
                {"title": "first", "steps": []},
                {"title": "second", "steps": []},
            ],
            "api_cases": [],
        }),
    )
    db_session.add(document)
    db_session.commit()
    original = test_case_service.create_case
    call_count = 0

    def fail_second(db, data, *, commit=True):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("injected second-case failure")
        return original(db, data, commit=commit)

    monkeypatch.setattr(test_case_service, "create_case", fail_second)
    response = client.post(
        f"/api/v1/requirements/{document.id}/import",
        json={"indices": [0, 1], "edited_cases": []},
        headers=auth_headers,
    )
    assert response.status_code == 500
    assert db_session.query(TestCase).count() == 0
    assert document.imported_count == 0
    assert db_session.query(AuditLog).count() == 0


def test_import_uses_final_edited_case_and_is_idempotent(
    client, db_session, auth_headers
):
    document = RequirementDocument(
        project_id=1,
        title="edited",
        ai_raw=json.dumps({
            "functional_cases": [{"title": "AI title", "steps": []}],
            "api_cases": [],
        }),
    )
    db_session.add(document)
    db_session.commit()
    body = {
        "indices": [0],
        "edited_cases": [{
            "index": 0,
            "title": "用户确认标题",
            "steps": '[{"action":"最终步骤"}]',
        }],
    }
    first = client.post(
        f"/api/v1/requirements/{document.id}/import",
        json=body,
        headers=auth_headers,
    )
    second = client.post(
        f"/api/v1/requirements/{document.id}/import",
        json=body,
        headers=auth_headers,
    )
    stored = db_session.query(TestCase).one()
    assert first.json()["data"]["imported"] == 1
    assert stored.title == "用户确认标题"
    assert stored.steps == '[{"action":"最终步骤"}]'
    assert second.json()["data"] == {"imported": 0, "skipped": 1, "total": 1}
    assert db_session.query(TestCase).count() == 1


def test_review_state_persists_approve_reject_edit_and_import(
    client, db_session, auth_headers
):
    document = RequirementDocument(
        project_id=1,
        title="review",
        ai_raw=json.dumps({
            "functional_cases": [{"title": "candidate", "steps": []}],
            "api_cases": [],
        }),
    )
    db_session.add(document)
    db_session.commit()
    edit = client.post(
        f"/api/v1/requirements/{document.id}/review/0",
        json={"action": "edit", "edited_data": {"title": "修订标题"}},
        headers=auth_headers,
    )
    assert edit.status_code == 200
    refreshed = client.get(
        f"/api/v1/requirements/{document.id}/review-state",
        headers=auth_headers,
    ).json()["data"]
    assert refreshed["functional_cases"][0]["review_status"] == "edited"
    assert refreshed["functional_cases"][0]["edited_data"]["title"] == "修订标题"
```

Also cover invalid index, cross-project document, functional/API mixed indexes and two concurrent attempts.

- [ ] **Step 2: Give `create_case` a caller-controlled transaction mode**

Use:

```python
def create_case(db: Session, data: dict, *, commit: bool = True) -> dict:
    row = TestCase(**_sanitize_case_data(data))
    db.add(row)
    if commit:
        db.commit()
        db.refresh(row)
    else:
        db.flush()
    return _row_to_dict(row)
```

Existing callers keep current behavior; Batch 48 import passes `commit=False`.

- [ ] **Step 3: Persist source index and enforce database uniqueness**

Add `TestCase.source_case_index: int | None` and a unique constraint on `(project_id, source_doc_id, source_case_index)`. Query existing imported indices before insert, sort stored indices, and set:

```python
row.imported_count = len(new_func) + len(new_api)
row.imported_func_count = len(new_func)
row.imported_api_count = len(new_api)
```

- [ ] **Step 4: Extend the import contract with final edited values**

Use:

```python
class CaseImportRequest(BaseModel):
    indices: list[int] = Field(default_factory=list)
    edited_cases: list[AIGeneratedCase] = Field(default_factory=list)
```

The route must validate each edited index against the stored AI case, preserve server-owned `index/case_type`, whitelist editable fields, and reject unknown/duplicate indexes.

- [ ] **Step 5: Implement persistent review endpoints**

Add:

```text
GET  /requirements/{document_id}/review-state
POST /requirements/{document_id}/review/{case_index}
```

Accepted actions are `approve`, `reject`, `edit`; `edit` requires non-empty `edited_data`. Upsert `RequirementReview` by `(requirement_id, case_index)`, overlay it on `ai_raw`, and expose pending/approved/rejected/edited/imported counts.

- [ ] **Step 6: Make business data and audit one transaction**

Add `commit=False` support to requirement service writes. The upload route uses the following exact transaction boundary; apply the same order to extract/confirm/generate/import/delete with their concrete service call and audit action:

```python
try:
    document = requirement_service.create_requirement(
        db,
        project_id=current.project_id or 0,
        creator_id=current.user.id,
        title=title,
        file_type=file_type,
        source_ref=source_ref,
        content=content,
        parsed_type=parsed_type,
        excel_cases=excel_cases,
        commit=False,
    )
    _audit(req, current, db, "requirement:upload", f"#{document['id']} {title}")
    db.commit()
except Exception:
    db.rollback()
    raise
```

Move every `_audit` call in `requirement_modules.py` before its corresponding `db.commit()`.

- [ ] **Step 7: Persist inherited cases before saving `ai_raw`**

Use normal fields `inherited` and `from_version` in the Pydantic schema, append inherited cases into `ai_result["functional_cases"]`, then call `update_ai_result`. A subsequent GET and import must see the same stable indexes.

- [ ] **Step 8: Run review/import tests**

Run:

```powershell
python -m pytest tests/test_requirement_review.py -q --tb=short
```

Expected: all review/edit/transaction/idempotency tests pass with zero partial writes.

- [ ] **Step 9: Commit review and transaction fixes**

Run:

```powershell
git add test-platform-v2/backend/app test-platform-v2/backend/tests/test_requirement_review.py
git commit -m "fix(batch-48): make requirement review and import durable"
```

### Task 4: Close module-tree, project-isolation and API-link gaps

- [ ] **Step 1: Write failing module acceptance tests**

Create `test_requirement_modules_acceptance.py` covering:

```python
def _add_module(db, *, project_id, bundle_id, name, parent_id=None, platform="APP"):
    row = RequirementModule(
        project_id=project_id,
        release_bundle_id=bundle_id,
        name=name,
        parent_module_id=parent_id,
        platform=platform,
    )
    db.add(row)
    db.flush()
    return row


def test_children_hides_other_project_tree(
    client, db_session, auth_headers
):
    foreign_bundle = ReleaseBundle(project_id=999, name="foreign")
    db_session.add(foreign_bundle)
    db_session.flush()
    foreign_parent = _add_module(
        db_session,
        project_id=999,
        bundle_id=foreign_bundle.id,
        name="secret-parent",
    )
    _add_module(
        db_session,
        project_id=999,
        bundle_id=foreign_bundle.id,
        name="secret-page",
        parent_id=foreign_parent.id,
    )
    db_session.commit()
    response = client.get(
        f"/api/v1/requirement-modules/bundle/{foreign_bundle.id}/children/{foreign_parent.id}",
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert "secret-page" not in response.text


def test_lazy_children_matches_full_tree_for_three_levels(
    client, db_session, auth_headers
):
    bundle = ReleaseBundle(project_id=1, name="own")
    db_session.add(bundle)
    db_session.flush()
    root = _add_module(
        db_session, project_id=1, bundle_id=bundle.id, name="root"
    )
    child = _add_module(
        db_session,
        project_id=1,
        bundle_id=bundle.id,
        name="child",
        parent_id=root.id,
    )
    _add_module(
        db_session,
        project_id=1,
        bundle_id=bundle.id,
        name="grandchild",
        parent_id=child.id,
    )
    db_session.commit()
    lazy = client.get(
        f"/api/v1/requirement-modules/bundle/{bundle.id}/children/{root.id}",
        headers=auth_headers,
    ).json()["data"]
    assert lazy[0]["children"][0]["name"] == "grandchild"
    assert lazy[0]["child_count"] == 1


@pytest.mark.parametrize("relation_type", ["unknown", "", "links_to_admin "])
def test_admin_link_rejects_invalid_relation_type(
    relation_type, client, auth_headers
):
    response = client.post(
        "/api/v1/requirement-modules/admin-links",
        json={
            "client_module_id": 1,
            "admin_module_id": 2,
            "relation_type": relation_type,
        },
        headers=auth_headers,
    )
    assert response.status_code == 422
```

Also test cross-bundle, reversed ADMIN→APP, APP→APP, duplicate and cross-project relations.

- [ ] **Step 2: Fix tree ownership and lazy recursion**

Validate bundle and parent against `current.project_id`; add `project_id` to child/grandchild queries; call:

```python
sub_nodes = _build_tree_nodes_from_list(gchildren, parent_id=child.id)
```

Apply project filtering to the full tree query too.

- [ ] **Step 3: Validate admin links**

Use `Literal["configures", "links_to_admin"]` in `ModuleAdminLinkCreate`. Require client platform in `APP/PC/WEB`, admin platform `ADMIN`, both in the same bundle/project, and a database uniqueness constraint across project/client/admin/type.

- [ ] **Step 4: Validate and persist API matching**

`match-api` must 404 for missing/foreign documents. Add a confirm contract that validates endpoint IDs belong to the current project, stores `linked_swagger_id` and stable linked endpoint IDs, and exposes them after refresh for coverage/trace consumers.

- [ ] **Step 5: Run module acceptance tests**

Run:

```powershell
python -m pytest tests/test_requirement_modules_acceptance.py tests/test_requirement_acceptance.py -q --tb=short
```

Expected: cross-project responses reveal no names/counts, three-level trees match, invalid relations and documents are rejected.

- [ ] **Step 6: Commit module/security fixes**

Run:

```powershell
git add test-platform-v2/backend/app/api/v1/requirement_modules.py test-platform-v2/backend/app/schemas/release_bundle.py test-platform-v2/backend/app/models/requirement_module.py test-platform-v2/backend/tests/test_requirement_modules_acceptance.py
git commit -m "fix(batch-48): enforce requirement module isolation"
```

### Task 5: Reconcile old databases and Alembic metadata

- [ ] **Step 1: Write migration contract tests**

Create `test_batch48_requirement_migration.py` that creates a pre-Batch-48 schema with existing rows, runs the migration upgrade twice through guarded helpers, and asserts:

```python
assert required_document_columns <= inspected_document_columns
assert {"description", "sort_order"} <= inspected_module_columns
assert old_row_title == "preserved"
assert unique_index_names >= {
    "uq_test_case_ai_source_index",
    "uq_requirement_review_case",
    "uq_module_admin_link_relation",
}
```

- [ ] **Step 2: Register every migrated model**

Add missing imports/`__all__` entries for `ApiToken`, defect child tables, perf tables, requirement review, case categories, `UiTestScript`, and wiki review tables. `Base.metadata` must include all tables already represented by migrations.

- [ ] **Step 3: Add one additive reconciliation migration**

Create revision `20260727_batch48` with `down_revision = "20260726_batch45"`. Use SQLAlchemy inspection guards before adding:

```text
requirement_document.release_bundle_id
requirement_document.linked_swagger_id
requirement_document.linked_api_endpoint_ids
requirement_module.description
requirement_module.sort_order
test_case.source_case_index
```

Create guarded unique indexes and retain existing data. Downgrade removes only objects created by this revision.

- [ ] **Step 4: Verify empty and old-schema upgrades**

Run:

```powershell
python -m pytest tests/test_batch48_requirement_migration.py tests/test_migration_revision_ids.py -q
python -m alembic upgrade head
python -m alembic current
python -m alembic check
```

Expected: one head `20260727_batch48`; upgrade/check exit 0; rerunning upgrade is a no-op; no real tables are proposed for removal.

- [ ] **Step 5: Commit migration reconciliation**

Run:

```powershell
git add test-platform-v2/backend/app/models test-platform-v2/backend/alembic test-platform-v2/backend/tests/test_batch48_requirement_migration.py
git commit -m "fix(batch-48): reconcile requirement database upgrades"
```

### Task 6: Fix frontend data flow, review UX, responsiveness and polling

- [ ] **Step 1: Write failing frontend tests**

Create the five Batch 48 Vitest files listed in the file map. They must assert:

```ts
expect(fetchRequirements).toHaveBeenCalledWith(
  expect.objectContaining({ page: 2, page_size: 10, keyword: 'target' }),
  expect.any(AbortSignal),
)
expect(importCases).toHaveBeenCalledWith(
  9,
  [0],
  [expect.objectContaining({ index: 0, title: '用户确认标题' })],
)
expect(generateTestCases).toHaveBeenCalledWith(9, { use_extraction: true })
expect(extractFeatures).toHaveBeenCalledWith(9)
```

Also assert the row is focusable and reacts to Enter/Space, review route renders, polling never overlaps, cleanup aborts, and repeated failures emit only one visible error.

- [ ] **Step 2: Split document paging/search from supporting data**

Keep domains/cases on a one-time `useApi`. Fetch documents with `{page: docPage, page_size: 10, keyword: debouncedKeyword}` and use server `total`; remove client slicing/filtering over the first 100 rows.

- [ ] **Step 3: Lazy-load detail and real coverage**

On `activeDocId`, call abortable detail and coverage helpers. Render full content from the detail response; render the returned `coverage_rate` with a truthful “当前需求覆盖率” label.

- [ ] **Step 4: Correct action semantics and review navigation**

“生成用例（基于拆分）” calls `generateTestCases(id, {use_extraction: true})`; “重新拆分” bypasses stored extraction and calls `extractFeatures`; register and expose `/requirement/:id/review`.

- [ ] **Step 5: Send final edited values and persist review edits**

`AiResultModal` sends selected edited cases. `ReviewPage` supports edit/approve/reject, disables selecting rejected/imported items, and reloads persisted server state after each mutation.

- [ ] **Step 6: Fix evidence preview and polling**

Fetch assets and pages together; map `merged_text || ocr_text` by page ID and use `/api/v1/lanhu-evidence/assets/{id}`. Replace `setInterval` with one awaited `setTimeout` chain, AbortController cleanup, 3s→6s→12s→30s capped backoff, and one toast per outage.

- [ ] **Step 7: Make the page usable at 390 px**

Change the outer layout to `flex-col xl:flex-row`; make the evidence panel `w-full xl:w-[260px]` with bounded mobile height; keep the content `w-full min-w-0`. Add `tabIndex={0}`, `aria-selected`, visible focus styles and Enter/Space handling to selectable rows.

- [ ] **Step 8: Make `useApi` single-request under Strict Mode**

Defer the initial execute to a zero-delay timer that the first Strict Mode cleanup cancels; the second effect instance performs the only network request. Continue aborting in-flight work on real unmount.

- [ ] **Step 9: Run frontend unit tests**

Run:

```powershell
npm test -- --run src/api/__tests__/requirement.test.ts src/pages/requirement src/hooks/__tests__/useApi.test.ts
npm run typecheck
npm run build
```

Expected: Batch 48 behavior tests, typecheck and build pass.

- [ ] **Step 10: Commit frontend fixes**

Run:

```powershell
git add test-platform-v2/frontend/src test-platform-v2/frontend/e2e/requirement.acceptance.spec.ts
git commit -m "fix(batch-48): complete requirement frontend acceptance"
```

### Task 7: Remove unaccepted dependency risk

- [ ] **Step 1: Upgrade the patched PostCSS line and reclassify build-only tooling**

Run:

```powershell
npm install --save-dev "postcss@^8.5.18"
```

Keep `shadcn` as build/development tooling rather than a runtime dependency if the lockfile proves it is not imported by `src/`.

- [ ] **Step 2: Run both audits and record exact residual findings**

Run:

```powershell
npm audit --omit=dev --json
npm audit --json
```

Expected: production dependencies contain zero high/critical findings. Any moderate residual has package/advisory/exposure/mitigation/owner recorded; full-tree high/critical findings must either be upgraded without breaking tests or remain an explicit `NEEDS WORK` blocker.

- [ ] **Step 3: Re-run the frontend gates after lockfile changes**

Run:

```powershell
npm run typecheck
npm run build
npm test -- --run
```

Expected: all three exit 0.

- [ ] **Step 4: Commit dependency remediation**

Run:

```powershell
git add test-platform-v2/frontend/package.json test-platform-v2/frontend/package-lock.json
git commit -m "fix(batch-48): remediate frontend dependency risk"
```

### Task 8: Publish reusable production acceptance rules and Batch 48 workflow gate

- [ ] **Step 1: Write the reusable rule**

Create `tests/test-case-standards/生产级模块验收规则.md` with twelve mandatory gates:

```text
A01 baseline traceability
A02 isolated environment
A03 functional main/alternate/error flows
A04 API input/business/response validation
A05 RBAC and project/tenant isolation
A06 UI/API/DB/audit transaction consistency
A07 idempotency/concurrency/retry
A08 over-one-page search/filter/sort/count
A09 desktop/tablet/mobile/a11y/network E2E
A10 real old-database migration
A11 automation and supply-chain security
A12 document/evidence consistency
```

Each function point requires at least one positive and one negative case. Each API case must verify input, business logic, HTTP/envelope/core response and database/audit/task side effects where applicable.

- [ ] **Step 2: Define objective release verdicts**

Document:

```text
READY       = all P0/P1 pass, no fatal/severe open issue, no production-impacting blocked/unexecuted case.
CONDITIONAL = only accepted P2/P3 risk with owner, expiry and approval evidence.
NEEDS WORK  = any P0/P1 failure, cross-project leak, partial commit/data loss, old DB upgrade failure,
              unaccepted high/critical vulnerability, or blocked external critical flow.
```

- [ ] **Step 3: Add evidence and report templates**

The reusable case template must include ID, module, linked requirement/history defect, priority, type, precondition, explicit input/steps, observable expected result, actual result, status, defect ID, executor/date and evidence. Add an evidence index mapping case IDs to sanitized screenshots, request/response, DB checks, logs or command output.

- [ ] **Step 4: Persist the new push confirmation gate**

Modify `AGENTS.md` so every push from Batch 48 onward, including later fix pushes and completion-confirmation evidence pushes, first asks:

```text
当前待推送范围如下。是否还有其他变动需要合并？
如果有，我将暂停推送，完成合并和自检后再重新确认。
```

No affirmative answer means no push.

- [ ] **Step 5: Update indexes and testing strategy**

Add the new standard to `tests/test-case-standards/CLAUDE.md`; add Batch 47/48 cases to `tests/test-cases/README.md` and `INDEX.md`; state in `docs/testing-strategy.md` that a P0 browser/E2E failure blocks production acceptance even when unit tests pass.

- [ ] **Step 6: Create the Batch 48 retest asset and QA report**

Copy all 48 Batch 47 cases into `BATCH48-测试平台需求服务-生产级复测.md`, preserve IDs, add Batch 48 actual/status/evidence fields, and map each failure to its fixing commit/test. Record external AI/Lanhu/PostgreSQL conditions as blocked unless actually executed.

- [ ] **Step 7: Commit rules and reports**

Run:

```powershell
git add AGENTS.md docs/testing-strategy.md tests work-logs docs/superpowers/plans/2026-07-27-batch-48-acceptance-fixes.md
git commit -m "docs(batch-48): standardize production module acceptance"
```

### Task 9: Full verification, local delivery summary and push pause

- [ ] **Step 1: Run backend hard gate and targeted suites**

Run:

```powershell
python -m ruff check app/ --select F821
python -m pytest tests/test_requirement.py tests/test_requirement_acceptance.py tests/test_requirement_review.py tests/test_requirement_modules_acceptance.py tests/test_batch48_requirement_migration.py -q --tb=short
```

Expected: exit 0 and exact pass count recorded.

- [ ] **Step 2: Run backend full regression**

Run:

```powershell
python -m pytest tests/ -q --tb=short
```

Expected: record total/pass/fail and the complete failure set; no new failure relative to `origin/main`.

- [ ] **Step 3: Run frontend hard gate and full regression**

Run:

```powershell
npm run typecheck
npm run build
npm test -- --run
```

Expected: exit 0 and exact file/test counts recorded.

- [ ] **Step 4: Run browser acceptance**

Run:

```powershell
npx playwright test e2e/requirement.acceptance.spec.ts
```

Expected: desktop `1440x900`, tablet `768x1024`, mobile `390x844`; no clipping, row keyboard activation works, each effective GET appears once, upload/detail/review/edit/import flow succeeds with disposable data.

- [ ] **Step 5: Run migration and security gates**

Run:

```powershell
python -m alembic upgrade head
python -m alembic check
npm audit --omit=dev
npm audit
```

Expected: Alembic exit 0; production high/critical 0; full dependency result and accepted residual findings recorded.

- [ ] **Step 6: Review scope and debug residue**

Run:

```powershell
git diff --check
git status --short
git diff --name-only origin/main...HEAD
rg -n "console\\.log|debugger|breakpoint\\(|print\\(" test-platform-v2/backend/app test-platform-v2/frontend/src
```

Expected: only Batch 47 evidence, Batch 48 fixes/tests/rules/reports; no database, credentials, browser state, backup or unrelated files.

- [ ] **Step 7: Show the mandatory change summary**

Use the repository template with branch `feature/batch-48-acceptance-fixes`, target `main`, every changed file, exact command/exit/pass counts and remaining risk.

- [ ] **Step 8: Ask the new push question and stop**

Ask:

```text
当前待推送范围如下。是否还有其他变动需要合并？
如果有，我将暂停推送；如果没有，请明确授权本次 push。
```

Expected: no `git push`, no PR and no completion confirmation until the user explicitly answers.
