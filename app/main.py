# =================
# ==== IMPORTS ====
# =================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import athletes, sessions, meals

# Options

app = FastAPI(
    title="TriCouple API",
    description="Planning entraînement, nutrition et batch cooking pour triathlètes",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(athletes.router)
app.include_router(sessions.router)
app.include_router(meals.router)


# ===================
# ==== FUNCTIONS ====
# ===================

@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}
