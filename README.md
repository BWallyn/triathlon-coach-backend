# Triathlon Coach — Backend

FastAPI + SQLAlchemy API powering Triathlon Coach, a triathlon training and nutrition
companion app for two athletes (`B` and `H`) who train together, targeting
Olympic and Half-Ironman race formats.

## Installation

```bash
cd triathlon-coach-backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Or with `uv` (recommended, matches `uv.lock`):

```bash
uv sync
```

Copy `.env.example` to `.env` and fill in the values (see **Environment
variables** below).

## Launch

```bash
uvicorn main:app --reload --port 8000
```

The API is available at `http://localhost:8000`
Interactive documentation: `http://localhost:8000/docs`

On startup, the app creates any missing tables, retrofits missing columns on
existing tables (SQLite/Postgres migrations don't happen automatically via
`create_all()`), syncs athlete names from environment variables, and seeds
ingredient nutrition data from Ciqual (ANSES).

## Environment variables

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy connection string. Accepts Neon/Render-style `postgres://` URLs (auto-rewritten to `postgresql://`). | `sqlite:///./triathlon_coach.db` |
| `ATHLETE_B_NAME` / `ATHLETE_H_NAME` | Display names for the two athletes. Internal IDs `B`/`H` stay fixed throughout the code — only the displayed name changes. | `Athlete B` / `Athlete H` |
| `LLM_PROVIDER` | `anthropic` or `openai` | `anthropic` |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | API key for the selected LLM provider | — |
| `LLM_MODEL` | Override the default model for the selected provider | provider default |

## Structure

```
triathlon-coach-backend/
├── main.py                  # FastAPI entry point, CORS, exception handling
├── app/
│   ├── config.py             # Athlete display names from env vars
│   ├── database.py           # Engine, session, migrations, seeding
│   ├── llm.py                 # LLM client abstraction (Anthropic / OpenAI)
│   ├── prompts.py             # All LLM prompts (training plan, meals, analysis)
│   ├── batch_utils.py          # Batch-cooking preset scaling & macro computation
│   ├── data/
│   │   └── ciqual_seed.py       # Seed nutrition data (Ciqual / ANSES)
│   ├── models/
│   │   └── base.py               # SQLAlchemy models
│   ├── schemas.py             # Pydantic schemas
│   └── routers/
│       ├── athletes.py         # GET/PATCH /athletes
│       ├── sessions.py         # Planned sessions + logged results (performance)
│       ├── races.py            # Target races (A/B/C priority, per discipline)
│       ├── meals.py            # Weekly meal planning + auto-generation
│       ├── wellness.py         # Sleep, feeling, weight + dashboard summary
│       ├── batch_cooking.py    # Batch recipes, cooking plans, shopping lists
│       └── ai.py                # AI-powered training plan / meals / weekly analysis
├── requirements.txt
└── triathlon_coach.db        # Created automatically on first launch (SQLite)
```

## Main endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/athletes` | List of athletes |
| PATCH | `/athletes/{id}` | Rename an athlete |
| GET/POST/DELETE | `/sessions` | Planned training sessions (filters: week_start, week_end, athlete_id) |
| GET | `/sessions/results` | Logged performance results, joined with the planned session |
| POST/GET/DELETE | `/sessions/{id}/result` | Upsert / fetch / delete a session's actual results |
| GET/POST/PUT/DELETE | `/races` | Target races per athlete or shared |
| GET/POST/PUT/DELETE | `/meals` | Weekly meal plan |
| POST | `/meals/generate` | Auto-generate meals based on actual training load |
| GET/POST | `/wellness/sleep`, `/wellness/feeling`, `/wellness/weight` | Wellness logs (upsert per athlete/date) |
| DELETE | `/wellness/weight/{id}` | Delete a weight entry |
| GET | `/wellness/summary` | Combined weekly dashboard data (load, sleep, feeling) |
| GET/POST/PUT/DELETE | `/batch-cooking/recipes` | Batch-cooking recipes |
| POST | `/batch-cooking/plans` | Assign portions of a recipe to meal slots with a macro preset |
| GET | `/batch-cooking/plans/{id}/shopping-list` | Total ingredient quantities to cook |
| POST | `/ai/training-plan` | Generate a weekly training plan, informed by races and recent wellness/performance data |
| POST | `/ai/meals/smart-generate` | Context-aware meal suggestions via LLM |
| GET | `/ai/weekly-analysis` | Load, recovery, and nutrition analysis via LLM |

## Notes

- `DATABASE_URL` should point at SQLite locally and PostgreSQL (Neon) in
  production; schema changes to existing tables are applied via the
  `_migrate_missing_columns()` helper in `app/database.py`, since
  `create_all()` cannot alter existing tables.
- A global exception handler ensures CORS headers are present even on
  unhandled 500 responses (Starlette's `ServerErrorMiddleware` sits above
  `CORSMiddleware`, so uncaught exceptions would otherwise bypass CORS).