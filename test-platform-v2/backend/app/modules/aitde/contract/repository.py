"""Contract repository (V30-050..V30-053).

Enforces the FROZEN immutability rule at both repository and service layers:
once a version is FROZEN it cannot be updated or deleted.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import APIException
from app.modules.aitde.common.enums import ContractVersionStatus
from app.modules.aitde.contract.models import (
    ChangeProposal,
    TestContract,
    TestContractVersion,
)


def snapshot_hash(snapshot: dict) -> str:
    return hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:32]


def get_identity(db: Session, mission_id: int) -> TestContract | None:
    return db.scalar(select(TestContract).where(TestContract.mission_id == mission_id))


def get_or_create_identity(
    db: Session, mission_id: int, created_by: int
) -> TestContract:
    contract = get_identity(db, mission_id)
    if contract:
        return contract
    contract = TestContract(
        mission_id=mission_id, name="Test Contract", created_by=created_by
    )
    db.add(contract)
    db.flush()
    return contract


def create_version(
    db: Session,
    contract_id: int,
    version_no: int,
    snapshot: dict,
    created_by: int,
    created_by_type: str = "AI",
) -> TestContractVersion:
    version = TestContractVersion(
        contract_id=contract_id,
        version_no=version_no,
        status=ContractVersionStatus.DRAFT.value,
        content_hash=snapshot_hash(snapshot),
        snapshot_json=json.dumps(snapshot, ensure_ascii=False),
        created_by=created_by,
        created_by_type=created_by_type,
    )
    db.add(version)
    db.flush()
    return version


def list_versions(db: Session, contract_id: int) -> list[TestContractVersion]:
    rows = db.scalars(
        select(TestContractVersion)
        .where(TestContractVersion.contract_id == contract_id)
        .order_by(TestContractVersion.version_no.asc())
    ).all()
    return list(rows)


def get_version(
    db: Session, contract_id: int, version_no: int
) -> TestContractVersion | None:
    return db.scalar(
        select(TestContractVersion).where(
            TestContractVersion.contract_id == contract_id,
            TestContractVersion.version_no == version_no,
        )
    )


def get_version_by_id(db: Session, version_id: int) -> TestContractVersion | None:
    return db.get(TestContractVersion, version_id)


def latest_version(db: Session, contract_id: int) -> TestContractVersion | None:
    return db.scalar(
        select(TestContractVersion)
        .where(TestContractVersion.contract_id == contract_id)
        .order_by(TestContractVersion.version_no.desc())
        .limit(1)
    )


def freeze_version(
    db: Session, version: TestContractVersion, user_id: int
) -> TestContractVersion:
    if version.status == ContractVersionStatus.FROZEN.value:
        raise APIException(
            code=409, msg="契约版本已冻结，不可重复冻结", http_status=409
        )
    if version.status not in (
        ContractVersionStatus.DRAFT.value,
        ContractVersionStatus.REVIEWING.value,
    ):
        raise APIException(
            code=409, msg=f"契约版本当前状态不可冻结：{version.status}", http_status=409
        )
    version.status = ContractVersionStatus.FROZEN.value
    version.approved_by = user_id
    version.approved_at = datetime.now()
    db.commit()
    db.refresh(version)
    return version


def ensure_mutable(version: TestContractVersion) -> None:
    if version.status == ContractVersionStatus.FROZEN.value:
        raise APIException(
            code=409, msg="Frozen contract cannot be mutated.", http_status=409
        )


def create_change_proposal(
    db: Session,
    mission_id: int,
    data: dict,
    actor: str,
    user_id: int,
) -> ChangeProposal:
    proposal = ChangeProposal(
        mission_id=mission_id,
        target_type=data.get("target_type", "CONTRACT"),
        target_id=data.get("target_id", 0),
        target_version=data.get("target_version", 0),
        proposal_type=data.get("proposal_type", "modify"),
        reason=data.get("reason", ""),
        diff_json=json.dumps(data.get("diff") or {}, ensure_ascii=False),
        source_refs_json=json.dumps(data.get("source_refs") or [], ensure_ascii=False),
        created_by_type=actor,
        created_by=user_id,
    )
    db.add(proposal)
    db.flush()
    return proposal
