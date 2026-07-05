# =================
# ==== IMPORTS ====
# =================

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base, Athlete

# Options

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./triathlon_coach.db")

# Render/Neon fournissent parfois des URLs qui commencent par "postgres://"
# alors que SQLAlchemy attend "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ===================
# ==== FUNCTIONS ====
# ===================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not db.query(Athlete).filter(Athlete.id == "B").first():
            db.add(Athlete(id="B", name="Benji"))
        if not db.query(Athlete).filter(Athlete.id == "H").first():
            db.add(Athlete(id="H", name="Hélène"))
        db.commit()
    finally:
        db.close()
