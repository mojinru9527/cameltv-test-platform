"""AIQE 版本化协议对象（Pydantic）。

所有跨进程/跨表 JSON 必须带 `schema_version`，并在这里做一次校验，
避免 Driver / Runner / API 各自解释字段。
"""
from app.aiqe.schemas.contracts import (  # noqa: F401
    ASSERTION_SCHEMA_VERSION,
    DRIVER_RESULT_SCHEMA_VERSION,
    RESOLVED_INPUT_SCHEMA_VERSION,
    AssertionOutcome,
    AssertionSpec,
    DriverResult,
    EvidenceFile,
    PreflightIssue,
    PreflightReport,
    ResolvedInput,
    SourceRef,
)
