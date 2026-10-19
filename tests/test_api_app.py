
"""Tests for the SYNAPSE API application."""


import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import synapse.api.app as app_module
from synapse.api.app import create_app
from synapse.core.config import Settings


def unused_uow_factory():
    raise AssertionError("The liveness endpoint must not access persistence.")


def test_liveness_endpoint() -> None:
    app = create_app(uow_factory=unused_uow_factory)

    with TestClient(app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_metadata() -> None:
    app = create_app(uow_factory=unused_uow_factory)

    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "SYNAPSE"
    assert "/health/live" in schema["paths"]

def test_default_app_uses_centralized_settings(
    monkeypatch,
) -> None:
    database_url = (
        "postgresql+psycopg://user:pass@localhost:5432/synapse"
    )
    settings = Settings(
        env="production",
        database_url=database_url,
        api_token="x" * 32,
        api_permissions="objectives:read,tasks:read",
        _env_file=None,
    )

    class FakeEngine:
        disposed = False

        def dispose(self) -> None:
            self.disposed = True

    fake_engine = FakeEngine()
    received_urls: list[str] = []

    def fake_create_database_engine(url: str) -> FakeEngine:
        received_urls.append(url)
        return fake_engine

    monkeypatch.setattr(app_module, "get_settings", lambda: settings)
    monkeypatch.setattr(
        app_module,
        "create_database_engine",
        fake_create_database_engine,
    )
    monkeypatch.setattr(
        app_module,
        "create_session_factory",
        lambda engine: object(),
    )

    app = app_module.create_app()

    assert received_urls == [database_url]
    assert app.state.api_token == "x" * 32
    assert app.state.api_permissions == frozenset(
        {"objectives:read", "tasks:read"}
    )

    with TestClient(app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert fake_engine.disposed is True

def test_default_app_rejects_invalid_production_settings(
    monkeypatch,
) -> None:
    database_url = (
        "postgresql+psycopg://user:pass@localhost:5432/synapse"
    )

    monkeypatch.setattr(
        app_module,
        "get_settings",
        lambda: Settings(
            env="production",
            database_url=database_url,
            api_token=None,
            api_permissions=frozenset(
                {"objectives:read", "tasks:read"}
            ),
            _env_file=None,
        ),
    )

    try:
        with pytest.raises(ValidationError):
            app_module.create_app()
    finally:
        pass


def test_custom_uow_factory_does_not_require_global_settings(
    monkeypatch,
) -> None:
    def fail_if_settings_loaded():
        raise AssertionError(
            "Injected UOW should not require global settings"
        )

    monkeypatch.setattr(
        app_module,
        "get_settings",
        fail_if_settings_loaded,
    )

    app = app_module.create_app(
        uow_factory=unused_uow_factory,
        api_token="test-token",
        api_permissions=frozenset({"objectives:read"}),
    )

    assert app.state.uow_factory is unused_uow_factory
    assert app.state.api_token == "test-token"
    assert app.state.api_permissions == frozenset({"objectives:read"})
