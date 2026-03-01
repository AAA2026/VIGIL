"""
Incident Storage Service (PostgreSQL/SQLAlchemy)

Persists detected incidents and exposes helper CRUD functions used by the
Flask routes and simulator. Falls back to SQLite for local dev/tests if
DATABASE_URL is not set.
"""

import time
import uuid
from typing import List, Dict, Optional

from sqlalchemy import select, func, update, delete
from sqlalchemy.exc import IntegrityError

from backend.db import Incident, get_session

# Simple registry of security personnel for dispatch (demo-only)
_security_roster = [
    {"id": "SEC-101", "name": "Officer Malik", "status": "available"},
    {"id": "SEC-102", "name": "Officer Chen", "status": "available"},
    {"id": "SEC-103", "name": "Officer Rivera", "status": "available"},
    {"id": "SEC-104", "name": "Chief Martinez", "status": "available"},
    {"id": "SEC-105", "name": "Officer Smith", "status": "available"},
]

_update_window_seconds = 40  # merge duplicate events per camera/type within this window
_max_insert_retries = 5


def _severity(confidence: float) -> str:
    return (
        "critical" if confidence > 0.9 else
        "high" if confidence > 0.75 else
        "medium" if confidence > 0.6 else
        "low"
    )


def _get_description(event_type: str, confidence: float) -> str:
    if event_type == "violence":
        return "Possible violence detected"
    if event_type == "crash":
        return "Possible vehicle crash detected"
    return f"Detected {event_type} @ {round(confidence*100,1)}%"


def _new_incident_id() -> str:
    return f"INC-{uuid.uuid4().hex[:14].upper()}"


def _next_incident_number(session) -> int:
    current = session.scalar(select(func.max(Incident.incident_number))) or 0
    return int(current) + 1


def add_incident(camera_id: str, event_type: str, confidence: float, video_path: str, model: str, extra: dict = None) -> Dict:
    """Create or merge an incident and persist to DB."""
    if event_type == "traffic":
        event_type = "crash"

    now_ts = time.time()
    severity = _severity(confidence)

    Session = get_session()
    with Session() as session:
        session.expire_on_commit = False

        # Dedup: same camera/type within time window OR same video file
        stmt = (
            select(Incident)
            .where(Incident.camera_id == camera_id)
            .where(Incident.type == event_type)
            .where(
                (Incident.video_url == video_path)
                | (Incident.timestamp >= now_ts - _update_window_seconds)
            )
            .order_by(Incident.timestamp.desc())
        )
        existing = session.scalars(stmt).first()

        if existing:
            existing.timestamp = now_ts
            existing.confidence = round(confidence * 100, 1)
            existing.severity = severity
            existing.description = _get_description(event_type, confidence)
            existing.video_url = video_path
            existing.model = model
            if extra:
                existing.extra = {**(existing.extra or {}), **extra}
            session.commit()
            incident = existing
        else:
            incident = None
            for _ in range(_max_insert_retries):
                incident = Incident(
                    id=_new_incident_id(),
                    incident_number=_next_incident_number(session),
                    type=event_type,
                    severity=severity,
                    location=f"Camera {camera_id}",
                    camera_id=camera_id,
                    timestamp=now_ts,
                    status="active",
                    acknowledged=0,
                    ack_by=None,
                    dispatched_to="",
                    assigned_security=None,
                    description=_get_description(event_type, confidence),
                    confidence=round(confidence * 100, 1),
                    video_url=video_path,
                    model=model,
                    extra=extra or {},
                )
                session.add(incident)
                try:
                    session.commit()
                    break
                except IntegrityError:
                    # Handle rare race on unique incident_number with a retry.
                    session.rollback()
                    incident = None

            if incident is None:
                raise RuntimeError("Failed to insert incident after retrying")

        session.refresh(incident)
        payload = incident.to_dict()

    # Emit websocket notification if available
    try:
        from backend.app import emit_incident_update
        emit_incident_update(payload)
    except Exception:
        pass
    return payload


def get_incidents(limit: int = 50, event_type: Optional[str] = None, status: Optional[str] = None) -> List[Dict]:
    Session = get_session()
    with Session() as session:
        stmt = select(Incident).order_by(Incident.timestamp.desc()).limit(limit)
        if event_type:
            stmt = stmt.where(Incident.type == event_type)
        if status:
            stmt = stmt.where(Incident.status == status)
        return [row.to_dict() for row in session.scalars(stmt).all()]


def get_incident_by_id(incident_id: str) -> Optional[Dict]:
    Session = get_session()
    with Session() as session:
        obj = session.get(Incident, incident_id)
        return obj.to_dict() if obj else None


def mark_incident_resolved(incident_id: str, resolution_type: str = "resolved") -> bool:
    Session = get_session()
    with Session() as session:
        obj = session.get(Incident, incident_id)
        if not obj:
            return False
        extra = obj.extra or {}
        extra["resolution_type"] = resolution_type
        obj.extra = extra
        obj.status = "resolved"
        session.commit()
        return True


def acknowledge_incident(incident_id: str, user_id: str) -> bool:
    Session = get_session()
    with Session() as session:
        updated = session.execute(
            update(Incident)
            .where(Incident.id == incident_id)
            .values(acknowledged=1, ack_by=user_id, status="acknowledged")
        )
        session.commit()
        return updated.rowcount > 0


def ack_all_incidents(user_id: str) -> int:
    Session = get_session()
    with Session() as session:
        updated = session.execute(
            update(Incident)
            .where(Incident.status != "resolved")
            .values(acknowledged=1, ack_by=user_id, status="acknowledged")
        )
        session.commit()
        return updated.rowcount


def dispatch_incident(incident_id: str, security_id: str) -> bool:
    Session = get_session()
    with Session() as session:
        obj = session.get(Incident, incident_id)
        if not obj:
            return False
        dispatched = (obj.dispatched_to or "").split(",") if obj.dispatched_to else []
        if security_id not in dispatched:
            dispatched.append(security_id)
        obj.dispatched_to = ",".join(filter(None, dispatched))
        obj.assigned_security = security_id
        obj.status = "dispatched"
        session.commit()
        return True


def list_security_roster():
    return _security_roster


def clear_incidents() -> int:
    Session = get_session()
    with Session() as session:
        deleted = session.execute(delete(Incident))
        session.commit()
        return deleted.rowcount


def get_incident_stats() -> Dict:
    Session = get_session()
    with Session() as session:
        total = session.scalar(select(func.count(Incident.id))) or 0
        active = session.scalar(select(func.count(Incident.id)).where(Incident.status == "active")) or 0
        resolved = session.scalar(select(func.count(Incident.id)).where(Incident.status == "resolved")) or 0
        return {"total": total, "active": active, "resolved": resolved}


def save_incident_feedback(incident_id: str, feedback_type: str) -> bool:
    Session = get_session()
    with Session() as session:
        obj = session.get(Incident, incident_id)
        if not obj:
            return False
        extra = obj.extra or {}
        extra["feedback"] = feedback_type
        obj.extra = extra
        session.commit()
        return True
