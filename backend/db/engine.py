"""Database engine/session configuration."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


def _normalize_url(url: str) -> str:
    clean = (url or "").strip()
    if clean.startswith("postgres://"):
        return "postgresql+psycopg://" + clean[len("postgres://") :]
    if clean.startswith("postgresql://") and "+psycopg" not in clean:
        return clean.replace("postgresql://", "postgresql+psycopg://", 1)
    return clean


def _get_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except (TypeError, ValueError):
        return default


def _get_url() -> str:
    url = _normalize_url(os.getenv("DATABASE_URL", ""))
    if url:
        return url
    # Dev fallback for local smoke/testing when DATABASE_URL is absent.
    return "sqlite:///./vigil.db"


def _is_sqlite(db_url: str) -> bool:
    return db_url.startswith("sqlite")


def _sqlite_connect_args() -> dict:
    # timeout avoids "database is locked" bursts during local concurrent writes.
    return {"check_same_thread": False, "timeout": 30}


def _engine_kwargs(db_url: str) -> dict:
    kwargs = {
        "echo": _get_bool_env("DB_ECHO", False),
        "future": True,
    }

    if _is_sqlite(db_url):
        kwargs["connect_args"] = _sqlite_connect_args()
        if db_url.endswith(":memory:") or db_url.endswith("://"):
            # Shared in-memory DB for tests/process-local sessions.
            kwargs["poolclass"] = StaticPool
    else:
        kwargs.update(
            {
                "pool_pre_ping": True,
                "pool_size": _get_int_env("DB_POOL_SIZE", 10),
                "max_overflow": _get_int_env("DB_MAX_OVERFLOW", 20),
                "pool_timeout": _get_int_env("DB_POOL_TIMEOUT", 30),
                "pool_recycle": _get_int_env("DB_POOL_RECYCLE", 1800),
            }
        )

    return kwargs


@lru_cache(maxsize=8)
def _engine_for_url(db_url: str) -> Engine:
    engine = create_engine(db_url, **_engine_kwargs(db_url))

    if _is_sqlite(db_url):
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):  # type: ignore[unused-argument]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

    return engine


def get_engine(url: Optional[str] = None) -> Engine:
    db_url = _normalize_url(url or _get_url())
    return _engine_for_url(db_url)


@lru_cache(maxsize=8)
def _sessionmaker_for_url(db_url: str):
    engine = get_engine(url=db_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)


def get_sessionmaker(url: Optional[str] = None):
    db_url = _normalize_url(url or _get_url())
    return _sessionmaker_for_url(db_url)


def get_session(url: Optional[str] = None):
    return get_sessionmaker(url=url)
