"""Abstract base class for external sync providers (Jira, TAPD, etc.)."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod

import httpx


class BaseSyncProvider(ABC):
    """Interface contract for external system sync providers."""

    # ── Default field mappings (overridden by config field_mapping JSON) ──

    DEFAULT_SEVERITY_MAP: dict[str, str] = {}
    DEFAULT_SEVERITY_REVERSE: dict[str, str] = {}
    DEFAULT_STATUS_MAP: dict[str, str] = {}
    DEFAULT_STATUS_REVERSE: dict[str, str] = {}

    def __init__(self, config: dict):
        self.base_url = config["base_url"].rstrip("/")
        self.auth = config["auth"]  # already-decrypted dict
        self.field_mapping = json.loads(config.get("field_mapping", "{}")) if isinstance(config.get("field_mapping"), str) else (config.get("field_mapping") or {})

    # ── Abstract interface ──

    @abstractmethod
    async def test_connection(self) -> tuple[bool, str]:
        """Verify credentials and connectivity. Returns (success, message)."""

    @abstractmethod
    async def push_defect(self, defect: dict) -> tuple[bool, str, str]:
        """Create/update issue in external system.
        Returns (success, external_id, external_url).
        """

    @abstractmethod
    async def pull_defect(self, external_id: str) -> tuple[bool, dict | None, str]:
        """Fetch issue from external system.
        Returns (success, defect_data_dict, error_message).
        """

    @abstractmethod
    async def sync_status(self, external_id: str, new_status: str) -> tuple[bool, str]:
        """Update only the status of an existing external issue.
        Returns (success, message).
        """

    # ── Shared HTTP helpers ──

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Wrapper with timeout and retry (mirrors notify_service pattern)."""
        url = f"{self.base_url}{path}" if not path.startswith("http") else path
        timeout = kwargs.pop("timeout", 30.0)
        last_error = ""
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.request(method, url, **kwargs)
                    resp.raise_for_status()
                    return resp
            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}: {e.response.text[:500]}"
            except Exception as e:
                last_error = str(e)
            if attempt < 2:
                import asyncio
                await asyncio.sleep(1 + attempt)  # 1s, 2s backoff
        raise RuntimeError(last_error)

    # ── Mapping helpers (use custom mapping from field_mapping, fallback to defaults) ──

    def map_severity_to_external(self, severity: str) -> str:
        custom = self.field_mapping.get("severity", {})
        return custom.get(severity, self.DEFAULT_SEVERITY_MAP.get(severity, severity))

    def map_severity_from_external(self, external_severity: str) -> str:
        custom_rev = self.field_mapping.get("severity_reverse", {})
        return custom_rev.get(external_severity, self.DEFAULT_SEVERITY_REVERSE.get(external_severity, "P2"))

    def map_status_to_external(self, status: str) -> str:
        custom = self.field_mapping.get("status", {})
        return custom.get(status, self.DEFAULT_STATUS_MAP.get(status, status))

    def map_status_from_external(self, external_status: str) -> str:
        custom_rev = self.field_mapping.get("status_reverse", {})
        return custom_rev.get(external_status, self.DEFAULT_STATUS_REVERSE.get(external_status, "open"))
