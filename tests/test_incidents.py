import os

os.environ["DISABLE_SIMULATOR"] = "1"
os.environ["FAST_BOOT"] = "1"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from backend.db import Base, get_engine, get_session  # noqa: E402
from backend.services import incident_storage as storage  # noqa: E402

# Prepare schema
engine = get_engine()
Base.metadata.create_all(engine)


def test_add_and_get_incident():
    storage.clear_incidents()
    incident = storage.add_incident(
        camera_id="CAM-TEST",
        event_type="violence",
        confidence=0.8,
        video_path="violence/test.mp4",
        model="test-model",
    )
    assert incident["cameraId"] == "CAM-TEST"
    fetched = storage.get_incident_by_id(incident["id"])
    assert fetched is not None
    assert fetched["id"] == incident["id"]


def test_ack_and_stats():
    storage.clear_incidents()
    inc = storage.add_incident(
        camera_id="CAM-ACK",
        event_type="crash",
        confidence=0.7,
        video_path="crash/test.mp4",
        model="test-model",
    )
    storage.acknowledge_incident(inc["id"], "tester")
    got = storage.get_incident_by_id(inc["id"])
    assert got["acknowledged"] is True
    stats = storage.get_incident_stats()
    assert stats["total"] >= 1


def test_unique_incident_ids_and_numbers_when_same_timestamp(monkeypatch):
    storage.clear_incidents()
    monkeypatch.setattr(storage.time, "time", lambda: 1700000000.0)

    inc1 = storage.add_incident(
        camera_id="CAM-X",
        event_type="violence",
        confidence=0.81,
        video_path="violence/a.mp4",
        model="m1",
    )
    inc2 = storage.add_incident(
        camera_id="CAM-X",
        event_type="crash",
        confidence=0.77,
        video_path="crash/a.mp4",
        model="m2",
    )

    assert inc1["id"] != inc2["id"]
    assert inc1["incident_number"] != inc2["incident_number"]


def test_ack_all_does_not_override_resolved_status():
    storage.clear_incidents()
    inc = storage.add_incident(
        camera_id="CAM-R",
        event_type="violence",
        confidence=0.9,
        video_path="violence/r.mp4",
        model="m1",
    )
    assert storage.mark_incident_resolved(inc["id"], resolution_type="confirmed") is True
    _ = storage.ack_all_incidents("qa-user")
    got = storage.get_incident_by_id(inc["id"])
    assert got["status"] == "resolved"
