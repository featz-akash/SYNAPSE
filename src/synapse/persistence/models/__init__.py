
"""ORM model registry for SYNAPSE persistence."""

from synapse.persistence.models.base import Base
from synapse.persistence.models.objective import ObjectiveRecord
from synapse.persistence.models.task import TaskRecord, task_dependencies
from synapse.persistence.models.audit import AuditRecord
from synapse.persistence.models.audit_head import AuditChainHead
from synapse.persistence.models.execution_claim import ExecutionClaim

__all__ = [
    "Base",
    "ObjectiveRecord",
    "TaskRecord",
    "task_dependencies",
    "AuditRecord",
    "ExecutionClaim",
    "AuditChainHead",
]
