"""AITDE V3.6 production services (V36-002..V36-012).

SVC        Purpose
---------- ---------------------------------------------------------------
Observer   create/stop/status observation session (persistent, recoverable)
XhrEvid    upgrade XHR capture → persistent session + sanitizer + Evidence
DbExplorer SELECT-only explore via ProductionDbGuard; row/time caps
QueryAudit record EVERY production query (100% coverage)
Pii        classify a field/value into a PII class
Mask       apply a masking profile; deterministic token keeps relation
EntityGraph extract an entity graph from a root ref (depth/row/cycle caps)
Template   build a masked, PII-free test template from a graph
Material   write a template into a Test Environment fixture (remap ids)
Gap        produce Evidence gap proposals (never auto-approve prod behaviour)
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import (
    GapProposalKind,
    MaskingStrategy,
    MaterializationStatus,
    ObservationMode,
    ObservationSessionStatus,
    PiiClassification,
    PolicyDecision,
)
from app.modules.aitde.data import repository as data_repository
from app.modules.aitde.production import repository as repo
from app.modules.aitde.production import policies
from app.modules.aitde.production.policies import (
    ProductionDbGuard,
    production_db_guard,
)


def _j(value: Any) -> Any:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


# ── V36-002: Persistent Observation Session ────────────────────────────────
class ProductionObserverService:
    """Create / stop / status an observation session. State persists in the DB,
    so a backend restart can resume or finish a session (task-level check)."""

    def start(
        self,
        db: Session,
        *,
        project_id: int,
        environment_id: int,
        mission_id: int | None,
        worker_id: int | None,
        mode: str,
        started_by: int,
        policy_version: str = "1.0",
    ) -> int:
        try:
            mode_val = ObservationMode(mode).value
        except ValueError:
            raise APIException(code=400, msg=f"无效观察模式: {mode}", http_status=400)
        row = repo.create_observation_session(
            db,
            {
                "project_id": project_id,
                "environment_id": environment_id,
                "mission_id": mission_id,
                "worker_id": worker_id,
                "mode": mode_val,
                "status": ObservationSessionStatus.ACTIVE.value,
                "policy_version": policy_version,
                "started_by": started_by,
            },
        )
        return row.id

    def stop(self, db: Session, session_id: int, *, user_id: int) -> None:
        row = repo.get_observation_session(db, session_id)
        if row is None:
            raise APIException(code=404, msg="观察会话不存在", http_status=404)
        repo.update_observation_session(
            db,
            session_id,
            {"status": ObservationSessionStatus.FINISHED.value, "finished_at": datetime.now()},
        )

    def status(self, db: Session, session_id: int) -> dict[str, Any]:
        row = repo.get_observation_session(db, session_id)
        if row is None:
            raise APIException(code=404, msg="观察会话不存在", http_status=404)
        return {
            "id": row.id,
            "project_id": row.project_id,
            "mission_id": row.mission_id,
            "environment_id": row.environment_id,
            "worker_id": row.worker_id,
            "mode": row.mode,
            "status": row.status,
            "policy_version": row.policy_version,
            "started_by": row.started_by,
            "started_at": row.started_at.isoformat() if row.started_at else None,
            "finished_at": row.finished_at.isoformat() if row.finished_at else None,
        }

    def recover_after_restart(self, db: Session) -> int:
        """Finish any ACTIVE session that survives a backend restart (V36-002)."""
        active = repo.list_observation_sessions(db, project_id=-1, status=None)
        count = 0
        for row in active:
            if row.status == ObservationSessionStatus.ACTIVE.value:
                repo.update_observation_session(
                    db, row.id, {"status": ObservationSessionStatus.FINISHED.value}
                )
                count += 1
        # Explicitly handle all ACTIVE rows regardless of project filter.
        from sqlalchemy import select
        from app.models.production_evidence import ProductionObservationSession

        rows = db.scalars(
            select(ProductionObservationSession).where(
                ProductionObservationSession.status == ObservationSessionStatus.ACTIVE.value
            )
        ).all()
        for row in rows:
            repo.update_observation_session(
                db, row.id, {"status": ObservationSessionStatus.FINISHED.value}
            )
            count += 1
        return count


production_observer_service = ProductionObserverService()


# ── V36-004: XHR Evidence Upgrade ──────────────────────────────────────────
class XhrEvidenceService:
    """Capture XHR from a read-only browser page, sanitise it and persist the
    evidence against the current observation session as an ObservedJourney.

    Uses EvidenceSanitizer for Authorization/Cookie/token redaction and
    Environment.base_url rather than a hardcoded host.
    """

    def __init__(
        self,
        sanitizer: Callable[..., tuple[bytes, str]] | None = None,
        *,
        base_url: str | None = None,
    ) -> None:
        from app.modules.aitde.evidence.sanitizer import sanitize as _sanitize

        # ``sanitize`` returns (bytes, status); status value is compared as str.
        self._sanitizer = sanitizer or (lambda data, ctype, headers: _sanitize(data, ctype, headers))
        self._base_url = base_url or ""

    def set_base_url(self, base_url: str) -> None:
        self._base_url = base_url or ""

    @property
    def base_url(self) -> str:
        return self._base_url

    def capture(
        self,
        db: Session,
        *,
        session_id: int,
        project_id: int,
        journey_name: str,
        events: list[dict[str, Any]],
    ) -> int:
        """Persist one observed journey + sanitised steps for a session."""
        journey = repo.create_journey(
            db,
            {
                "project_id": project_id,
                "session_id": session_id,
                "name": journey_name,
                "journey_hash": hashlib.sha256(
                    json.dumps(events, ensure_ascii=False).encode()
                ).hexdigest(),
                "summary_json": _j({"event_count": len(events)}),
                "source_ref_json": _j({"base_url": self._base_url}),
            },
        )
        steps = []
        for ev in events:
            headers = ev.get("headers") or {}
            safe_headers = self._redact_headers(headers)
            body = ev.get("body") or ""
            safe_body = self._sanitize_body(body, ev.get("content_type"))
            steps.append(
                {
                    "event_type": ev.get("event_type", "XHR"),
                    "semantic_action_json": _j(ev.get("semantic_action") or {}),
                    "url_template": ev.get("url") or "",
                    "xhr_refs_json": _j(
                        {
                            "method": ev.get("method"),
                            "status": ev.get("status"),
                            "headers": safe_headers,
                            "body": safe_body,
                        }
                    ),
                    "evidence_refs_json": _j(ev.get("evidence_refs") or []),
                }
            )
        repo.create_journey_steps(db, journey.id, steps)
        return journey.id

    def _redact_headers(self, headers: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k, v in (headers or {}).items():
            if k.lower() in {"authorization", "cookie", "set-cookie", "x-api-key", "api-key", "x-auth-token"}:
                out[k] = "<REDACTED>"
            else:
                out[k] = v
        return out

    def _sanitize_body(self, body: Any, content_type: str | None) -> str:
        if isinstance(body, str):
            data = body.encode("utf-8", errors="replace")
        else:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8", errors="replace")
        try:
            safe, _status = self._sanitizer(data, content_type or "application/json", {})
            return safe.decode("utf-8", errors="replace")
        except Exception:
            return "<REDACTED>"


xhr_evidence_service = XhrEvidenceService()


# ── V36-005/006: Prod DB Explorer + Query Audit ─────────────────────────────
class ProductionDbExplorer:
    """Run a read-only query against a production DataSource.

    Selection goes through ProductionDbGuard (SELECT-only + row/time/schema
    caps). Every query is audited (V36-006, 100% coverage) — unless the guard
    DENY, in which case we still record the attempted query as DENIED.
    """

    def __init__(self, guard: ProductionDbGuard | None = None) -> None:
        self._guard = guard or production_db_guard

    def inspect(
        self,
        db: Session,
        *,
        project_id: int,
        data_source_id: int,
        session_id: int | None,
        sql: str,
        schema: str | None,
        row_provider: Callable[[str], list[dict[str, Any]]] | None = None,
        table_names: list[str] | None = None,
    ) -> dict[str, Any]:
        ok, reason = self._guard.guard_scan(sql, table_names)
        if not ok:
            repo.create_query_audit(
                db,
                {
                    "project_id": project_id,
                    "session_id": session_id,
                    "data_source_id": data_source_id,
                    "query_fingerprint": policies.fingerprint_sql(sql),
                    "operation_type": "SELECT",
                    "schema_name": schema,
                    "table_names_json": _j(table_names or []),
                    "row_count": 0,
                    "duration_ms": 0,
                    "policy_decision": PolicyDecision.DENY.value,
                },
            )
            raise APIException(code=400, msg=f"生产查询被拒绝: {reason}", http_status=400)

        started = datetime.now()
        rows = row_provider(sql) if row_provider else []
        duration_ms = int((datetime.now() - started).total_seconds() * 1000)
        repo.create_query_audit(
            db,
            {
                "project_id": project_id,
                "session_id": session_id,
                "data_source_id": data_source_id,
                "query_fingerprint": policies.fingerprint_sql(sql),
                "operation_type": "SELECT",
                "schema_name": schema,
                "table_names_json": _j(table_names or []),
                "row_count": len(rows),
                "duration_ms": duration_ms,
                "policy_decision": PolicyDecision.ALLOW.value,
            },
        )
        return {"rows": rows, "row_count": len(rows), "duration_ms": duration_ms}


production_db_explorer = ProductionDbExplorer()


# ── V36-007: PII Classifier ─────────────────────────────────────────────────
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?86)?1[3-9]\d{9}(?!\d)")
_ID_RE = re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")  # 18 位身份证
_IP_RE = re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")
_TOKEN_RE = re.compile(r"(?i)(bearer\s+[A-Za-z0-9._~+/=-]{8,}|eyJ[A-Za-z0-9_-]{10,})")
# Field-name heuristics → class
_FIELD_NAME_MAP = {
    "email": PiiClassification.EMAIL,
    "phone": PiiClassification.PHONE,
    "mobile": PiiClassification.PHONE,
    "mobilephone": PiiClassification.PHONE,
    "name": PiiClassification.PERSON_NAME,
    "realname": PiiClassification.PERSON_NAME,
    "username": PiiClassification.PERSON_NAME,
    "idcard": PiiClassification.ID_NUMBER,
    "id_number": PiiClassification.ID_NUMBER,
    "address": PiiClassification.ADDRESS,
    "bank_account": PiiClassification.BANK_ACCOUNT,
    "bankcard": PiiClassification.BANK_ACCOUNT,
    "token": PiiClassification.TOKEN,
    "access_token": PiiClassification.TOKEN,
    "device_id": PiiClassification.DEVICE_ID,
    "deviceid": PiiClassification.DEVICE_ID,
    "ip": PiiClassification.IP,
    "ipaddress": PiiClassification.IP,
}


class PiiClassifier:
    """V36-007 — classify a value / field into a PII class (rules-first)."""

    def classify(self, field_name: str = "", value: str = "") -> str:
        fn = (field_name or "").lower()
        if fn in _FIELD_NAME_MAP:
            return _FIELD_NAME_MAP[fn].value
        if not value:
            return PiiClassification.FREE_TEXT.value
        if _EMAIL_RE.search(value):
            return PiiClassification.EMAIL.value
        if _PHONE_RE.search(value):
            return PiiClassification.PHONE.value
        if _ID_RE.search(value):
            return PiiClassification.ID_NUMBER.value
        if _IP_RE.search(value):
            return PiiClassification.IP.value
        if _TOKEN_RE.search(value):
            return PiiClassification.TOKEN.value
        return PiiClassification.FREE_TEXT.value


pii_classifier = PiiClassifier()


# ── V36-008: Masking Service ────────────────────────────────────────────────
def _deterministic_token(value: str, *, salt: str) -> str:
    return "tok_" + hashlib.sha256(f"{salt}:{value}".encode()).hexdigest()[:16]


class MaskingService:
    """Apply a masking profile to a dict-shaped record. Deterministic token
    (keyed by profile salt) preserves cross-record relations (V36-008)."""

    def __init__(self, classifier: PiiClassifier | None = None) -> None:
        self._classifier = classifier or pii_classifier

    def apply(self, *, profile_id: int, rules: list[Any], record: dict[str, Any]) -> dict[str, Any]:
        """Apply each matching rule. ``rules`` are MaskingRule ORM rows."""
        results: dict[str, Any] = {}
        for key, value in record.items():
            matched = False
            for rule in rules:
                if rule.field_pattern not in {"*", key}:
                    continue
                matched = True
                strat = rule.strategy
                if strat == MaskingStrategy.PRESERVE.value:
                    results[key] = value
                elif strat == MaskingStrategy.REDACT.value:
                    results[key] = "<REDACTED>"
                elif strat == MaskingStrategy.HASH.value:
                    results[key] = hashlib.sha256(str(value).encode()).hexdigest()
                elif strat == MaskingStrategy.TOKENIZE.value:
                    results[key] = _deterministic_token(str(value), salt=f"profile-{profile_id}")
                elif strat == MaskingStrategy.FAKE.value:
                    results[key] = f"fake_{hashlib.sha256(str(value).encode()).hexdigest()[:8]}"
                else:
                    results[key] = value
                break
            if not matched:
                results[key] = value
        return results

    def validation_report(self, *, profile_id: int, record: dict[str, Any]) -> dict[str, Any]:
        """Return a report that no raw sensitive value survives in the output.
        Checks the record values against the classification vocabulary."""
        masked = self.apply(profile_id=profile_id, rules=[], record=record)
        leaks = []
        for key, value in record.items():
            out = masked.get(key)
            if str(value) and str(value) == str(out):
                cls = self._classifier.classify(key, str(value))
                if cls != PiiClassification.FREE_TEXT.value:
                    leaks.append({"field": key, "classification": cls})
        return {"leaks": leaks, "valid": not leaks}


masking_service = MaskingService()


# ── V36-009: Entity Graph Extractor ─────────────────────────────────────────
class EntityGraphExtractor:
    """Extract a relation graph from a root entity reference. FK / config
    relations with depth, node and row caps; cycle-safe."""

    def __init__(self, *, max_depth: int = 4, max_nodes: int = 200, max_rows: int = 1000) -> None:
        self.max_depth = max_depth
        self.max_nodes = max_nodes
        self.max_rows = max_rows

    def extract(
        self,
        *,
        root_entity_type: str,
        root_ref_hash: str,
        child_loader: Callable[[str, str, int], list[dict[str, Any]]],
    ) -> tuple[dict[str, Any], str]:
        """BFS over relations. ``child_loader`` returns child nodes for a given
        (parent_entity_type, parent_ref_hash, depth). Returns (graph, content_hash)."""
        visited: set[tuple[str, str]] = set()
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        queue: list[tuple[str, str, int]] = [(root_entity_type, root_ref_hash, 0)]
        while queue:
            entry = queue.pop(0)
            etype, ref, depth = entry
            if (etype, ref) in visited:
                continue
            visited.add((etype, ref))
            if len(nodes) >= self.max_nodes or depth > self.max_depth:
                break
            children = child_loader(etype, ref, depth)
            if len(children) > self.max_rows:
                children = children[: self.max_rows]
            node_id = f"{etype}:{ref}"
            nodes.append({"id": node_id, "entity_type": etype, "ref_hash": ref, "depth": depth})
            for child in children:
                ctype = child.get("entity_type", "")
                cref = child.get("ref_hash", "")
                if not ctype:
                    continue
                edges.append({"from": node_id, "to": f"{ctype}:{cref}", "relation": child.get("relation", "FK")})
                queue.append((ctype, cref, depth + 1))
        graph = {"root": f"{root_entity_type}:{root_ref_hash}", "nodes": nodes, "edges": edges}
        content_hash = hashlib.sha256(json.dumps(graph, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        return graph, content_hash


entity_graph_extractor = EntityGraphExtractor()


# ── V36-010: Prod Template Builder ──────────────────────────────────────────
class ProdTemplateBuilder:
    """Build a masked, PII-free test template from an entity graph snapshot."""

    def __init__(self, masking: MaskingService | None = None) -> None:
        self._masking = masking or masking_service

    def build(
        self,
        *,
        name: str,
        graph: dict[str, Any],
        masking_profile_id: int | None,
        rules: list[Any],
        project_id: int,
        mission_id: int | None,
        created_by: int,
    ) -> dict[str, Any]:
        masked_nodes = []
        for node in graph.get("nodes", []):
            payload = {
                "entity_type": node.get("entity_type"),
                "ref_hash": node.get("ref_hash"),
                "depth": node.get("depth", 0),
                "attributes": self._apply_to_strings(node.get("attributes") or {}, masking_profile_id, rules),
            }
            masked_nodes.append(payload)
        template = {"name": name, "nodes": masked_nodes, "edges": graph.get("edges", [])}
        return template

    def _apply_to_strings(self, attributes: dict[str, Any], masking_profile_id: int | None, rules: list[Any]) -> dict[str, Any]:
        result = self._masking.apply(
            profile_id=masking_profile_id or 0, rules=rules, record=attributes
        )
        # Safety net (V36-010): any field that is still equal to its original
        # value AND is PII-classified (not FREE_TEXT) is redacted, so the built
        # template never leaks raw PII even when no rule matched.
        for key, value in attributes.items():
            if str(result.get(key)) == str(value) and value != "":
                cls = self._masking._classifier.classify(key, str(value)) \
                    if hasattr(self._masking, "_classifier") else "FREE_TEXT"
                if cls != PiiClassification.FREE_TEXT.value:
                    result[key] = "<REDACTED>"
        return result


prod_template_builder = ProdTemplateBuilder()


# ── V36-011: Template Materializer ──────────────────────────────────────────
class TemplateMaterializer:
    """Write a validated template into a Test Environment fixture, remapping
    production IDs to deterministic test IDs (V36-011)."""

    def materialize(
        self,
        db: Session,
        *,
        template_id: int,
        target_environment_id: int,
        project_id: int,
    ) -> int:
        template_row = repo.get_prod_template(db, template_id)
        if template_row is None:
            raise APIException(code=404, msg="模板不存在", http_status=404)
        template = json.loads(template_row.template_json or "{}")
        node_rows = []
        id_remap: dict[str, str] = {}
        for node in template.get("nodes", []):
            remapped = _deterministic_token(node.get("ref_hash", ""), salt=f"mat-{template_id}")
            id_remap[node.get("ref_hash", "")] = remapped
            node_rows.append(
                {
                    "entity_type": node.get("entity_type", ""),
                    "logical_key": f"prod-template-{template_id}",
                    "physical_ref_json": _j(
                        {"template_node": node, "test_ref": remapped, "target_environment_id": target_environment_id}
                    ),
                    "created_by_fixture": True,
                }
            )
        fixture = data_repository.create_fixture(
            db,
            {
                "project_id": project_id,
                "scenario_version_id": 0,
                "data_plan_id": 0,
                "environment_id": target_environment_id,
                "strategy": "PROD_TEMPLATE",
                "status": "PROVISIONING",
                "namespace": f"prod-template-{template_id}",
                "manifest_json": _j(template),
            },
        )
        for row in node_rows:
            row["fixture_id"] = fixture.id
            data_repository.create_fixture_entity(db, row)
        fixture.status = "READY"
        db.commit()
        db.refresh(fixture)
        materialization = repo.create_materialization(
            db,
            {
                "template_id": template_id,
                "target_environment_id": target_environment_id,
                "fixture_id": fixture.id,
                "status": MaterializationStatus.READY.value,
                "id_remap_json": _j(id_remap),
            },
        )
        return materialization.id


template_materializer = TemplateMaterializer()


# ── V36-012: Evidence Gap Analysis ──────────────────────────────────────────
class ProductionEvidenceToDesignService:
    """Turn real paths / states into proposals. Proposals NEVER auto-approve a
    production behaviour as the new contract; they only surface candidates."""

    def analyze_gaps(
        self, *, journey: dict[str, Any], contract_refs: list[str] | None = None
    ) -> list[dict[str, Any]]:
        proposals: list[dict[str, Any]] = []
        events = journey.get("events", [])
        steps = []
        for ev in events:
            semantic = ev.get("semantic_action", {})
            steps.append(
                {
                    "kind": GapProposalKind.SOURCE_ARTIFACT.value,
                    "title": "real path observed",
                    "confidence": "high",
                    "evidence": ev.get("url", ""),
                    "auto_approved": False,
                }
            )
            semantic_name = semantic.get("name") or semantic.get("type") or ""
            if semantic_name and not any(semantic_name in c for c in contract_refs or []):
                proposals.append(
                    {
                        "kind": GapProposalKind.SCENARIO_GAP.value,
                        "title": f"semantic action not in contract refs: {semantic_name}",
                        "confidence": "medium",
                        "evidence": semantic_name,
                        "auto_approved": False,
                    }
                )
        if not proposals:
            proposals = [{"kind": GapProposalKind.SOURCE_ARTIFACT.value, "title": "no gap", "confidence": "low"}]
        return proposals


production_evidence_to_design_service = ProductionEvidenceToDesignService()
