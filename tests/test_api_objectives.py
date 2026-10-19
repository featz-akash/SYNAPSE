"""Tests for the SYNAPSE Objectives API."""

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
    database_path = tmp_path / "api-test.db"
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


def test_create_objective(client: TestClient) -> None:
    response = client.post(
        "/objectives",
        json={
            "title": "Build SYNAPSE",
            "description": "Develop the reasoning engine.",
            "success_criteria": [
                "Validate reasoning outputs",
                "Preserve auditability",
            ],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Build SYNAPSE"
    assert body["description"] == "Develop the reasoning engine."
    assert body["success_criteria"] == [
        "Validate reasoning outputs",
        "Preserve auditability",
    ]
    assert body["id"]
    assert body["revision"] == 1


def test_get_existing_objective(client: TestClient) -> None:
    created = client.post(
        "/objectives",
        json={
            "title": "Test objective",
            "success_criteria": ["Pass the tests"],
        },
    )
    objective_id = created.json()["id"]

    response = client.get(f"/objectives/{objective_id}")

    assert response.status_code == 200
    assert response.json()["id"] == objective_id
    assert response.json()["title"] == "Test objective"


def test_get_missing_objective_returns_404(client: TestClient) -> None:
    response = client.get("/objectives/nonexistent-objective")

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["code"] == "resource_not_found"
    assert detail["message"] == "Objective not found."
    assert detail["details"]["objective_id"] == "nonexistent-objective"


def test_create_objective_rejects_missing_success_criteria(
    client: TestClient,
) -> None:
    response = client.post(
        "/objectives",
        json={"title": "Incomplete objective"},
    )

    assert response.status_code == 422


def test_create_objective_rejects_blank_title(
    client: TestClient,
) -> None:
    response = client.post(
        "/objectives",
        json={
            "title": "",
            "success_criteria": ["Pass the tests"],
        },
    )

    assert response.status_code == 422


def test_get_existing_task(client: TestClient) -> None:
    objective = client.post(
        "/objectives",
        json={
            "title": "Task API objective",
            "success_criteria": ["Retrieve tasks"],
        },
    )
    assert objective.status_code == 201
    objective_id = objective.json()["id"]

    created = client.post(
        f"/objectives/{objective_id}/tasks",
        json={
            "title": "Implement retrieval",
            "description": "Add a GET endpoint.",
        },
    )
    assert created.status_code == 201
    task_id = created.json()["id"]

    response = client.get(f"/tasks/{task_id}")

    assert response.status_code == 200
    assert response.json()["id"] == task_id
    assert response.json()["objective_id"] == objective_id
    assert response.json()["title"] == "Implement retrieval"


def test_get_missing_task_returns_404(client: TestClient) -> None:
    response = client.get("/tasks/nonexistent-task")

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["code"] == "resource_not_found"
    assert detail["message"] == "Task not found."
    assert detail["details"]["task_id"] == "nonexistent-task"


def test_create_objective_rejects_whitespace_only_title(
    client: TestClient,
) -> None:
    response = client.post(
        "/objectives",
        json={
            "title": "   ",
            "success_criteria": ["Pass the tests"],
        },
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "validation_error"


def test_create_objective_rejects_blank_success_criteria_item(
    client: TestClient,
) -> None:
    response = client.post(
        "/objectives",
        json={
            "title": "Valid objective",
            "success_criteria": ["   "],
        },
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "validation_error"
