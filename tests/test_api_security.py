
"""Security tests for the SYNAPSE API."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from synapse.api.app import create_app


def unused_uow_factory():
    """Fail if a rejected request reaches persistence."""
    raise AssertionError("Rejected requests must not access persistence.")


@pytest.fixture
def configured_app():
    """Create an API with a token and no granted permissions."""
    return create_app(
        uow_factory=unused_uow_factory,
        api_token="test-only-token",
        api_permissions=frozenset(),
    )


@pytest.fixture
def client(configured_app) -> Iterator[TestClient]:
    """Create a test client without default authentication headers."""
    with TestClient(configured_app) as test_client:
        yield test_client


def test_missing_token_returns_401(client: TestClient) -> None:
    response = client.post(
        "/objectives",
        json={
            "title": "Unauthorized objective",
            "success_criteria": ["Must not be created"],
        },
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_invalid_token_returns_401(client: TestClient) -> None:
    response = client.post(
        "/objectives",
        headers={"Authorization": "Bearer invalid-token"},
        json={
            "title": "Unauthorized objective",
            "success_criteria": ["Must not be created"],
        },
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_missing_permission_returns_403(client: TestClient) -> None:
    response = client.post(
        "/objectives",
        headers={"Authorization": "Bearer test-only-token"},
        json={
            "title": "Forbidden objective",
            "success_criteria": ["Must not be created"],
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "The authenticated principal lacks the required permission."
    )


def test_missing_token_configuration_returns_503() -> None:
    app = create_app(
        uow_factory=unused_uow_factory,
        api_token="",
        api_permissions=frozenset({"objectives:write"}),
    )

    with TestClient(app) as test_client:
        response = test_client.post(
            "/objectives",
            json={
                "title": "Unconfigured objective",
                "success_criteria": ["Must not be created"],
            },
        )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "API authentication is not configured."
    )


def test_liveness_remains_public(client: TestClient) -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_read_only_principal_cannot_create_objective() -> None:
    app = create_app(
        uow_factory=unused_uow_factory,
        api_token="read-only-token",
        api_permissions=frozenset({"objectives:read"}),
    )

    with TestClient(app) as test_client:
        response = test_client.post(
            "/objectives",
            headers={"Authorization": "Bearer read-only-token"},
            json={
                "title": "Unauthorized write",
                "success_criteria": ["Must not be created"],
            },
        )

    assert response.status_code == 403


def test_task_write_permission_does_not_grant_task_read() -> None:
    app = create_app(
        uow_factory=unused_uow_factory,
        api_token="write-only-token",
        api_permissions=frozenset({"tasks:write"}),
    )

    with TestClient(app) as test_client:
        response = test_client.get(
            "/tasks/nonexistent-task",
            headers={"Authorization": "Bearer write-only-token"},
        )

    assert response.status_code == 403


def test_objective_read_permission_does_not_grant_task_read() -> None:
    app = create_app(
        uow_factory=unused_uow_factory,
        api_token="objective-reader-token",
        api_permissions=frozenset({"objectives:read"}),
    )

    with TestClient(app) as test_client:
        response = test_client.get(
            "/tasks/nonexistent-task",
            headers={"Authorization": "Bearer objective-reader-token"},
        )

    assert response.status_code == 403


def test_task_read_permission_does_not_grant_state_transition() -> None:
    app = create_app(
        uow_factory=unused_uow_factory,
        api_token="task-reader-token",
        api_permissions=frozenset({"tasks:read"}),
    )

    with TestClient(app) as test_client:
        response = test_client.patch(
            "/tasks/nonexistent-task/state",
            headers={"Authorization": "Bearer task-reader-token"},
            json={"target_state": "ready", "expected_revision": 1},
        )

    assert response.status_code == 403
