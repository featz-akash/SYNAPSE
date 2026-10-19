"""Pydantic schemas for the Objectives API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from synapse.domain.state import TaskState


class ObjectiveCreateRequest(BaseModel):
    """Request body for creating an objective."""

    title: str = Field(min_length=1, max_length=500)
    success_criteria: list[str] = Field(min_length=1)
    description: str = Field(default="", max_length=10000)


class ObjectiveResponse(BaseModel):
    """Public representation of an objective."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str
    success_criteria: list[str]
    created_at: datetime
    revision: int

class TaskCreateRequest(BaseModel):
    """Request body for creating a task."""

    title: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=10000)
    dependencies: list[str] = Field(default_factory=list)


class TaskResponse(BaseModel):
    """Public representation of a task."""

    id: str
    objective_id: str
    title: str
    description: str
    dependencies: list[str]
    created_at: datetime
    revision: int


class TaskStateTransitionRequest(BaseModel):
    """Request body for transitioning a task to another state."""

    target_state: TaskState
    expected_revision: int = Field(ge=0, strict=True)
