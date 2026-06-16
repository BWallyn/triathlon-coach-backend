# tricouple-backend

API FastAPI + SQLite pour l'application TriCouple.

## Installation

```bash
cd tricouple-backend
python -m venv venv
source venv/bin/activate       # Windows : venv\Scripts\activate
pip install -r requirements.txt
```

## Lancement

```bash
uvicorn app.main:app --reload --port 8000
```

L'API est disponible sur `http://localhost:8000`  
Documentation interactive : `http://localhost:8000/docs`

## Structure

```
tricouple-backend/
├── app/
│   ├── main.py          # Point d'entrée FastAPI
│   ├── database.py      # Engine SQLite + init
│   ├── schemas.py       # Pydantic schemas
│   ├── models/
│   │   └── base.py      # SQLAlchemy models
│   └── routers/
│       ├── athletes.py  # GET/PATCH /athletes
│       ├── sessions.py  # GET/POST/DELETE /sessions
│       └── meals.py     # GET/POST/PUT/DELETE /meals + /meals/generate
├── requirements.txt
└── tricouple.db         # Créé automatiquement au premier lancement
```

## Endpoints principaux

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/athletes` | Liste des athlètes |
| PATCH | `/athletes/{id}` | Renommer un athlète |
| GET | `/sessions` | Séances (filtres: week_start, week_end, athlete_id) |
| POST | `/sessions` | Ajouter une séance |
| DELETE | `/sessions/{id}` | Supprimer une séance |
| GET | `/meals` | Repas (filtres: week_start, week_end) |
| POST | `/meals/generate` | Générer repas depuis la charge réelle |
| POST | `/meals` | Créer un repas manuel |
| PUT | `/meals/{id}` | Modifier un repas |
| DELETE | `/meals/{id}` | Supprimer un repas |
