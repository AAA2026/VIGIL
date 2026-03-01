from datetime import datetime
import uuid
from backend.db.session import db_session
from backend.db.models import DemoRequest

def _to_dict(r: DemoRequest) -> dict:
    return {
        "id": r.id,
        "fullName": r.fullName,
        "email": r.email,
        "phone": r.phone,
        "organization": r.organization,
        "role": r.role,
        "cameras": r.cameras,
        "message": r.message,
        "status": r.status,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "created_at_human": r.created_at_human,
        "updated_at": r.updated_at
    }

def get_demo_requests():
    """Load all demo requests (newest first)."""
    with db_session() as s:
        rows = s.query(DemoRequest).order_by(DemoRequest.created_at.desc()).all()
        return [_to_dict(x) for x in rows]

def save_demo_request(data):
    """Save a new demo request."""
    now = datetime.now()
    new_request = DemoRequest(
        id=str(uuid.uuid4()),
        fullName=data.get("fullName", ""),
        email=data.get("email", ""),
        phone=data.get("phone", ""),
        organization=data.get("organization", ""),
        role=data.get("role", ""),
        cameras=data.get("cameras", ""),
        message=data.get("message", ""),
        status="pending",
        created_at=now,
        created_at_human=now.strftime("%Y-%m-%d %H:%M"),
        updated_at=None
    )
    with db_session() as s:
        s.add(new_request)
        s.flush()
        return _to_dict(new_request)

def update_demo_request_status(request_id, status):
    """Update the status of a request."""
    with db_session() as s:
        req = s.query(DemoRequest).filter(DemoRequest.id == request_id).first()
        if not req:
            return False
        req.status = status
        req.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        s.add(req)
        return True
