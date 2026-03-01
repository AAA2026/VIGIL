from contextlib import contextmanager
from sqlalchemy.orm import sessionmaker
from backend.db.engine import engine

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

@contextmanager
def db_session():
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
