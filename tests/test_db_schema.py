import os

os.environ["DISABLE_SIMULATOR"] = "1"
os.environ["FAST_BOOT"] = "1"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import inspect  # noqa: E402

from backend.db import Base, get_engine  # noqa: E402


def test_incidents_indexes_exist():
    engine = get_engine()
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    indexes = {idx["name"] for idx in inspector.get_indexes("incidents")}
    checks = {chk["name"] for chk in inspector.get_check_constraints("incidents")}

    assert "ix_incidents_timestamp" in indexes
    assert "ix_incidents_camera_timestamp" in indexes
    assert "ix_incidents_status_timestamp" in indexes
    assert "ix_incidents_type_timestamp" in indexes
    assert "ck_incidents_status_enum" in checks
