"""M1-B contract regression: every canonical state pair, independently specified."""

import pytest

from synapse.domain.contracts import Objective, Task
from synapse.domain.errors import InvalidTransitionError, StaleRevisionError
from synapse.domain.state import ObjectiveState, ObjectiveStateMachine, TaskState, TaskStateMachine

# Independently maintained acceptance matrix: do not import private transition tables.
OBJECTIVE_EDGES = {
    'draft': 'needs_input ready cancelled',
    'needs_input': 'draft ready cancelled',
    'ready': 'running paused cancelled',
    'running': 'needs_input awaiting_approval paused blocked completed failed cancelled',
    'awaiting_approval': 'running blocked paused cancelled',
    'paused': 'ready running blocked cancelled',
    'blocked': 'ready running awaiting_approval failed cancelled',
    'completed': '', 'failed': '', 'cancelled': '',
}
TASK_EDGES = {
    'proposed': 'ready blocked cancelled',
    'ready': 'awaiting_approval running blocked cancelled',
    'awaiting_approval': 'ready running blocked cancelled',
    'running': 'verifying reconciling failed blocked cancelled',
    'verifying': 'succeeded failed reconciling blocked',
    'reconciling': 'verifying ready blocked failed cancelled',
    'succeeded': '', 'failed': '',
    'blocked': 'ready awaiting_approval failed cancelled',
    'cancelled': '',
}


def _objective():
    return Objective(title='Check', success_criteria=('Verified',))


def _task():
    return Task(objective_id=_objective().id, title='Inspect')


@pytest.mark.parametrize('source', list(ObjectiveState))
@pytest.mark.parametrize('target', list(ObjectiveState))
def test_objective_full_transition_matrix(source, target):
    entity = _objective()
    allowed = target.value in OBJECTIVE_EDGES[source.value].split()
    if allowed:
        result = ObjectiveStateMachine.transition(
            entity, source, target, expected_revision=0,
            all_tasks_succeeded=True, success_criteria_verified=True,
        )
        assert result is target
        assert entity.revision == 1
    else:
        with pytest.raises(InvalidTransitionError):
            ObjectiveStateMachine.transition(
                entity, source, target, expected_revision=0,
                all_tasks_succeeded=True, success_criteria_verified=True,
            )
        assert entity.revision == 0


@pytest.mark.parametrize('source', list(TaskState))
@pytest.mark.parametrize('target', list(TaskState))
def test_task_full_transition_matrix(source, target):
    entity = _task()
    allowed = target.value in TASK_EDGES[source.value].split()
    if allowed:
        assert TaskStateMachine.transition(entity, source, target, expected_revision=0) is target
        assert entity.revision == 1
    else:
        with pytest.raises(InvalidTransitionError):
            TaskStateMachine.transition(entity, source, target, expected_revision=0)
        assert entity.revision == 0


@pytest.mark.parametrize('kind', ['objective', 'task'])
def test_stale_revision_never_mutates(kind):
    if kind == 'objective':
        entity = _objective()
        with pytest.raises(StaleRevisionError):
            ObjectiveStateMachine.transition(
                entity, ObjectiveState.DRAFT, ObjectiveState.READY, expected_revision=1,
            )
    else:
        entity = _task()
        with pytest.raises(StaleRevisionError):
            TaskStateMachine.transition(
                entity, TaskState.PROPOSED, TaskState.READY, expected_revision=1,
            )
    assert entity.revision == 0
