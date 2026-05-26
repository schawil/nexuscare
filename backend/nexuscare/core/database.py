"""
Session SQLAlchemy + Base déclarative avec optimisations de performance.
Utilise le pattern get_db() pour l'injection de dépendances FastAPI.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from nexuscare.core.config import settings

# Configuration optimisée pour SQLite en production
# Pour PostgreSQL/MySQL en production, utiliser QueuePool avec pool_size et max_overflow
connect_args = {"check_same_thread": False}

# Optimisation : pool de connexions pour éviter la surcharge de création
# StaticPool est idéal pour SQLite en environnement mono-processus
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG,        # Log SQL en mode debug uniquement
    pool_pre_ping=True,         # Vérifie la connexion avant utilisation
    pool_recycle=3600,          # Recycle les connexions après 1h
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Optimisations SQLite pour de meilleures performances."""
    cursor = dbapi_connection.cursor()
    # Mode WAL pour lectures/écritures concurrentes
    cursor.execute("PRAGMA journal_mode=WAL")
    # Cache plus grand pour réduire les I/O disque
    cursor.execute("PRAGMA cache_size=-64000")  # 64MB
    # Synchronisation moins stricte pour performance (WAL est sûr)
    cursor.execute("PRAGMA synchronous=NORMAL")
    # Temp tables en mémoire
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.close()


class Base(DeclarativeBase):
    """Base commune à tous les modèles SQLAlchemy."""
    pass


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


def get_db():
    """
    Dependency FastAPI : fournit une session DB par requête.
    La session est fermée automatiquement après chaque requête.
    
    Optimisation : expire_on_commit=False évite le rechargement automatique
    des objets après commit, réduisant les requêtes inutiles.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
