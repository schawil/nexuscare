"""
Session SQLAlchemy + Base déclarative.
Utilise le pattern get_db() pour l'injection de dépendances FastAPI.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from nexuscare.core.config import settings

# check_same_thread=False requis pour SQLite avec FastAPI (threads multiples)
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=settings.DEBUG,        # Log SQL en mode debug
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base commune à tous les modèles SQLAlchemy."""
    pass


def get_db():
    """
    Dependency FastAPI : fournit une session DB par requête.
    La session est fermée automatiquement après chaque requête.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
