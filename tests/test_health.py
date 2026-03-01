import os

os.environ["DISABLE_SIMULATOR"] = "1"
os.environ["FAST_BOOT"] = "1"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from backend.app import app  # noqa: E402


def test_health_endpoint():
    client = app.test_client()
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["db"] is True
