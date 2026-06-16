from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base, Athlete

DATABASE_URL = "sqlite:///./tricouple.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    # Seed default athletes
    db = SessionLocal()
    try:
        if not db.query(Athlete).filter(Athlete.id == "B").first():
            db.add(Athlete(id="B", name="Benji"))
        if not db.query(Athlete).filter(Athlete.id == "C").first():
            db.add(Athlete(id="C", name="Ma copine"))
        db.commit()
    finally:
        db.close()
