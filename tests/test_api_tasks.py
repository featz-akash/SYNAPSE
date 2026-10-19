
"""Tests for the SYNAPSE Tasks API."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from synapse.api.app import create_app
from synapse.persistence.models import Base
from synapse.persistence.unit_of_work import SqlAlchemyUnitOfWork


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    """Create an isolated API backed by a temporary SQLite database."""
    database_path = tmp_path / "tasks-api-test.db"
    engine = create_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(engine)

    session_factory: sessionmaker[Session] = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    def uow_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    app = create_app(
    uow_factory=uow_factory,
    api_token="test-only-token",
    api_permissions=frozenset(
        {
            "objectives:read",
            "objectives:write",
            "tasks:read",
            "tasks:write",
        }
    ),
)

    with TestClient(app) as test_client:
        test_client.headers["Authorization"] = "Bearer test-only-token"
        yield test_client

    engine.dispose()


def create_task(client: TestClient) -> str:
    """Create an objective and task, returning the task ID."""
    objective_response = client.post(
        "/objectives",
        json={
            "title": "Task state API objective",
            "success_criteria": ["Verify state transitions"],
        },
    )
    assert objective_response.status_code == 201
    objective_id = objective_response.json()["id"]

    task_response = client.post(
        f"/objectives/{objective_id}/tasks",
        json={"title": "Transition test task"},
    )
    assert task_response.status_code == 201
    return task_response.json()["id"]


def test_transition_task_to_ready(client: TestClient) -> None:
    task_id = create_task(client)

    response = client.patch(
        f"/tasks/{task_id}/state",
        json={"target_state": "ready", "expected_revision": 1},
    )

    assert response.status_code == 200
    assert response.json()["id"] == task_id
    assert response.json()["revision"] == 2


def test_transition_task_rejects_stale_revision(
    client: TestClient,
) -> None:
    task_id = create_task(client)

    response = client.patch(
        f"/tasks/{task_id}/state",
        json={"target_state": "ready", "expected_revision": 0},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "stale_revision"


def test_transition_task_rejects_invalid_transition(
    client: TestClient,
) -> None:
    task_id = create_task(client)

    response = client.patch(
        f"/tasks/{task_id}/state",
        json={"target_state": "succeeded", "expected_revision": 1},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "invalid_state_transition"


def test_transition_task_rejects_invalid_state_value(
    client: TestClient,
) -> None:
    task_id = create_task(client)

    response = client.patch(
        f"/tasks/{task_id}/state",
        json={"target_state": "unknown", "expected_revision": 1},
    )

    assert response.status_code == 422

def test_transition_missing_task_returns_404(
    client: TestClient,
) -> None:
    response = client.patch(
        "/tasks/nonexistent-task/state",
        json={
            "target_state": "ready",
            "expected_revision": 0,
        },
    )

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["code"] == "resource_not_found"
    assert detail["message"] == "Task not found."
    assert detail["details"]["task_id"] == "nonexistent-task"


def test_create_task_rejects_whitespace_only_title(
    client: TestClient,
) -> None:
    objective_response = client.post(
        "/objectives",
        json={
            "title": "Task validation objective",
            "success_criteria": ["Validate task creation"],
        },
    )
    assert objective_response.status_code == 201
    objective_id = objective_response.json()["id"]

    response = client.post(
        f"/objectives/{objective_id}/tasks",
        json={"title": "   "},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "validation_error"


def test_create_task_under_missing_objective_returns_404(
    client: TestClient,
) -> None:
    response = client.post(
        "/objectives/nonexistent-objective/tasks",
        json={"title": "A task"},
    )

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["code"] == "resource_not_found"


def test_create_task_rejects_blank_dependency_identifier(
    client: TestClient,
) -> None:
    objective_response = client.post(
        "/objectives",
        json={
            "title": "Dependency validation objective",
            "success_criteria": ["Validate dependencies"],
        },
    )
    assert objective_response.status_code == 201
    objective_id = objective_response.json()["id"]

    response = client.post(
        f"/objectives/{objective_id}/tasks",
        json={
            "title": "Task with invalid dependency",
            "dependencies": ["   "],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "validation_error"


def test_create_task_rejects_duplicate_dependencies(
    client: TestClient,
) -> None:
    objective_response = client.post(
        "/objectives",
        json={
            "title": "Duplicate dependency objective",
            "success_criteria": ["Validate duplicate dependencies"],
        },
    )
    assert objective_response.status_code == 201
    objective_id = objective_response.json()["id"]

    dependency_response = client.post(
        f"/objectives/{objective_id}/tasks",
        json={"title": "Dependency task"},
    )
    assert dependency_response.status_code == 201
    dependency_id = dependency_response.json()["id"]

    response = client.post(
        f"/objectives/{objective_id}/tasks",
        json={
            "title": "Task with duplicate dependencies",
            "dependencies": [dependency_id, dependency_id],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "validation_error"


def test_transition_task_rejects_boolean_revision(
    client: TestClient,
) -> None:
    task_id = create_task(client)

    response = client.patch(
        f"/tasks/{task_id}/state",
        json={"target_state": "ready", "expected_revision": True},
    )

    assert response.status_code == 422


def test_read_only_client_cannot_transition_task_state(
    client: TestClient,
) -> None:
    """A denied state transition must leave the task unchanged."""
    from synapse.api.app import create_app

    task_id = create_task(client)

    # Capture the task before the unauthorized request.
    before = client.get(f"/tasks/{task_id}")
    assert before.status_code == 200
    original_task = before.json()

    # This principal can read tasks but cannot change their state.
    read_only_app = create_app(
        uow_factory=client.app.state.uow_factory,
        api_token="read-only-token",
        api_permissions=frozenset({"tasks:read"}),
    )

    with TestClient(read_only_app) as read_only_client:
        denied = read_only_client.patch(
            f"/tasks/{task_id}/state",
            json={
                "target_state": "ready",
                "expected_revision": original_task["revision"],
            },
            headers={"Authorization": "Bearer read-only-token"},
        )

    assert denied.status_code == 403

    # Verify the task remains unchanged using the authorized client.
    after = client.get(f"/tasks/{task_id}")
    assert after.status_code == 200
    updated_task = after.json()

    assert updated_task["revision"] == original_task["revision"]
    assert updated_task == original_task
