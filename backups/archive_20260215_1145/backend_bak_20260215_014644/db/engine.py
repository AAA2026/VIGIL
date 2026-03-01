import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv

# Load environment variables from .env/.env.production when present
load_dotenv()

_engine = None  # lazy singleton


def _allow_sqlite_fallback() -> bool:
    """Permit SQLite only for local/dev or when explicitly allowed."""
    env = (os.getenv("FLASK_ENV", "") or os.getenv("ENVIRONMENT", "")).lower()
    explicit = os.getenv("ALLOW_SQLITE_FALLBACK", "0").strip() == "1"
    return explicit or env in ("development", "dev", "local")


def get_database_url() -> str:
    """Return a usable database URL.

    Priority:
    1) DATABASE_URL env var (PostgreSQL recommended)
    2) Fallback to local SQLite file under backend/data/vigil.db for dev/demo
    """
    url = (os.getenv("DATABASE_URL", "") or "").strip()
    if url:
        if url.startswith("postgresql"):
            return url
        if url.startswith("sqlite") and _allow_sqlite_fallback():
            return url
        raise RuntimeError("DATABASE_URL must be PostgreSQL; SQLite is only allowed when ALLOW_SQLITE_FALLBACK=1 in dev.")

    if _allow_sqlite_fallback():
        # Safe dev fallback (SQLite)
        print("[DB] DATABASE_URL not set; using local SQLite fallback for development.")
        sqlite_path = Path(__file__).parent.parent / "data" / "vigil.db"
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{sqlite_path.as_posix()}"

    raise RuntimeError("DATABASE_URL is required (PostgreSQL). Set it to proceed.")


def _is_postgres(url: str) -> bool:
    return url.startswith("postgresql")


def create_db_engine():
    url = get_database_url()
    echo = os.getenv("DB_ECHO", "0").strip() == "1"

    if _is_postgres(url):
        # PostgreSQL production settings
        pool_size = int(os.getenv("DB_POOL_SIZE", "20"))  # Default 20 connections
        max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "10"))  # Allow +10 overflow
        pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "3600"))  # Recycle connections after 1h
        pool_pre_ping = os.getenv("DB_POOL_PRE_PING", "1") == "1"  # Test connection before use

        engine = create_engine(
            url,
            echo=echo,
            future=True,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_recycle=pool_recycle,
            pool_pre_ping=pool_pre_ping,
            connect_args={
                "connect_timeout": 10,
                "options": "-c statement_timeout=30000 -c application_name=vigil-backend",
            },
        )
    else:
        # SQLite dev mode: no pooling, multi-thread friendly
        engine = create_engine(
            url,
            echo=echo,
            future=True,
            poolclass=NullPool,
            connect_args={"check_same_thread": False},
        )

    # Smoke test connectivity early
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as e:
        raise RuntimeError(
            "[DB] Connection failed. Verify DATABASE_URL (or SQLite fallback), network, and credentials."
        ) from e

    return engine


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_db_engine()
    return _engine


# Public engine handle used across the app
engine = get_engine()
