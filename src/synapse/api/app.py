
"""FastAPI application factory for SYNAPSE."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import Engine

from synapse.api.routes.objectives import router as objectives_router
from synapse.api.routes.tasks import router as tasks_router
from synapse.core.config import get_settings
from synapse.persistence.database import (
    create_database_engine,
    create_session_factory,
)
from synapse.persistence.unit_of_work import SqlAlchemyUnitOfWork

UowFactory = Callable[[], SqlAlchemyUnitOfWork]



def create_app(
    *,
    uow_factory: UowFactory | None = None,
    api_token: str | None = None,
    api_permissions: frozenset[str] | None = None,
) -> FastAPI:
    """Create and configure the SYNAPSE API application."""

    engine: Engine | None = None
    settings = None

    if uow_factory is None:
        settings = get_settings()
        engine = create_database_engine(settings.database_url)
        session_factory = create_session_factory(engine)

        def default_uow_factory() -> SqlAlchemyUnitOfWork:
            return SqlAlchemyUnitOfWork(session_factory)

        resolved_uow_factory = default_uow_factory
    else:
        resolved_uow_factory = uow_factory

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            if engine is not None:
                engine.dispose()

    app = FastAPI(
        title="SYNAPSE",
        description="A bounded, auditable neuro-symbolic reasoning system.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.state.uow_factory = resolved_uow_factory

    # Explicit arguments override configured defaults.
    configured_token = (
        api_token
        if api_token is not None
        else (
            settings.api_token.get_secret_value()
            if settings is not None and settings.api_token is not None
            else None
        )
    )

    configured_permissions = (
        api_permissions
        if api_permissions is not None
        else (
            settings.api_permissions
            if settings is not None
            else frozenset()
        )
    )

    app.state.api_token = configured_token
    app.state.api_permissions = configured_permissions

    app.include_router(objectives_router)
    app.include_router(tasks_router)

    # Public liveness endpoint; does not require authentication.
    @app.get("/health/live", tags=["health"])
    def liveness() -> dict[str, str]:
        return {"status": "ok"}

    return app
