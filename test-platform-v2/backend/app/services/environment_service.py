"""环境与变量 Service — CRUD + 变量引用解析。"""
from __future__ import annotations

import re
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.environment import Environment, EnvironmentVariable
from app.core.cipher import encrypt_value, decrypt_value

_VAR_PATTERN = re.compile(r"\$\{(\w+)\}")


# ── Environment CRUD ──

def list_environments(db: Session, project_id: int) -> list[dict]:
    rows = db.scalars(
        select(Environment)
        .where(Environment.project_id == project_id)
        .order_by(Environment.id)
    ).all()
    return [_env_to_dict(r) for r in rows]


def get_environment(db: Session, env_id: int, project_id: int) -> dict | None:
    row = db.scalar(
        select(Environment).where(
            Environment.id == env_id, Environment.project_id == project_id
        )
    )
    return _env_to_dict(row) if row else None


def create_environment(db: Session, project_id: int, data: dict) -> dict:
    row = Environment(project_id=project_id, **data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _env_to_dict(row)


def update_environment(db: Session, env_id: int, data: dict) -> dict | None:
    row = db.get(Environment, env_id)
    if not row:
        return None
    for k, v in data.items():
        if v is not None:
            setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return _env_to_dict(row)


def delete_environment(db: Session, env_id: int) -> bool:
    row = db.get(Environment, env_id)
    if not row:
        return False
    # Cascade delete variables
    vars_ = db.scalars(
        select(EnvironmentVariable).where(EnvironmentVariable.environment_id == env_id)
    ).all()
    for v in vars_:
        db.delete(v)
    db.delete(row)
    db.commit()
    return True


# ── Variable CRUD ──

def list_variables(db: Session, environment_id: int) -> list[dict]:
    rows = db.scalars(
        select(EnvironmentVariable)
        .where(EnvironmentVariable.environment_id == environment_id)
        .order_by(EnvironmentVariable.key)
    ).all()
    return [_var_to_dict(r, mask_sensitive=False) for r in rows]


def create_variable(db: Session, environment_id: int, data: dict) -> dict:
    """Create a variable, encrypting the value if encrypted=True."""
    encrypted = data.get("encrypted", False)
    value = data.get("value", "")
    if encrypted and value:
        data["value"] = encrypt_value(value)
    row = EnvironmentVariable(environment_id=environment_id, **data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _var_to_dict(row, mask_sensitive=True)


def update_variable(db: Session, var_id: int, data: dict) -> dict | None:
    row = db.get(EnvironmentVariable, var_id)
    if not row:
        return None
    encrypted = data.get("encrypted", row.encrypted)
    if "value" in data and data["value"] is not None:
        if encrypted:
            data["value"] = encrypt_value(data["value"])
        row.value = data["value"]
    for k, v in data.items():
        if v is not None and k not in ("value",):
            setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return _var_to_dict(row, mask_sensitive=True)


def delete_variable(db: Session, var_id: int) -> bool:
    row = db.get(EnvironmentVariable, var_id)
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ── Variable Resolution ──

def resolve_variables(db: Session, environment_id: int, template: str) -> str:
    """Replace ${VAR_NAME} in template with variable values from the given environment."""
    vars_ = db.scalars(
        select(EnvironmentVariable).where(
            EnvironmentVariable.environment_id == environment_id
        )
    ).all()
    var_map: dict[str, str] = {}
    for v in vars_:
        val = v.value
        if v.encrypted and val:
            try:
                val = decrypt_value(val)
            except Exception:
                pass  # keep ciphertext if decryption fails
        var_map[v.key] = val

    def _replacer(m: re.Match) -> str:
        return var_map.get(m.group(1), m.group(0))

    return _VAR_PATTERN.sub(_replacer, template)


# ── Helper ──

def _env_to_dict(r: Environment) -> dict:
    return {
        "id": r.id,
        "project_id": r.project_id,
        "name": r.name,
        "env_type": r.env_type,
        "base_url": r.base_url,
        "description": r.description,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


def _var_to_dict(r: EnvironmentVariable, mask_sensitive: bool = False) -> dict:
    val = r.value
    if r.encrypted and mask_sensitive:
        val = "••••••••"
    return {
        "id": r.id,
        "environment_id": r.environment_id,
        "key": r.key,
        "value": val,
        "encrypted": r.encrypted,
        "description": r.description,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }
