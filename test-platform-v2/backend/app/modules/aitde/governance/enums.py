"""AITDE V4.0 Enterprise governance string enums (V40-009..020)."""

from __future__ import annotations

from enum import Enum


class SensitivityLevel(str, Enum):
    """Data or model-input sensitivity used for model routing (V40-014)."""

    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class RetentionAction(str, Enum):
    """Post-retention action for an artifact (V40-012)."""

    ARCHIVE = "ARCHIVE"
    DELETE = "DELETE"
    KEEP = "KEEP"


class ArtifactType(str, Enum):
    """Artifact kinds that retention policies can govern (V40-012)."""

    EVIDENCE = "EVIDENCE"
    REPLAY = "REPLAY"
    RUN = "RUN"
    DATASET = "DATASET"
    LOG = "LOG"


class DrTestType(str, Enum):
    """Disaster-recovery drill types (V40-017)."""

    BACKUP_RESTORE = "BACKUP_RESTORE"
    FAILOVER = "FAILOVER"
    OBJECT_STORE_RESTORE = "OBJECT_STORE_RESTORE"
    TEMPORAL_RECOVERY = "TEMPORAL_RECOVERY"


class DrTestStatus(str, Enum):
    PENDING = "PENDING"
    PASS = "PASS"
    FAIL = "FAIL"


class PolicyStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    ARCHIVED = "ARCHIVED"


class GovernanceExceptionStatus(str, Enum):
    OPEN = "OPEN"
    APPROVED = "APPROVED"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"


class ReadinessMetric(str, Enum):
    """Platform Readiness Gate metric keys (V40-018)."""

    P0_FALSE_PASS_RATE = "p0_false_pass_rate"
    FALSE_FAIL_RATE = "false_fail_rate"
    EVIDENCE_COMPLETENESS = "evidence_completeness"
    REPLAY_AUDIT_CONSISTENCY = "replay_audit_consistency"
    FIXTURE_CLEANUP_SUCCESS = "fixture_cleanup_success"
    PROD_UNAUTHORIZED_WRITE = "prod_unauthorized_write"
    SECRET_LEAKAGE = "secret_leakage"
    PII_LEAKAGE = "pii_leakage"
    CONTRACT_UNAUTHORIZED_MUTATION = "contract_unauthorized_mutation"
    MISSION_WORKFLOW_ADOPTION = "mission_workflow_adoption"
