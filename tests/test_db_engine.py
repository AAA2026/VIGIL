import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from backend.db.engine import _normalize_url, get_engine, get_sessionmaker  # noqa: E402


def test_postgres_url_normalization():
    url = _normalize_url("postgres://user:pass@localhost:5432/vigil")
    assert url == "postgresql+psycopg://user:pass@localhost:5432/vigil"


def test_engine_and_sessionmaker_share_same_engine_for_same_url():
    engine = get_engine("sqlite:///:memory:")
    sessionmaker_ = get_sessionmaker("sqlite:///:memory:")
    with sessionmaker_() as session:
        assert session.bind is engine
