"""Keep Alembic revision identifiers compatible with the version table width."""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

# The V3.9 revision ids are 37-41 chars; the R2 reality-gate migration widens
# ``alembic_version.version_num`` to VARCHAR(128) (default Alembic is 32), so any
# future revision id must stay within 128 chars.
MAX_REVISION_ID_LEN = 128


def test_all_revision_ids_fit_version_table_column() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    revisions = ScriptDirectory.from_config(config).walk_revisions()

    oversized = [
        revision.revision
        for revision in revisions
        if len(revision.revision) > MAX_REVISION_ID_LEN
    ]

    assert oversized == [], f"Alembic revision IDs exceed {MAX_REVISION_ID_LEN} characters: {oversized}"
