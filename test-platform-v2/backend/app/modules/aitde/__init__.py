"""AITDE V3 modular monolith package (V30-003).

Bounded-context blueprint for the Mission runtime. Kept as a package skeleton in
EPIC-00; each domain gets its model/service/API inside its own bounded submodule
(mission -> source -> scope -> contract -> scenario -> ...) to avoid the legacy
flat ``app/models`` / ``app/services`` pile-up.
"""

# Importing the package registers AITDE domain models on ``Base.metadata`` so
# Alembic and ``create_all`` can discover them (V30-003 DoD).
from app.modules.aitde.mission import models  # noqa: F401
from app.modules.aitde.sources import models as sources_models  # noqa: F401
from app.modules.aitde.scope import models as scope_models  # noqa: F401
from app.modules.aitde.contract import models as contract_models  # noqa: F401
from app.modules.aitde.scenario import models as scenario_models  # noqa: F401
