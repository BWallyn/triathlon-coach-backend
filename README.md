# Triathlon coach backend

API FastAPI + SQLite for the Triathlon coach app.

## Installation

```bash
cd triathlon-coach-backend
python -m venv venv
source venv/bin/activate       # Windows : venv\Scripts\activate
pip install -r requirements.txt
```

## Launch

```bash
uvicorn app.main:app --reload --port 8000
```

The API is available at `http://localhost:8000`  
Interactive documentation: `http://localhost:8000/docs`

## Structure

```
triathlon-coach-backend/
├── app/
│   ├── main.py          # FastAPI entry point
│   ├── database.py      # SQLite engine + init
│   ├── schemas.py       # Pydantic schemas
│   ├── models/
│   │   └── base.py      # SQLAlchemy models
│   └── routers/
│       ├── athletes.py  # GET/PATCH /athletes
│       ├── sessions.py  # GET/POST/DELETE /sessions
│       └── meals.py     # GET/POST/PUT/DELETE /meals + /meals/generate
├── requirements.txt
└── triathlon_coach.db   # Automatically created at first launch
```

## Main endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/athletes` | List of athletes |
| PATCH | `/athletes/{id}` | Rename an athlete |
| GET | `/sessions` | Sessions (filters: week_start, week_end, athlete_id) |
| POST | `/sessions` | Add a session |
| DELETE | `/sessions/{id}` | Delete a session |
| GET | `/meals` | Meals (filters: week_start, week_end) |
| POST | `/meals/generate` | Generate meals using the real load |
| POST | `/meals` | Manually create a meal |
| PUT | `/meals/{id}` | Modify a meal |
| DELETE | `/meals/{id}` | Delete a meal |
