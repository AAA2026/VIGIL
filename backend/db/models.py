import time
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Enum,
    Text,
    JSON,
    Index,
    CheckConstraint,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class IncidentStatus(str):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    DISPATCHED = "dispatched"
    RESOLVED = "resolved"


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        Index("ix_incidents_timestamp", "timestamp"),
        Index("ix_incidents_camera_timestamp", "camera_id", "timestamp"),
        Index("ix_incidents_status_timestamp", "status", "timestamp"),
        Index("ix_incidents_type_timestamp", "type", "timestamp"),
        CheckConstraint("confidence >= 0 AND confidence <= 100", name="ck_incidents_confidence_range"),
        CheckConstraint("acknowledged IN (0, 1)", name="ck_incidents_acknowledged_bool"),
        CheckConstraint(
            "status IN ('active', 'acknowledged', 'dispatched', 'resolved')",
            name="ck_incidents_status_enum",
        ),
    )

    id = Column(String, primary_key=True)
    incident_number = Column(Integer, autoincrement=True, nullable=True, unique=True)
    type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    location = Column(String(255), nullable=True)
    camera_id = Column(String(50), nullable=False)
    timestamp = Column(Float, default=lambda: time.time(), nullable=False)
    status = Column(String(32), default=IncidentStatus.ACTIVE, nullable=False)
    acknowledged = Column(Integer, default=0)
    ack_by = Column(String(120), nullable=True)
    dispatched_to = Column(Text, nullable=True)  # comma-separated list
    assigned_security = Column(String(120), nullable=True)
    description = Column(Text, nullable=True)
    confidence = Column(Float, default=0.0)
    video_url = Column(String(512), nullable=True)
    model = Column(String(120), nullable=True)
    extra = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "incident_number": self.incident_number,
            "type": self.type,
            "severity": self.severity,
            "location": self.location,
            "cameraId": self.camera_id,
            "timestamp": self.timestamp,
            "timestamp_human": datetime.utcfromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S"),
            "status": self.status,
            "acknowledged": bool(self.acknowledged),
            "ack_by": self.ack_by,
            "dispatched_to": (self.dispatched_to or "").split(",") if self.dispatched_to else [],
            "assigned_security": self.assigned_security,
            "description": self.description,
            "confidence": self.confidence,
            "video_url": self.video_url,
            "videoUrl": self.video_url,
            "model": self.model,
            "extra": self.extra or {},
        }
