"""
Incident Storage Service (DB-backed)

This module keeps the same public functions as the original in-memory version,
but persists incidents/actions to a database (SQLite by default, Postgres via DATABASE_URL).

Key behavior preserved:
- Dedup/merge within a time window per camera/type, and strict dedup by identical video file path.
- Status workflow: active -> acknowledged -> dispatched -> resolved (plus confirmed for feedback).
- Frontend compatibility: returned incident dict matches legacy keys (id, cameraId, videoUrl, timestamp, etc.)
"""

import time
import threading
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from sqlalchemy.exc import IntegrityError

from backend.db.session import db_session
from backend.db.models import (
    Incident,
    IncidentAction,
    CarCrashIncident,
    ViolenceIncident,
)
from backend.db.runtime import get_or_create_active_run_id, start_new_run

# Thread safety: keep a small lock to preserve deterministic dedup updates under concurrent simulator threads.
_lock = threading.Lock()

_max_incidents = 200  # kept for parity; DB stores more, but API defaults to recent
_update_window_seconds = 40  # merge duplicate events per camera/type within this window

# Simple registry of security personnel for dispatch (demo-only)
_security_roster = [
    {"id": "SEC-101", "name": "Officer Malik", "status": "available"},
    {"id": "SEC-102", "name": "Officer Chen", "status": "available"},
    {"id": "SEC-103", "name": "Officer Rivera", "status": "available"},
    {"id": "SEC-104", "name": "Chief Martinez", "status": "available"},
    {"id": "SEC-105", "name": "Officer Smith", "status": "available"},
]


def _utcnow() -> datetime:
    return datetime.utcnow().replace(tzinfo=timezone.utc)


def _dt_to_epoch(dt: datetime) -> float:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def _epoch_to_dt(epoch: float) -> datetime:
    return datetime.fromtimestamp(epoch, tz=timezone.utc)


def _severity_from_conf(conf: float) -> str:
    # conf in 0..1
    if conf > 0.9:
        return "critical"
    if conf > 0.75:
        return "high"
    if conf > 0.6:
        return "medium"
    return "low"


def _get_description(event_type: str, confidence: float) -> str:
    if event_type == "violence":
        return f"Possible violence detected ({confidence:.0%} confidence)"
    if event_type == "crash":
        return f"Possible traffic incident detected ({confidence:.0%} confidence)"
    if event_type == "people_count":
        return "People counting event"
    return f"Detected event: {event_type} ({confidence:.0%} confidence)"


def _incident_to_dict(inc: Incident) -> Dict:
    ts_epoch = _dt_to_epoch(inc.timestamp)
    d = {
        "id": inc.external_id,
        "incident_number": inc.internal_id,  # stable increasing number
        "type": inc.type,
        "severity": inc.severity,
        "location": inc.location or f"Camera {inc.camera_id}",
        "cameraId": inc.camera_id,
        "timestamp": ts_epoch,
        "timestamp_human": datetime.fromtimestamp(ts_epoch).strftime("%Y-%m-%d %H:%M:%S"),
        "status": inc.status,
        "acknowledged": bool(inc.acknowledged),
        "ack_by": inc.ack_by,
        "dispatched_to": inc.dispatched_to or [],
        "assigned_security": inc.assigned_security,
        "description": inc.description,
        "confidence": float(inc.confidence),
        "video_url": inc.video_url,
        "videoUrl": inc.videoUrl,
        "model": inc.model,
    }

    # Feedback fields
    if inc.aiFeedback is not None:
        d["aiFeedback"] = bool(inc.aiFeedback)
    if inc.feedbackType is not None:
        d["feedbackType"] = inc.feedbackType
    if inc.resolution_type is not None:
        d["resolution_type"] = inc.resolution_type

    # Extra fields
    if inc.extra_json and isinstance(inc.extra_json, dict):
        d.update(inc.extra_json)

    return d


def _add_action(session, inc: Incident, actor: str, action: str, from_status: Optional[str], to_status: Optional[str], detail: Optional[dict] = None):
    a = IncidentAction(
        incident_internal_id=inc.internal_id,
        actor=actor or "system",
        action=action,
        from_status=from_status,
        to_status=to_status,
        detail_json=detail or None,
        created_at=_utcnow().replace(tzinfo=None),
    )
    session.add(a)


def add_incident(camera_id: str, event_type: str, confidence: float, video_path: str, model: str, extra: dict = None) -> Dict:
    """Store a new incident detection (DB-backed) with dedup/merge."""
    # Normalize event_type for crash
    if event_type == "traffic":
        event_type = "crash"

    severity = _severity_from_conf(confidence)
    now_epoch = time.time()
    now_dt = _epoch_to_dt(now_epoch).replace(tzinfo=None)  # store naive UTC in DB

    run_id = get_or_create_active_run_id()

    with _lock:
        with db_session() as s:
            # Strict key lookup first to satisfy unique constraint deterministically
            existing_key = (
                s.query(Incident)
                .filter(Incident.run_id == run_id)
                .filter(Incident.camera_id == camera_id)
                .filter(Incident.type == event_type)
                .filter(Incident.video_url == video_path)
                .order_by(Incident.timestamp.desc(), Incident.internal_id.desc())
                .first()
            )
            if existing_key:
                from_status = existing_key.status
                existing_key.timestamp = now_dt
                existing_key.updated_at = _utcnow().replace(tzinfo=None)
                existing_key.confidence = round(confidence * 100, 1)
                existing_key.severity = severity
                existing_key.description = _get_description(event_type, confidence)
                existing_key.video_url = video_path
                existing_key.videoUrl = video_path
                existing_key.model = model
                if extra:
                    merged = dict(existing_key.extra_json or {})
                    merged.update(extra)
                    existing_key.extra_json = merged
                s.add(existing_key)
                _add_action(
                    s,
                    existing_key,
                    actor="system",
                    action="merge_update",
                    from_status=from_status,
                    to_status=existing_key.status,
                    detail={"confidence": existing_key.confidence, "severity": severity, "video": video_path},
                )
                incident_dict = _incident_to_dict(existing_key)
                _flush_with_dedup(
                    session=s,
                    run_id=run_id,
                    camera_id=camera_id,
                    event_type=event_type,
                    video_path=video_path,
                    now_dt=now_dt,
                    severity=severity,
                    confidence=confidence,
                    model=model,
                    extra=extra,
                )
                _upsert_subtype(s, incident_dict, event_type, extra or {})
                return incident_dict

            # Find an existing incident to merge:
            window_start = (now_dt - timedelta(seconds=_update_window_seconds))
            q = (
                s.query(Incident)
                .filter(Incident.run_id == run_id)
                .filter(Incident.camera_id == camera_id)
                .filter(Incident.type == event_type)
                .filter(
                    (Incident.video_url == video_path) |
                    (Incident.videoUrl == video_path) |
                    (Incident.timestamp >= window_start)
                )
                .order_by(Incident.timestamp.desc())
            )
            existing = q.first()

            if existing:
                from_status = existing.status
                # Update fields; keep existing status
                existing.timestamp = now_dt
                existing.updated_at = _utcnow().replace(tzinfo=None)
                existing.confidence = round(confidence * 100, 1)
                existing.severity = severity
                existing.description = _get_description(event_type, confidence)
                existing.video_url = video_path
                existing.videoUrl = video_path
                existing.model = model

                # Merge extra into extra_json
                if extra:
                    merged = dict(existing.extra_json or {})
                    merged.update(extra)
                    existing.extra_json = merged

                s.add(existing)
                _add_action(
                    s,
                    existing,
                    actor="system",
                    action="merge_update",
                    from_status=from_status,
                    to_status=existing.status,
                    detail={"confidence": existing.confidence, "severity": severity, "video": video_path},
                )
                s.flush()
                incident_dict = _incident_to_dict(existing)

            else:
                # Create new incident record
                external_id = f"INC-{int(now_epoch)}-{camera_id}"
                inc = Incident(
                    external_id=external_id,
                    run_id=run_id,
                    camera_id=camera_id,
                    type=event_type,
                    severity=severity,
                    location=f"Camera {camera_id}",
                    timestamp=now_dt,
                    status="active",
                    acknowledged=False,
                    ack_by=None,
                    dispatched_to=[],
                    assigned_security=None,
                    description=_get_description(event_type, confidence),
                    confidence=round(confidence * 100, 1),
                    video_url=video_path,
                    videoUrl=video_path,
                    model=model,
                    extra_json=extra or None,
                    created_at=_utcnow().replace(tzinfo=None),
                    updated_at=_utcnow().replace(tzinfo=None),
                )
                s.add(inc)
                s.flush()  # get internal_id
                _add_action(
                    s,
                    inc,
                    actor="system",
                    action="create",
                    from_status=None,
                    to_status="active",
                    detail={"confidence": inc.confidence, "severity": severity, "video": video_path},
                )
                incident_dict = _incident_to_dict(inc)

            # Unique constraint may fire under race conditions across processes; handle gracefully.
            incident_dict = _flush_with_dedup(
                session=s,
                run_id=run_id,
                camera_id=camera_id,
                event_type=event_type,
                video_path=video_path,
                now_dt=now_dt,
                severity=severity,
                confidence=confidence,
                model=model,
                extra=extra,
            ) or incident_dict

            # Persist subtype details if provided
            _upsert_subtype(s, incident_dict, event_type, extra or {})

    # Emit websocket notification if available
    try:
        from backend.app import emit_incident_update
        emit_incident_update(incident_dict)
    except Exception as e:
        print(f"[WARN] Could not emit incident update: {e}")

    return incident_dict


def get_incidents(limit: int = 50, event_type: Optional[str] = None, status: Optional[str] = None, include_all: bool = False) -> List[Dict]:
    """Retrieve incidents (defaults to current active demo run)."""
    run_id = get_or_create_active_run_id()
    with db_session() as s:
        q = s.query(Incident)
        if not include_all:
            q = q.filter(Incident.run_id == run_id)
        if event_type:
            if event_type == "traffic":
                event_type = "crash"
            q = q.filter(Incident.type == event_type)
        if status:
            q = q.filter(Incident.status == status)
        q = q.order_by(Incident.timestamp.desc()).limit(limit)
        return [_incident_to_dict(x) for x in q.all()]


def get_incident_by_id(incident_id: str) -> Optional[Dict]:
    with db_session() as s:
        inc = s.query(Incident).filter(Incident.external_id == incident_id).first()
        return _incident_to_dict(inc) if inc else None


def acknowledge_incident(incident_id: str, user_id: str) -> bool:
    with _lock:
        with db_session() as s:
            inc = s.query(Incident).filter(Incident.external_id == incident_id).first()
            if not inc:
                return False
            from_status = inc.status
            inc.acknowledged = True
            inc.ack_by = user_id
            if inc.status == "active":
                inc.status = "acknowledged"
            inc.updated_at = _utcnow().replace(tzinfo=None)
            s.add(inc)
            _add_action(s, inc, actor=user_id or "unknown", action="ack", from_status=from_status, to_status=inc.status, detail=None)
            return True


def dispatch_incident(incident_id: str, security_id: str) -> bool:
    with _lock:
        with db_session() as s:
            inc = s.query(Incident).filter(Incident.external_id == incident_id).first()
            if not inc:
                return False
            from_status = inc.status
            # Append dispatch target
            targets = list(inc.dispatched_to or [])
            if security_id not in targets:
                targets.append(security_id)
            inc.dispatched_to = targets
            inc.assigned_security = security_id
            if inc.status in ("active", "acknowledged"):
                inc.status = "dispatched"
            inc.updated_at = _utcnow().replace(tzinfo=None)
            s.add(inc)
            _add_action(s, inc, actor=security_id or "unknown", action="dispatch", from_status=from_status, to_status=inc.status, detail={"security_id": security_id})
            return True


def mark_incident_resolved(incident_id: str, resolution_type: str = "resolved") -> bool:
    if resolution_type not in ["resolved", "not_resolved", "false_positive"]:
        resolution_type = "resolved"
    with _lock:
        with db_session() as s:
            inc = s.query(Incident).filter(Incident.external_id == incident_id).first()
            if not inc:
                return False
            from_status = inc.status
            inc.status = "resolved"
            inc.resolution_type = resolution_type
            inc.updated_at = _utcnow().replace(tzinfo=None)
            s.add(inc)
            _add_action(s, inc, actor="system", action="resolve", from_status=from_status, to_status="resolved", detail={"resolution_type": resolution_type})
            return True


def ack_all_incidents(user_id: str) -> int:
    """Dismiss all incidents by starting a new demo run (keeps old incidents in DB for history)."""
    run_id = get_or_create_active_run_id()
    with _lock:
        with db_session() as s:
            count = s.query(Incident).filter(Incident.run_id == run_id).count()
    # Start new run AFTER counting
    start_new_run(name=f"Dismissed by {user_id or 'system'}")
    return int(count)


def clear_incidents() -> None:
    """Clear incidents for the UI by starting a new demo run."""
    start_new_run(name="Cleared Incidents")


def get_incident_stats() -> Dict:
    """Return summary statistics for the current run."""
    run_id = get_or_create_active_run_id()
    with db_session() as s:
        total = s.query(Incident).filter(Incident.run_id == run_id).count()
        by_status = {}
        by_type = {}
        rows = s.query(Incident.status, Incident.type).filter(Incident.run_id == run_id).all()
        for st, tp in rows:
            by_status[st] = by_status.get(st, 0) + 1
            by_type[tp] = by_type.get(tp, 0) + 1
    return {"total": total, "by_status": by_status, "by_type": by_type}


def list_security_roster() -> List[Dict]:
    return _security_roster


def save_incident_feedback(incident_id: str, feedback_type: str) -> bool:
    """Process user feedback (confirm/reject) and save data for retraining."""
    if feedback_type not in ("confirm", "reject"):
        return False

    with _lock:
        with db_session() as s:
            inc = s.query(Incident).filter(Incident.external_id == incident_id).first()
            if not inc:
                return False

            from_status = inc.status
            inc.aiFeedback = True
            inc.feedbackType = feedback_type

            if feedback_type == "reject":
                inc.status = "resolved"
                inc.resolution_type = "false_positive"
                print(f"❌ Incident {incident_id} rejected (False Alarm)")
            elif feedback_type == "confirm":
                inc.status = "confirmed"
                print(f"✅ Incident {incident_id} confirmed (True Positive)")

            inc.updated_at = _utcnow().replace(tzinfo=None)
            s.add(inc)

            _add_action(
                s,
                inc,
                actor="operator",
                action="feedback",
                from_status=from_status,
                to_status=inc.status,
                detail={"feedbackType": feedback_type},
            )

            # Copy for retraining (best-effort)
            try:
                incident_dict = _incident_to_dict(inc)
                _copy_for_retraining(incident_dict, feedback_type)
            except Exception as e:
                print(f"[RETRAIN ERROR] Failed to save data: {e}")

            return True


def _copy_for_retraining(incident: Dict, feedback_type: str):
    """Copy video clip + metadata under backend/data/retraining for future training."""
    from backend.app import PROJECT_ROOT  # uses existing constant
    src_rel = incident.get("video_url") or incident.get("videoUrl")
    if not src_rel:
        return

    from pathlib import Path as _P
    video_base = PROJECT_ROOT / "data" / "videos"

    src_rel_path = _P(src_rel)
    if src_rel_path.is_absolute():
        src_path = src_rel_path
    else:
        src_path = video_base / src_rel_path

    if not src_path.exists():
        # Try alternate: fallback to video_base by filename only
        alt = video_base / _P(src_rel).name
        if alt.exists():
            src_path = alt
        else:
            return

    out_dir = PROJECT_ROOT / "backend" / "data" / "retraining" / feedback_type / incident.get("type", "unknown")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Copy video
    out_video = out_dir / f"{incident.get('id')}_{Path(src_path).name}"
    try:
        shutil.copy2(src_path, out_video)
    except Exception:
        # If copy fails, skip
        return

    # Save metadata
    meta = dict(incident)
    meta["saved_at"] = datetime.utcnow().isoformat()
    meta_file = out_dir / f"{incident.get('id')}.json"
    meta_file.write_text(__import__("json").dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def _resolve_unique_conflict(session, run_id: str, camera_id: str, event_type: str, video_path: str,
                             now_dt: datetime, severity: str, confidence: float, model: str, extra: Dict) -> Dict:
    """
    Resolve UNIQUE (run_id, camera_id, type, video_url) conflicts by collapsing duplicates into the newest row.
    """
    session.rollback()
    rows = (
        session.query(Incident)
        .filter(Incident.run_id == run_id)
        .filter(Incident.camera_id == camera_id)
        .filter(Incident.type == event_type)
        .filter(Incident.video_url == video_path)
        .order_by(Incident.timestamp.desc(), Incident.internal_id.desc())
        .all()
    )
    if not rows:
        raise

    # Keep the newest, delete the rest
    keeper = rows[0]
    for dup in rows[1:]:
        session.delete(dup)
    from_status = keeper.status
    keeper.timestamp = now_dt
    keeper.updated_at = _utcnow().replace(tzinfo=None)
    keeper.confidence = round(confidence * 100, 1)
    keeper.severity = severity
    keeper.description = _get_description(event_type, confidence)
    keeper.video_url = video_path
    keeper.videoUrl = video_path
    keeper.model = model
    if extra:
        merged = dict(keeper.extra_json or {})
        merged.update(extra)
        keeper.extra_json = merged
        session.add(keeper)
    _add_action(
        session,
        keeper,
        actor="system",
        action="merge_update",
        from_status=from_status,
        to_status=keeper.status,
        detail={"confidence": keeper.confidence, "severity": severity, "video": video_path},
    )
    session.flush()
    return _incident_to_dict(keeper)


def _flush_with_dedup(session, run_id, camera_id, event_type, video_path, now_dt, severity, confidence, model, extra):
    """
    Try flushing; on IntegrityError resolve duplicates once.
    """
    try:
        session.flush()
        return None
    except IntegrityError:
        return _resolve_unique_conflict(
            session=session,
            run_id=run_id,
            camera_id=camera_id,
            event_type=event_type,
            video_path=video_path,
            now_dt=now_dt,
            severity=severity,
            confidence=confidence,
            model=model,
            extra=extra,
        )


def _upsert_subtype(session, incident_dict: Dict, event_type: str, extra: Dict):
    """Create/update subtype detail tables for crash/violence."""
    if not incident_dict:
        return
    incident_internal_id = incident_dict.get("incident_number")
    if not incident_internal_id:
        return

    if event_type == "crash":
        rec = session.get(CarCrashIncident, incident_internal_id)
        if not rec:
            rec = CarCrashIncident(incident_id=incident_internal_id)
        vehicle_count = extra.get("vehicle_count")
        if vehicle_count is not None:
            rec.vehicle_count = vehicle_count
        severity_level = extra.get("severity_level")
        if severity_level:
            rec.severity_level = severity_level
        session.add(rec)
    elif event_type == "violence":
        rec = session.get(ViolenceIncident, incident_internal_id)
        if not rec:
            rec = ViolenceIncident(incident_id=incident_internal_id)
        violence_type = extra.get("violence_type")
        if violence_type:
            rec.violence_type = violence_type
        persons_involved = extra.get("persons_involved")
        if persons_involved is not None:
            rec.persons_involved = persons_involved
        session.add(rec)
