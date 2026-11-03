"""API tests for the read-only reasoning integration."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from synapse.api.app import create_app
from synapse.knowledge.knowledge_graph.engine import KnowledgeGraph


def unused_uow_factory():
    raise AssertionError("Reasoning must not access persistence.")


@pytest.fixture
def graph() -> KnowledgeGraph:
    return KnowledgeGraph()


@pytest.fixture
def client(graph: KnowledgeGraph) -> Iterator[TestClient]:
    app = create_app(
        uow_factory=unused_uow_factory,
        api_token="reasoning-token",
        api_permissions=frozenset({"reasoning:run"}),
        reasoning_graph=graph,
    )
    with TestClient(app) as test_client:
        yield test_client


def _headers() -> dict[str, str]:
    return {"Authorization": "Bearer reasoning-token"}


def test_reasoning_requires_authentication(graph: KnowledgeGraph) -> None:
    app = create_app(
        uow_factory=unused_uow_factory,
        api_token="reasoning-token",
        api_permissions=frozenset({"reasoning:run"}),
        reasoning_graph=graph,
    )
    with TestClient(app) as client:
        response = client.post(
            "/reasoning/run",
            json={"claim_ids": ["missing-claim"]},
        )
    assert response.status_code == 401


def test_reasoning_requires_permission(graph: KnowledgeGraph) -> None:
    app = create_app(
        uow_factory=unused_uow_factory,
        api_token="reasoning-token",
        api_permissions=frozenset(),
        reasoning_graph=graph,
    )
    with TestClient(app) as client:
        response = client.post(
            "/reasoning/run",
            headers=_headers(),
            json={"claim_ids": ["missing-claim"]},
        )
    assert response.status_code == 403


def test_reasoning_graph_must_be_configured() -> None:
    app = create_app(
        uow_factory=unused_uow_factory,
        api_token="reasoning-token",
        api_permissions=frozenset({"reasoning:run"}),
    )
    with TestClient(app) as client:
        response = client.post(
            "/reasoning/run",
            headers=_headers(),
            json={"claim_ids": ["claim-1"]},
        )
    assert response.status_code == 503
    assert response.json()["detail"] == "Reasoning graph is not configured."


def test_invalid_payload_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/reasoning/run",
        headers=_headers(),
        json={"claim_ids": [], "max_depth": 99},
    )
    assert response.status_code == 422
