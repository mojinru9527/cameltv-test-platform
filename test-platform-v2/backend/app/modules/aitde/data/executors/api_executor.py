"""AITDE V3.9-R2 (DATA-002) — ApiFixtureExecutor: real HTTP POST + VERIFY.

Creates a test entity through the DataSource's REST create endpoint, then
*verifies* the created resource physically exists via GET before it may count as
a physical effect. A 200/201 from create with no real resource behind it is
treated as a failure (``VERIFY_MISMATCH``) — never READY.
"""
from __future__ import annotations

import re
from typing import Any

from app.modules.aitde.drivers.http.data_api_driver import DataApiError

# A safe id-path segment: bare word, optionally dotted (e.g. "id", "record.id").
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$")
_ID_TEMPLATE_RE = re.compile(r"\{id\}")


def _dig(node: Any, path: str) -> Any:
    """Navigate a nested dict by dotted path; return None if any hop missing."""
    current = node
    for seg in path.split("."):
        if not isinstance(current, dict) or seg not in current:
            return None
        current = current[seg]
    return current


class ApiFixtureExecutor:
    """Execute an API_BUILDER ``CREATE`` against a REST test endpoint."""

    @staticmethod
    def execute_create(
        driver: Any,
        endpoint: str,
        payload: dict[str, Any],
        *,
        get_endpoint: str | None = None,
        id_field: str = "id",
    ) -> dict[str, Any]:
        """POST the payload, extract the physical id, then GET VERIFY.

        ``get_endpoint`` may use an ``{id}`` template (e.g. ``"/memberships/{id}"``);
        when omitted the create endpoint + ``/`` + id is used.
        Raises ``DataApiError`` when the create is rejected, the id is missing
        from the response, or the created resource cannot be verified present.
        """
        if not endpoint or not isinstance(endpoint, str):
            raise DataApiError("NO_ENDPOINT", "create endpoint missing")
        if not isinstance(payload, dict) or not payload:
            raise DataApiError("EMPTY_PAYLOAD", "no create payload")
        if not _IDENT_RE.match(str(id_field)):
            raise DataApiError("UNSAFE_ID_FIELD", str(id_field))

        # CREATE — driver raises CREATE_REJECTED on 4xx/5xx.
        status, data = driver.post(endpoint, payload)
        resource_id = _dig(data, id_field)
        if resource_id is None:
            raise DataApiError(
                "NO_ID", f"create response missing id field '{id_field}'"
            )

        # VERIFY the created resource physically exists.
        if get_endpoint and _ID_TEMPLATE_RE.search(str(get_endpoint)):
            verify_path = _ID_TEMPLATE_RE.sub(str(resource_id), str(get_endpoint))
        elif get_endpoint:
            verify_path = f"{str(get_endpoint).rstrip('/')}/{resource_id}"
        else:
            verify_path = f"{endpoint.rstrip('/')}/{resource_id}"

        vstatus, vdata = driver.get(verify_path)
        verified_id = _dig(vdata, id_field)
        if verified_id is None or str(verified_id) != str(resource_id):
            raise DataApiError(
                "VERIFY_MISMATCH", "created resource not present on verify"
            )
        return {
            "created": True,
            "physical_id": resource_id,
            "resource": vdata,
            "verify_status": int(vstatus),
        }
