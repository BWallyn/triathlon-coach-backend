# =================
# ==== IMPORTS ====
# =================

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import athletes, meals, sessions

# Options

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    init_db()
    yield


app = FastAPI(
    title="TriCouple API",
    description="Planning entraînement, nutrition et batch cooking pour triathlètes",
    version="1.0.0",
    lifespan=lifespan,
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


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}
