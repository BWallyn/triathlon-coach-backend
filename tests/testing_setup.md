# Backend test suite — setup

63 tests, all passing (verified against a reconstruction of your backend in
a sandbox). Drop the `tests/` folder into your repo root (next to `app/`
and `main.py`) and follow the steps below.

## 1. Install dev dependencies

```bash
uv add --dev pytest httpx
# or: pip install pytest httpx
```

`httpx` is required by `fastapi.testclient.TestClient`, not by your app itself.

## 2. Point pytest at the right place

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
```

## 3. Run it

```bash
uv run pytest -v
# or: pytest -v
```

## What's covered in this first batch

- **`test_batch_utils.py`** — `scale_quantity`, `compute_portion_macros`,
  `current_season`. Pure functions, no DB.
- **`test_charge_calculation.py`** — `_compute_charge` (meals.py) and
  `_charge_for_day`/`_charge_for_athlete_day` (wellness.py), including a
  test that the two independent implementations agree at the high/med/low
  boundaries.
- **`test_races.py`** — `_validate_race` as a unit test, plus a few
  API-level tests (invalid format rejected, valid race round-trips, shared
  `athlete_id=None` races show up for both athletes).
- **`test_batch_cooking_api.py`** — the full plan-creation flow through the
  real API: portions grouped correctly by (date, slot), macros scale with
  presets, non-scalable ingredients (salt etc.) stay fixed, existing meals
  get overwritten, the shopping list sums scaled quantities correctly, and
  a recipe in use by a plan can't be deleted.

## `conftest.py` — how isolation works

- `db_session`: a fresh **in-memory SQLite DB per test**, built straight
  from your SQLAlchemy models (`Base.metadata.create_all`) — no migration
  step needed, since your models already declare every column the
  `_migrate_missing_columns` helper would otherwise retrofit on a real DB.
  It also seeds the Ciqual nutrition table directly, since your app's
  `lifespan` only seeds whatever DB `DATABASE_URL` points at.
- `client`: a `TestClient` wired to use that same `db_session` via a
  dependency override on `get_db`. **Nothing here ever touches your real
  dev SQLite file or a Postgres/Neon instance** — `DATABASE_URL` is forced
  to `sqlite:///:memory:` before `main` is even imported, so even the
  app's own `lifespan` startup is sandboxed to a throwaway DB.
- `seeded_athletes`: convenience fixture that inserts `Athlete(id="B")` /
  `Athlete(id="H")` when a test needs them to exist (SQLite doesn't enforce
  FK constraints by default, so most tests don't strictly need this, but a
  few of the race tests use it for realism).

## One assumption I made

Your `app/models/base.py` document didn't show a `discipline` column on the
`Race` model, but `RaceIn`/`RaceOut` schemas and `_validate_race` clearly
expect one, and your migration helper retrofits it via `ALTER TABLE`. I
assumed it's just missing from that particular doc snapshot and added
`discipline = Column(String, nullable=False, default="triathlon")` to the
reconstructed model so the tests would even run. **Worth double-checking
your actual `app/models/base.py` has this** — if it doesn't, `race.discipline`
would already be broken in production today (Pydantic's `from_attributes`
would fail trying to read it off the ORM object).

## Suggested next batch (not included here)

- `app/routers/ai.py`'s `_training_phase`, `_race_context`,
  `_recent_feedback_summary` — pure-ish, DB-session-based, no LLM call
  involved, straightforward to unit test with a `db_session` fixture.
- Wellness upsert behavior (sleep/feeling/weight "update if exists, else
  create") via the API — the same pattern is repeated three times and
  would benefit from being locked down once.
- A smoke test for `_migrate_missing_columns` against a DB seeded with the
  *old* schema (pre-migration columns) to confirm it doesn't blow up.