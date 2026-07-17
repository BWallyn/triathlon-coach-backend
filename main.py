# =================
# ==== IMPORTS ====
# =================

# Charger le fichier .env AVANT tout import du package `app`, afin que les
# variables (ATHLETE_B_NAME, ATHLETE_H_NAME, DATABASE_URL, clés LLM...) soient
# disponibles dès le chargement de app.config / app.database.
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.database import init_db
from app.routers import (
    ai,
    athletes,
    batch_cooking,
    meals,
    sessions,
    wellness,
)

# Options
load_dotenv()
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://triathlon-coach-frontend.vercel.app",
]

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
    allow_origins=["http://localhost:5173", "http://localhost:3000", "https://triathlon-coach-frontend.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions and return a JSON response with CORS headers if the origin is allowed."""
    response = JSONResponse(status_code=500, content={"detail": "Internal server error"})
    origin = request.headers.get("origin")
    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

app.include_router(athletes.router)
app.include_router(sessions.router)
app.include_router(meals.router)
app.include_router(ai.router)
app.include_router(wellness.router)
app.include_router(batch_cooking.router)


# ===================
# ==== FUNCTIONS ====
# ===================


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}
