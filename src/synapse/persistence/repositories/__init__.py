"""Repository operations for SYNAPSE persistence."""

from synapse.persistence.repositories.dependencies import replace_task_dependencies
from synapse.persistence.repositories.objectives import (
    create_objective,
    get_objective,
)

__all__ = [
    "create_objective",
    "get_objective",
    "replace_task_dependencies",
]
