"""
Shared pytest fixtures.

`db_session` gives each test a fresh, isolated in-memory SQLite database
(tables created straight from the SQLAlchemy models -- no migrations
needed, since the models already declare every column the migration
helper would otherwise retrofit).

`client` wires a FastAPI TestClient to use that same `db_session` via a
dependency override, so API-level tests never touch your real dev/prod
database. The app's own `lifespan` (which calls `init_db()` against
`DATABASE_URL`) is pointed at a *separate*, throwaway in-memory DB by
setting `DATABASE_URL` before `main` is imported -- so nothing here can
ever write to `triathlon_coach.db` or a real Postgres instance.
"""
from __future__ import annotations

import os

from main import app

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.data.ciqual_seed import seed_ingredient_nutrition
from app.database import get_db
from app.models.base import Athlete, Base


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    # Mirror what init_db() does for a real DB: seed the Ciqual nutrition
    # table. The app's own lifespan seeds a *different* (throwaway) DB, since
    # this fixture's engine is intentionally isolated from it.
    seed_ingredient_nutrition(session)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def seeded_athletes(db_session):
    """Seed the two athletes so FK-adjacent code has something to point at."""
    db_session.add_all([Athlete(id="B", name="Benji"), Athlete(id="H", name="Hélène")])
    db_session.commit()
    return db_session


@pytest.fixture()
def client(db_session):

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
