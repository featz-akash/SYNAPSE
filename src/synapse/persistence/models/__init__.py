"""ORM model registry for SYNAPSE persistence."""

from synapse.persistence.models.base import Base

__all__ = ["Base"]

from synapse.persistence.models.objective import ObjectiveRecord
from synapse.persistence.models.task import TaskRecord, task_dependencies

__all__ = ["Base", "ObjectiveRecord", "TaskRecord", "task_dependencies"]
