"""AITDE V3.9-R2 (DATA-002) HTTP data-API driver package.

Drivers here turn a DataSource ``config`` + ``secret_ref`` into real, typed calls
to a test-environment REST API for the API_BUILDER strategy. They never embed a
literal secret in code or config — only the ``secret_ref`` (reference) is carried
and applied to the ``Authorization`` header at transport time.
"""
from __future__ import annotations

from app.modules.aitde.drivers.http.data_api_driver import (
    DataApiDriver,
    DataApiError,
)

__all__ = ["DataApiDriver", "DataApiError"]
