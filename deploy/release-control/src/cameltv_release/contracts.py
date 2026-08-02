"""Immutable, dependency-light contracts for the release-control core."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_SECRET_REF_PATTERN = re.compile(r"^secret://(?P<environment>[a-z][a-z0-9-]*)/[a-z0-9][a-z0-9/_-]*@v[1-9][0-9]*$")
_FORBIDDEN_SECRET_KEY_PARTS = ("password", "token", "private_key", "database_url", "secret_key")


class Artifact(BaseModel):
    """Immutable application artifact bound by digest and SBOM checksum."""

    model_config = ConfigDict(extra="forbid")

    image: str = Field(min_length=1)
    digest: str
    sbom_sha256: str

    @field_validator("digest")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if not _DIGEST_PATTERN.fullmatch(value):
            raise ValueError("must be an immutable sha256 digest")
        return value

    @field_validator("sbom_sha256")
    @classmethod
    def validate_sbom_sha256(cls, value: str) -> str:
        if not _SHA256_PATTERN.fullmatch(value):
            raise ValueError("must be a lowercase SHA-256 checksum")
        return value


class BackendArtifact(Artifact):
    """Backend artifact evidence extends the shared artifact contract."""

    openapi_sha256: str

    @field_validator("openapi_sha256")
    @classmethod
    def validate_openapi_sha256(cls, value: str) -> str:
        if not _SHA256_PATTERN.fullmatch(value):
            raise ValueError("must be a lowercase SHA-256 checksum")
        return value


class DatabaseTarget(BaseModel):
    """Database revision target for one immutable release."""

    model_config = ConfigDict(extra="forbid")

    alembic_heads: list[str] = Field(min_length=1, max_length=1)
    target_revision: str = Field(min_length=1)
    rollback_mode: str = Field(pattern=r"^application-rollback-or-forward-fix$")

    @model_validator(mode="after")
    def validate_unique_target_head(self) -> "DatabaseTarget":
        if self.alembic_heads[0] != self.target_revision:
            raise ValueError("target_revision must equal the only alembic head")
        return self


class ReleaseManifest(BaseModel):
    """Validated immutable release unit; it deliberately contains no secret values."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(pattern=r"^1\.0$")
    release_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,127}$")
    git_sha: str
    frontend: Artifact
    backend: BackendArtifact
    database: DatabaseTarget
    config_schema: str = Field(min_length=1)
    secret_refs: list[str] = Field(min_length=1)
    qa_evidence: list[str] = Field(min_length=1)

    @field_validator("git_sha")
    @classmethod
    def validate_git_sha(cls, value: str) -> str:
        if not _GIT_SHA_PATTERN.fullmatch(value):
            raise ValueError("must be a 40-character lowercase Git SHA")
        return value

    @field_validator("secret_refs")
    @classmethod
    def validate_secret_refs(cls, values: list[str], info: ValidationInfo) -> list[str]:
        environment = info.context.get("environment") if info.context else "test"
        for value in values:
            match = _SECRET_REF_PATTERN.fullmatch(value)
            if not match:
                raise ValueError("must use secret://<environment>/<name>@v<version>")
            if match.group("environment") != environment:
                raise ValueError("must target the requested environment")
        return values

    @field_validator("qa_evidence")
    @classmethod
    def validate_qa_evidence(cls, values: list[str]) -> list[str]:
        if not all(value.startswith("artifact://") for value in values):
            raise ValueError("must contain artifact references")
        return values

    def canonical_json(self) -> bytes:
        """Return canonical bytes used to identify this immutable manifest."""
        payload: dict[str, Any] = self.model_dump(mode="json")
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")

    def manifest_sha256(self) -> str:
        """Return SHA-256 of canonical manifest bytes."""
        return hashlib.sha256(self.canonical_json()).hexdigest()
