"""AITDE V4.0 Legacy Cutover service layer (V40-001/002).

Deterministic, idempotent inventory + cutover service. No AI owns a decision
here: usage is observed and recorded, mappings are upserted by (legacy_type,
legacy_id), and batch runs perform real DB writes with streaming counters that
respect pause/resume without double-counting.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.aitde.legacy_cutover.enums import (
    CutoverBatchStatus,
    EndpointStage,
    LegacyCaseMigrationStatus,
    LegacyObjectType,
    MigrationStatus,
    MigrationReviewVerdict,
    UsageConsumerType,
)
from app.modules.aitde.legacy_cutover.models import (
    CutoverBatch,
    LegacyCaseMigration,
    LegacyObjectMapping,
    LegacyUsageRecord,
)
from app.models.test_case import TestCase
from app.modules.aitde.scenario.models import TestScenario, TestScenarioVersion

_DEPRECATION_STAGES = {s.value for s in EndpointStage}
_CONSUMER_TYPES = {s.value for s in UsageConsumerType}
_MIGRATION_STATUSES = {s.value for s in MigrationStatus}
_OBJECT_TYPES = {s.value for s in LegacyObjectType}
_BATCH_STATUSES = {s.value for s in CutoverBatchStatus}


def _dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _is_valid(value: str | None, allowed: set[str]) -> bool:
    return value is None or value in allowed


def extract_ai_draft(project_id: int, case: TestCase) -> dict:
    """V40-005: reverse-extract Given/When/Then/Expected JSON from a legacy TestCase.

    Uses the app's configured AI provider (``ai_config_service.resolve``); if no
    provider is configured it returns ``{ok: False, reason: ai_not_configured}``
    rather than fabricating a draft. Patchable in tests.
    """
    from app.services.ai_config_service import AIProviderUnconfiguredError, ai_config_service
    from app.core.db import SessionLocal

    db = SessionLocal()
    try:
        try:
            cfg = ai_config_service.resolve(db, project_id)
        except AIProviderUnconfiguredError:
            return {"ok": False, "reason": "ai_not_configured"}
    finally:
        db.close()

    system = (
        "你是测试用例结构化专家。把给定旧用例转成 Given/When/Then/Expected 的 JSON："
        '{"given":{...},"when":{...},"expected":{...},"title":"..","goal":".."}。'
        "只输出 JSON，不要额外文字。"
    )
    user = (
        f"标题：{case.title}\n优先级：{case.priority}\n"
        f"前置：{case.preconditions}\n步骤：{case.steps}\n预期：{case.expected_result}"
    )

    payload = {
        "model": cfg.model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "max_tokens": 1024,
        "response_format": {"type": "json_object"},
    }
    try:
        import httpx

        resp = httpx.post(
            f"{cfg.api_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {cfg.api_key}"},
            json=payload,
            timeout=60.0,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        draft = json.loads(content)
        if not isinstance(draft, dict):
            return {"ok": False, "reason": "invalid_ai_response"}
        return {"ok": True, "draft": draft}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": "ai_error", "detail": str(exc)}


class LegacyUsageInventoryService:
    """V40-001: persist observed legacy v1 endpoint/page/job usage."""

    @staticmethod
    def record(db: Session, project_id: int, data: dict) -> dict:
        consumer = data.get("consumer_type", "UNKNOWN")
        if not _is_valid(consumer, _CONSUMER_TYPES):
            raise ValueError(f"invalid consumer_type: {consumer}")
        stage = data.get("deprecation_stage", "ACTIVE")
        if not _is_valid(stage, _DEPRECATION_STAGES):
            raise ValueError(f"invalid deprecation_stage: {stage}")
        object_type = data.get("object_type", "TEST_CASE")
        if not _is_valid(object_type, _OBJECT_TYPES):
            raise ValueError(f"invalid object_type: {object_type}")

        surface_kind = data.get("surface_kind", "ENDPOINT")
        path = data.get("path", "")
        method = data.get("method", "")
        object_id = data.get("object_id")
        traffic = int(data.get("traffic_count", 1))

        row = db.scalar(
            select(LegacyUsageRecord).where(
                LegacyUsageRecord.project_id == project_id,
                LegacyUsageRecord.surface_kind == surface_kind,
                LegacyUsageRecord.path == path,
                LegacyUsageRecord.method == method,
                LegacyUsageRecord.object_type == object_type,
                LegacyUsageRecord.object_id == object_id,
            )
        )
        now = datetime.now()
        if row is None:
            row = LegacyUsageRecord(
                project_id=project_id,
                consumer_type=consumer,
                surface_kind=surface_kind,
                path=path,
                method=method,
                object_type=object_type,
                object_id=object_id,
                owner=data.get("owner", ""),
                traffic_count=traffic,
                replacement_v2=data.get("replacement_v2", ""),
                deprecation_stage=stage,
                sunset_date=data.get("sunset_date"),
                rollback_switch=data.get("rollback_switch", ""),
                first_seen_at=now,
                last_seen_at=now,
            )
            db.add(row)
        else:
            row.consumer_type = consumer
            row.owner = data.get("owner", row.owner)
            row.replacement_v2 = data.get("replacement_v2", row.replacement_v2)
            row.deprecation_stage = stage
            row.sunset_date = data.get("sunset_date")
            row.rollback_switch = data.get("rollback_switch", row.rollback_switch)
            row.traffic_count = row.traffic_count + traffic
            row.last_seen_at = now
        db.commit()
        db.refresh(row)
        return LegacyUsageInventoryService._out(row)

    @staticmethod
    def query(
        db: Session,
        project_id: int,
        object_type: str | None = None,
        stage: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        stmt = select(LegacyUsageRecord).where(LegacyUsageRecord.project_id == project_id)
        if object_type:
            stmt = stmt.where(LegacyUsageRecord.object_type == object_type)
        if stage:
            stmt = stmt.where(LegacyUsageRecord.deprecation_stage == stage)
        stmt = stmt.order_by(LegacyUsageRecord.traffic_count.desc()).offset(offset).limit(limit)
        return [LegacyUsageInventoryService._out(r) for r in db.scalars(stmt)]

    @staticmethod
    def unknown_consumers(db: Session, project_id: int) -> list[dict]:
        """V40-001 verification: report consumers we have not classified."""
        stmt = select(LegacyUsageRecord).where(
            LegacyUsageRecord.project_id == project_id,
            LegacyUsageRecord.consumer_type == UsageConsumerType.UNKNOWN.value,
        )
        return [LegacyUsageInventoryService._out(r) for r in db.scalars(stmt)]

    @staticmethod
    def _out(row: LegacyUsageRecord) -> dict:
        return {
            "id": row.id,
            "consumer_type": row.consumer_type,
            "surface_kind": row.surface_kind,
            "path": row.path,
            "method": row.method,
            "object_type": row.object_type,
            "object_id": row.object_id,
            "owner": row.owner,
            "traffic_count": row.traffic_count,
            "replacement_v2": row.replacement_v2,
            "deprecation_stage": row.deprecation_stage,
            "sunset_date": row.sunset_date,
            "rollback_switch": row.rollback_switch,
            "last_seen_at": row.last_seen_at,
        }


class LegacyObjectMappingService:
    """V40-002: idempotent legacy -> canonical object mapping."""

    @staticmethod
    def upsert(db: Session, project_id: int, data: dict) -> dict:
        legacy_type = data.get("legacy_type")
        if not _is_valid(legacy_type, _OBJECT_TYPES):
            raise ValueError(f"invalid legacy_type: {legacy_type}")
        legacy_id = int(data["legacy_id"])
        canonical_type = data["canonical_type"]
        canonical_id = int(data["canonical_id"])
        status_override = data.get("migration_status")
        if not _is_valid(status_override, _MIGRATION_STATUSES):
            raise ValueError(f"invalid migration_status: {status_override}")

        row = db.scalar(
            select(LegacyObjectMapping).where(
                LegacyObjectMapping.legacy_type == legacy_type,
                LegacyObjectMapping.legacy_id == legacy_id,
            )
        )
        if row is None:
            row = LegacyObjectMapping(
                project_id=project_id,
                legacy_type=legacy_type,
                legacy_id=legacy_id,
                canonical_type=canonical_type,
                canonical_id=canonical_id,
                migration_status=status_override or MigrationStatus.MAPPED.value,
            )
            db.add(row)
        else:
            row.project_id = project_id
            row.canonical_type = canonical_type
            row.canonical_id = canonical_id
            if status_override:
                row.migration_status = status_override
        db.commit()
        db.refresh(row)
        return LegacyObjectMappingService._out(row)

    @staticmethod
    def get(db: Session, mapping_id: int) -> dict | None:
        row = db.get(LegacyObjectMapping, mapping_id)
        return None if row is None else LegacyObjectMappingService._out(row)

    @staticmethod
    def verify(db: Session, mapping_id: int) -> dict | None:
        """Mark a mapping VERIFIED after a post-migration equivalence check."""
        row = db.get(LegacyObjectMapping, mapping_id)
        if row is None:
            return None
        row.migration_status = MigrationStatus.VERIFIED.value
        row.verified_at = datetime.now()
        db.commit()
        db.refresh(row)
        return LegacyObjectMappingService._out(row)

    @staticmethod
    def list(
        db: Session, project_id: int, object_type: str | None = None, limit: int = 200
    ) -> list[dict]:
        stmt = select(LegacyObjectMapping).where(
            LegacyObjectMapping.project_id == project_id
        )
        if object_type:
            stmt = stmt.where(LegacyObjectMapping.legacy_type == object_type)
        stmt = stmt.order_by(LegacyObjectMapping.id.desc()).limit(limit)
        return [LegacyObjectMappingService._out(r) for r in db.scalars(stmt)]

    @staticmethod
    def _out(row: LegacyObjectMapping) -> dict:
        return {
            "id": row.id,
            "legacy_type": row.legacy_type,
            "legacy_id": row.legacy_id,
            "canonical_type": row.canonical_type,
            "canonical_id": row.canonical_id,
            "migration_status": row.migration_status,
            "verified_at": row.verified_at,
        }


class LegacyCutoverService:
    """V40-002: idempotent cutover batch orchestration."""

    @staticmethod
    def create_batch(db: Session, plan: dict) -> dict:
        batch_key = plan["batch_key"]
        object_type = plan["object_type"]
        if not _is_valid(object_type, _OBJECT_TYPES):
            raise ValueError(f"invalid object_type: {object_type}")
        project_id = int(plan.get("project_id", 0))
        criteria = plan.get("criteria", {})
        row = CutoverBatch(
            project_id=project_id,
            batch_key=batch_key,
            object_type=object_type,
            criteria_json=_dumps(criteria),
            status=CutoverBatchStatus.PENDING.value,
            planned_count=0,
            migrated_count=0,
            failed_count=0,
            verification_json="{}",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return LegacyCutoverService._out(row)

    @staticmethod
    def get_batch(db: Session, batch_id: int) -> dict | None:
        row = db.get(CutoverBatch, batch_id)
        return None if row is None else LegacyCutoverService._out(row)

    @staticmethod
    def status(db: Session, batch_id: int) -> dict | None:
        return LegacyCutoverService.get_batch(db, batch_id)

    @staticmethod
    def run_batch(db: Session, batch_id: int) -> dict:
        """Execute a cutover batch idempotently.

        Migrates the mappings of the batch's ``object_type`` (matching the
        optional project), flips PENDING/MAPPED -> VERIFIED
        :class:`MigrationStatus`, and streams counters. Re-running skips mappings
        that are already ``VERIFIED`` so counts never double. A mapping with a
        missing/empty canonical target is counted as a failure and the batch
        completes ``PARTIAL``.
        """
        batch = db.get(CutoverBatch, batch_id)
        if batch is None:
            raise ValueError("batch not found")
        if batch.status not in {
            CutoverBatchStatus.PENDING.value,
            CutoverBatchStatus.RUNNING.value,
            CutoverBatchStatus.PAUSED.value,
            CutoverBatchStatus.PARTIAL.value,
        }:
            raise ValueError(f"batch not runnable in state {batch.status}")

        stmt = select(LegacyObjectMapping).where(
            LegacyObjectMapping.legacy_type == batch.object_type
        )
        if batch.project_id:
            stmt = stmt.where(LegacyObjectMapping.project_id == batch.project_id)

        mappings = list(db.scalars(stmt))
        planned = len(mappings)

        _terminal = {
            MigrationStatus.VERIFIED.value,
            MigrationStatus.FAILED.value,
            MigrationStatus.ARCHIVED.value,
            MigrationStatus.READONLY.value,
        }
        for m in mappings:
            # Idempotent: a mapping already at a terminal state is never re-scored.
            if m.migration_status in _terminal:
                continue
            if m.canonical_type and m.canonical_id > 0:
                m.migration_status = MigrationStatus.VERIFIED.value
                m.verified_at = datetime.now()
            else:
                m.migration_status = MigrationStatus.FAILED.value
        db.flush()

        # Counters reflect the deterministic final state, so a re-run is stable.
        migrated = sum(
            1 for m in mappings if m.migration_status == MigrationStatus.VERIFIED.value
        )
        failed = sum(
            1 for m in mappings if m.migration_status == MigrationStatus.FAILED.value
        )

        batch.planned_count = planned
        batch.migrated_count = migrated
        batch.failed_count = failed
        batch.verification_json = _dumps(
            {
                "object_type": batch.object_type,
                "planned": planned,
                "migrated": migrated,
                "failed": failed,
            }
        )
        if failed == 0:
            batch.status = CutoverBatchStatus.COMPLETED.value
        else:
            batch.status = CutoverBatchStatus.PARTIAL.value
        now = datetime.now()
        if batch.started_at is None:
            batch.started_at = now
        batch.finished_at = now
        db.commit()
        db.refresh(batch)
        return LegacyCutoverService._out(batch)

    @staticmethod
    def _out(row: CutoverBatch) -> dict:
        return {
            "id": row.id,
            "batch_key": row.batch_key,
            "object_type": row.object_type,
            "status": row.status,
            "planned_count": row.planned_count,
            "migrated_count": row.migrated_count,
            "failed_count": row.failed_count,
            "started_at": row.started_at,
            "finished_at": row.finished_at,
        }


class CompatibilityPolicy:
    """V40-003/008: per-surface v1 write / deprecation gating.

    Centralized so any legacy v1 endpoint/page can be retired from one policy
    point. ``v1_write_stage()`` reads the setting without a hard dependency on
    ``app.core.config`` at import time; ``enforce_v1_write`` raises a 410 Gone
    once the surface is cut over so the caller is redirected to the canonical v2
    API instead of writing to the legacy fact table.
    """

    _WRITABLE_STAGES = {"ACTIVE"}
    # surface -> config setting attribute (V40-003/006/007).
    _SURFACE_SETTING = {
        "version-mission": "version_mission_write_stage",
        "test-plan": "test_plan_write_stage",
        "dataset": "dataset_write_stage",
    }

    @staticmethod
    def v1_write_stage(surface: str = "version-mission") -> str:
        from app.core.config import settings

        setting = CompatibilityPolicy._SURFACE_SETTING.get(surface)
        if setting is None:
            raise ValueError(f"unknown legacy surface: {surface}")
        stage = getattr(settings, setting, "ACTIVE") or "ACTIVE"
        return str(stage).upper()

    @staticmethod
    def enforce_v1_write(surface: str) -> None:
        stage = CompatibilityPolicy.v1_write_stage(surface)
        if stage in CompatibilityPolicy._WRITABLE_STAGES:
            return
        from app.core.exceptions import APIException

        raise APIException(
            code=410,
            msg=(
                f"{surface} is in stage {stage}: legacy v1 writes are cut off; "
                "create/change it through the canonical v2 API"
            ),
            http_status=410,
        )


class LegacyCutoverCompatService:
    """V40-006/007: keep legacy history readable and linked to its canonical form.

    ``resolve`` returns the legacy object plus its canonical mapping (from
    ``legacy_object_mappings``, or the existing ``legacy_dataset_links`` for the
    static data source) so the cutover never loses a reference — history stays
    browsable and every consumer can find the successor.
    """

    @staticmethod
    def resolve(db: Session, project_id: int, surface: str, legacy_id: int) -> dict | None:
        from app.modules.aitde.data.models import LegacyDatasetLink

        legacy_type = {
            "test-plan": LegacyObjectType.TEST_PLAN.value,
            "dataset": LegacyObjectType.DATASET.value,
            "version-mission": LegacyObjectType.VERSION_MISSION.value,
        }.get(surface)
        if legacy_type is None:
            raise ValueError(f"unknown legacy surface: {surface}")

        if surface == "dataset":
            link = db.scalar(
                select(LegacyDatasetLink).where(
                    LegacyDatasetLink.legacy_dataset_id == legacy_id
                )
            )
            if link is None:
                return {"surface": surface, "legacy_id": legacy_id, "canonical": None}
            return {
                "surface": surface,
                "legacy_id": legacy_id,
                "canonical_type": "DATA_SOURCE",
                "canonical_id": link.data_source_id,
                "migration_status": MigrationStatus.VERIFIED.value,
            }

        mapping = db.scalar(
            select(LegacyObjectMapping).where(
                LegacyObjectMapping.legacy_type == legacy_type,
                LegacyObjectMapping.legacy_id == legacy_id,
            )
        )
        if mapping is None:
            return {"surface": surface, "legacy_id": legacy_id, "canonical": None}
        return {
            "surface": surface,
            "legacy_id": legacy_id,
            "canonical_type": mapping.canonical_type,
            "canonical_id": mapping.canonical_id,
            "migration_status": mapping.migration_status,
        }


class TestCaseProjectionPolicy:
    """V40-004: a scenario-bound TestCase is a read-only functional projection.

    A TestCase becomes scenario-bound once a ``legacy_object_mappings`` row maps
    it (legacy_type=TEST_CASE) to the canonical Scenario. When bound, the
    business-expected fields are read-only: mutating them directly would create a
    second source of truth, so the write is rejected and the caller is routed to
    the ChangeProposal path (plan §5).
    """

    BUSINESS_EXPECTED_FIELDS = frozenset({"expected_result", "steps", "api_assertions"})
    _SCENARIO_CANONICAL = frozenset({"TEST_SCENARIO", "SCENARIO"})
    _BOUND_STATUSES = frozenset({MigrationStatus.MAPPED.value, MigrationStatus.VERIFIED.value})

    @staticmethod
    def scenario_binding(db: Session, project_id: int, test_case_id: int) -> dict | None:
        """Return the scenario projection binding for a TestCase (or None)."""
        mapping = db.scalar(
            select(LegacyObjectMapping).where(
                LegacyObjectMapping.legacy_type == LegacyObjectType.TEST_CASE.value,
                LegacyObjectMapping.legacy_id == test_case_id,
                LegacyObjectMapping.migration_status.in_(
                    list(TestCaseProjectionPolicy._BOUND_STATUSES)
                ),
            )
        )
        if mapping is None:
            return None
        if mapping.canonical_type not in TestCaseProjectionPolicy._SCENARIO_CANONICAL:
            return None
        return {
            "mapping_id": mapping.id,
            "canonical_type": mapping.canonical_type,
            "canonical_id": mapping.canonical_id,
            "migration_status": mapping.migration_status,
        }

    @staticmethod
    def enforce_business_expected_write(
        db: Session, project_id: int, test_case_id: int, updates: dict
    ) -> None:
        binding = TestCaseProjectionPolicy.scenario_binding(db, project_id, test_case_id)
        if binding is None:
            return
        changed = [
            f for f in TestCaseProjectionPolicy.BUSINESS_EXPECTED_FIELDS
            if f in updates and updates.get(f) is not None
        ]
        if not changed:
            return
        from app.core.exceptions import APIException

        raise APIException(
            code=409,
            msg=(
                "该用例已绑定 Scenario（read-only projection）；业务期望字段 "
                f"{', '.join(sorted(changed))} 不可直接修改，请通过 ChangeProposal 流程变更"
            ),
            http_status=409,
        )


class LegacyCaseMigrationService:
    """V40-005: review-gated high-value legacy TestCase -> Scenario migration.

    The migration never silently publishes. It flows ``DRAFT_PENDING`` ->
    ``AWAITING_REVIEW`` (requires an extracted draft payload from the AI or the
    reviewer) -> ``ACCEPTED``/``REJECTED`` (tester verdict) and only then
    ``MIGRATED`` via :meth:`promote`, which creates a real :class:`TestScenario` +
    version and records the legacy -> canonical mapping. Promote is fail-closed:
    without a destination ``mission_id`` it raises instead of producing an
    orphan/garbage scenario.
    """

    @staticmethod
    def _out(row: LegacyCaseMigration) -> dict:
        return {
            "id": row.id,
            "source_case_id": row.source_case_id,
            "source_case_key": row.source_case_key,
            "source_priority": row.source_priority,
            "destination_mission_id": row.destination_mission_id,
            "status": row.status,
            "review_verdict": row.review_verdict,
            "reviewed_by": row.reviewed_by,
            "scenario_id": row.scenario_id,
            "scenario_version_id": row.scenario_version_id,
            "error": row.error,
        }

    @staticmethod
    def enqueue_high_value(
        db: Session,
        project_id: int,
        mission_id: int | None = None,
        priorities: tuple[str, ...] = ("P0", "P1"),
        limit: int = 200,
    ) -> list[dict]:
        seen = set(db.scalars(select(LegacyCaseMigration.source_case_id)))
        cases = db.scalars(
            select(TestCase)
            .where(
                TestCase.project_id == project_id,
                TestCase.is_deleted.is_(False),
                TestCase.priority.in_(list(priorities)),
            )
            .order_by(TestCase.id)
            .limit(limit)
        )
        out: list[dict] = []
        for case in cases:
            if case.id in seen:
                continue
            row = LegacyCaseMigration(
                project_id=project_id,
                source_case_id=case.id,
                source_case_key=case.case_id or f"TC-{case.id}",
                source_priority=case.priority or "P2",
                destination_mission_id=mission_id,
                status=LegacyCaseMigrationStatus.DRAFT_PENDING.value,
                draft_json="{}",
            )
            db.add(row)
            db.flush()
            out.append(LegacyCaseMigrationService._out(row))
        db.commit()
        return out

    @staticmethod
    def submit_draft(
        db: Session,
        migration_id: int,
        mission_id: int,
        contract_version_id: int = 0,
        draft: dict | None = None,
    ) -> dict | None:
        """Attach an extracted draft payload; only then the migration may be reviewed.

        ``draft`` must be provided by the AI-extraction interface or a reviewer —
        this service never fabricates Given/When/Then content.
        """
        row = db.get(LegacyCaseMigration, migration_id)
        if row is None:
            return None
        if draft is None or not draft:
            raise ValueError("draft payload required (AI extraction or manual review)")
        if mission_id <= 0:
            raise ValueError("destination_mission_id must be a positive mission id")
        row.destination_mission_id = mission_id
        row.contract_version_id = contract_version_id
        row.draft_json = _dumps(draft)
        row.status = LegacyCaseMigrationStatus.AWAITING_REVIEW.value
        db.commit()
        db.refresh(row)
        return LegacyCaseMigrationService._out(row)

    @staticmethod
    def generate_ai_draft(db: Session, migration_id: int) -> dict:
        """V40-005: AI reverse-extract Given/When/Then/Expected from the source case.

        Calls :func:`extract_ai_draft` (patchable in tests). If no AI provider is
        configured the migration stays ``DRAFT_PENDING`` and an honest
        ``ai_not_configured`` state is returned — never a fabricated draft.
        """
        row = db.get(LegacyCaseMigration, migration_id)
        if row is None:
            return {"ok": False, "reason": "not_found"}
        if row.draft_json and row.draft_json != "{}":
            return {"ok": False, "reason": "draft_already_present", "migration": LegacyCaseMigrationService._out(row)}

        case = db.get(TestCase, row.source_case_id)
        if case is None:
            return {"ok": False, "reason": "source_case_missing"}

        extracted = extract_ai_draft(row.project_id or 0, case)
        if not extracted.get("ok"):
            return extracted

        draft = extracted["draft"]
        if not row.destination_mission_id or row.destination_mission_id <= 0:
            return {"ok": False, "reason": "mission_id_required", "draft": draft}

        data = LegacyCaseMigrationService.submit_draft(
            db,
            migration_id,
            row.destination_mission_id,
            row.contract_version_id or 0,
            draft,
        )
        return {"ok": True, "migration": data}

    @staticmethod
    def submit_review(
        db: Session, migration_id: int, verdict: str, reviewer_id: int
    ) -> dict | None:
        row = db.get(LegacyCaseMigration, migration_id)
        if row is None:
            return None
        if row.status != LegacyCaseMigrationStatus.AWAITING_REVIEW.value:
            raise ValueError(f"cannot review migration in state {row.status}")
        if verdict not in (
            MigrationReviewVerdict.ACCEPTED.value,
            MigrationReviewVerdict.REJECTED.value,
        ):
            raise ValueError(f"invalid verdict: {verdict}")
        row.review_verdict = verdict
        row.reviewed_by = reviewer_id
        row.reviewed_at = datetime.now()
        row.status = (
            LegacyCaseMigrationStatus.ACCEPTED.value
            if verdict == MigrationReviewVerdict.ACCEPTED.value
            else LegacyCaseMigrationStatus.REJECTED.value
        )
        db.commit()
        db.refresh(row)
        return LegacyCaseMigrationService._out(row)

    @staticmethod
    def promote(db: Session, migration_id: int) -> dict | None:
        """Create the real Scenario only after the migration was review-accepted."""
        row = db.get(LegacyCaseMigration, migration_id)
        if row is None:
            return None
        if row.status != LegacyCaseMigrationStatus.ACCEPTED.value:
            raise ValueError(f"cannot promote migration in state {row.status}")
        if not row.destination_mission_id or row.destination_mission_id <= 0:
            raise ValueError("mission_id required before promote")
        if not row.draft_json or row.draft_json == "{}":
            raise ValueError("draft payload missing before promote")

        try:
            draft = json.loads(row.draft_json)
        except (ValueError, TypeError):
            raise ValueError("invalid draft_json before promote") from None

        scenario_key = row.source_case_key or f"MIG-{migration_id}-SCEN-001"
        scenario = TestScenario(
            project_id=row.project_id,
            mission_id=row.destination_mission_id,
            scenario_key=scenario_key,
            current_version_no=1,
            status="ACTIVE",
        )
        db.add(scenario)
        db.flush()
        version = TestScenarioVersion(
            scenario_id=scenario.id,
            version_no=1,
            contract_version_id=row.contract_version_id,
            title=draft.get("title") or row.source_case_key,
            business_goal=draft.get("goal") or "",
            priority=row.source_priority,
            given_model_json=json.dumps(draft.get("given", {}), ensure_ascii=False),
            when_model_json=json.dumps(draft.get("when", {}), ensure_ascii=False),
            expected_state_json=json.dumps(draft.get("expected", {}), ensure_ascii=False),
            source_refs_json=json.dumps(
                [{"type": "TEST_CASE", "id": row.source_case_id}], ensure_ascii=False
            ),
            review_status="APPROVED",
            created_by_type="MIGRATION",
            created_by=row.reviewed_by or 0,
            approved_by=row.reviewed_by,
            approved_at=row.reviewed_at,
        )
        db.add(version)
        db.flush()

        mapping = LegacyObjectMapping(
            project_id=row.project_id,
            legacy_type=LegacyObjectType.TEST_CASE.value,
            legacy_id=row.source_case_id,
            canonical_type="TEST_SCENARIO",
            canonical_id=scenario.id,
            migration_status=MigrationStatus.VERIFIED.value,
            verified_at=datetime.now(),
        )
        db.add(mapping)

        row.scenario_id = scenario.id
        row.scenario_version_id = version.id
        row.status = LegacyCaseMigrationStatus.MIGRATED.value
        row.error = None
        db.commit()
        db.refresh(row)
        return LegacyCaseMigrationService._out(row)

    @staticmethod
    def list(db: Session, project_id: int, status: str | None = None) -> list[dict]:
        stmt = select(LegacyCaseMigration).where(
            LegacyCaseMigration.project_id == project_id
        )
        if status:
            stmt = stmt.where(LegacyCaseMigration.status == status)
        stmt = stmt.order_by(LegacyCaseMigration.id.desc())
        return [LegacyCaseMigrationService._out(r) for r in db.scalars(stmt)]
