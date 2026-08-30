"""AITDE V3.4 Temporal workflow + activities package (V34).

Temporal runs workflow definitions inside a restricted sandbox that re-imports
the module. This package lives under ``app/`` (whose ``__init__`` is empty) so
the workflow module's import chain never pulls ``app.core.db`` / ``pathlib`` —
keeping the workflow deterministic and sandbox-clean. Activities are NOT
sandboxed, so they may import the wider app as the version grows.
"""
