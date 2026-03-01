import os
from datetime import datetime
from backend.db.engine import engine
from backend.db.base import Base
from backend.db.session import db_session
from backend.db.models import Camera, AppUser
from backend.config import DEFAULT_CAMERAS
from werkzeug.security import generate_password_hash
from backend.db import migrations

DEFAULT_USERS = {
    'admin@vigil.com': {'password': 'admin123', 'role': 'admin', 'name': 'Admin User'},
    'officer@vigil.com': {'password': 'officer123', 'role': 'officer', 'name': 'Officer Smith'},
    'security@vigil.com': {'password': 'security123', 'role': 'security', 'name': 'Chief Martinez'},
}

def init_db():
    """Create tables if they don't exist."""
    Base.metadata.create_all(bind=engine)
    try:
        # Ensure production indexes exist even on upgraded databases.
        migrations.migrate_create_production_indexes()
    except Exception as e:
        print(f"[DB] Index migration warning: {e}")

def _should_seed_demo_data() -> bool:
    """
    Only seed demo cameras/users outside production unless explicitly allowed.
    SEED_DEMO_DATA=1 can override in any environment; default is on for dev, off for prod.
    """
    env = (os.getenv("FLASK_ENV", "") or os.getenv("ENVIRONMENT", "")).lower()
    seed_flag = os.getenv("SEED_DEMO_DATA")
    if seed_flag is not None:
        return seed_flag.strip() == "1"
    return env not in ("production", "prod")

def seed_db():
    """Seed cameras and demo users if absent."""
    if not _should_seed_demo_data():
        return

    with db_session() as s:
        # Seed cameras
        for cam in DEFAULT_CAMERAS:
            # DEFAULT_CAMERAS may be a list[str] or list[dict]
            if isinstance(cam, str):
                cid = cam
                name = f"Camera {cid}"
                location = None
                stream_url = None
            else:
                cid = cam.get("id") or cam.get("camera_id") or cam.get("cameraId")
                name = cam.get("name") or f"Camera {cid}"
                location = cam.get("location")
                stream_url = cam.get("stream_url") or cam.get("streamUrl")
            if not cid:
                continue
            existing = s.query(Camera).filter(Camera.id == cid).first()
            if not existing:
                s.add(Camera(
                    id=cid,
                    name=name,
                    location=location,
                    stream_url=stream_url,
                    is_active=True,
                    created_at=datetime.utcnow(),
                ))

        # Seed users
        for email, u in DEFAULT_USERS.items():
            existing = s.query(AppUser).filter(AppUser.email == email).first()
            if not existing:
                s.add(AppUser(
                    email=email,
                    name=u.get("name") or email,
                    role=u.get("role") or "officer",
                    password_hash=generate_password_hash(u.get("password") or ""),
                    is_active=True,
                    created_at=datetime.utcnow(),
                ))

def init_db_and_seed():
    init_db()
    seed_db()
