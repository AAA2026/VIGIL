import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Text,
    Index,
    Enum,
    CheckConstraint,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from backend.db.base import Base
from backend.db.engine import get_database_url

def _json_type():
    url = get_database_url()
    # Use JSONB on Postgres, JSON on SQLite.
    if url.startswith("postgresql"):
        return JSONB
    return SQLiteJSON

JSONType = _json_type()

# Controlled vocabularies (enforced with CHECK/ENUM)
INCIDENT_TYPES = ("violence", "crash", "people_count", "other")
INCIDENT_STATUSES = ("active", "acknowledged", "dispatched", "resolved", "confirmed")
INCIDENT_SEVERITIES = ("low", "medium", "high", "critical")
USER_ROLES = ("admin", "officer", "security")
NOTIFICATION_CHANNELS = ("email", "sms", "push", "webhook")
NOTIFICATION_PRIORITIES = ("low", "normal", "high", "urgent")
AI_MODEL_TYPES = ("vision", "nlp", "multimodal", "other")
AI_SPECIALIZATIONS = ("violence", "car_crash", "people_count", "other")
VIOLENCE_TYPES = ("assault", "fight", "weapon", "other")
SEVERITY_LEVELS = ("minor", "moderate", "severe", "critical")


class Camera(Base):
    __tablename__ = "camera"
    id = Column(String, primary_key=True)  # e.g. "CAM-01"
    name = Column(String, nullable=False)
    location = Column(String, nullable=True)
    stream_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, server_default="true")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, server_default=func.now())
    model_id = Column(String, ForeignKey("ai_model.id", ondelete="SET NULL"), nullable=True)

class DemoRun(Base):
    __tablename__ = "demo_run"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, default="Demo Run")
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False, server_default=func.now())
    ended_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, server_default="true")

class Incident(Base):
    __tablename__ = "incident"
    internal_id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String, nullable=False, index=True)  # what frontend uses as "id"
    run_id = Column(String, ForeignKey("demo_run.id", ondelete="SET NULL"), nullable=True, index=True)

    camera_id = Column(String, ForeignKey("camera.id", ondelete="RESTRICT"), nullable=False, index=True)
    type = Column(Enum(*INCIDENT_TYPES, name="incident_type"), nullable=False, index=True)
    severity = Column(Enum(*INCIDENT_SEVERITIES, name="incident_severity"), nullable=False)
    location = Column(String, nullable=True)
    model_id = Column(String, ForeignKey("ai_model.id", ondelete="SET NULL"), nullable=True, index=True)

    timestamp = Column(DateTime, nullable=False, index=True)  # event time
    status = Column(Enum(*INCIDENT_STATUSES, name="incident_status"), nullable=False, default="active", server_default="active", index=True)
    acknowledged = Column(Boolean, default=False, nullable=False, server_default="false")
    ack_by = Column(String, nullable=True)
    dispatched_to = Column(JSONType, nullable=False, default=list)  # list of security IDs
    assigned_security = Column(String, nullable=True)

    description = Column(Text, nullable=True)
    confidence = Column(Float, nullable=False)  # percentage 0..100 (matches current API)
    video_url = Column(String, nullable=True)
    videoUrl = Column(String, nullable=True)    # legacy camelCase
    model = Column(String, nullable=True)

    aiFeedback = Column(Boolean, nullable=True)
    feedbackType = Column(String, nullable=True)
    resolution_type = Column(String, nullable=True)

    extra_json = Column(JSONType, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False, server_default=func.now(), onupdate=func.now())

    actions = relationship("IncidentAction", back_populates="incident", cascade="all, delete-orphan")

    __table_args__ = (
Index('idx_incident_dedup', "run_id", "camera_id", "type", "timestamp"),
Index('idx_incident_recent', "status", "timestamp"),
Index('idx_incident_camera_time', "camera_id", "timestamp"),
Index('idx_incident_type_time', "type", "timestamp"),
UniqueConstraint("external_id", name="uq_incident_external_id"),
UniqueConstraint("run_id", "camera_id", "type", "video_url", name="uq_incident_run_cam_type_video"),
CheckConstraint("confidence >= 0 AND confidence <= 100", name="ck_incident_conf_range"),
)

class IncidentAction(Base):
    __tablename__ = "incident_action"
    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_internal_id = Column(Integer, ForeignKey("incident.internal_id", ondelete="CASCADE"), nullable=False, index=True)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    from_status = Column(String, nullable=True)
    to_status = Column(String, nullable=True)
    detail_json = Column(JSONType, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, server_default=func.now())

    incident = relationship("Incident", back_populates="actions")


class CarCrashIncident(Base):
    __tablename__ = "car_crash_incident"
    incident_id = Column(Integer, ForeignKey("incident.internal_id", ondelete="CASCADE"), primary_key=True)
    vehicle_count = Column(Integer, nullable=True)
    severity_level = Column(Enum(*SEVERITY_LEVELS, name="car_crash_severity"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, server_default=func.now())


class ViolenceIncident(Base):
    __tablename__ = "violence_incident"
    incident_id = Column(Integer, ForeignKey("incident.internal_id", ondelete="CASCADE"), primary_key=True)
    violence_type = Column(Enum(*VIOLENCE_TYPES, name="violence_type"), nullable=True)
    persons_involved = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, server_default=func.now())

class DemoRequest(Base):
    __tablename__ = "demo_request"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    fullName = Column(String, nullable=False, default="")
    email = Column(String, nullable=False, default="")
    phone = Column(String, nullable=False, default="")
    organization = Column(String, nullable=False, default="")
    role = Column(String, nullable=False, default="")
    cameras = Column(String, nullable=False, default="")
    message = Column(Text, nullable=False, default="")
    status = Column(String, nullable=False, default="pending", server_default="pending", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, server_default=func.now())
    created_at_human = Column(String, nullable=False, default="")
    updated_at = Column(String, nullable=True)

class Report(Base):
    __tablename__ = "report"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False, index=True)
    format = Column(String, nullable=False)
    generated_date = Column(DateTime, default=datetime.utcnow, nullable=False, server_default=func.now(), index=True)
    file_path = Column(String, nullable=True)
    data_json = Column(JSONType, nullable=True)
    generated_by = Column(String, ForeignKey("app_user.email", ondelete="SET NULL"), nullable=True)

class AppUser(Base):
    __tablename__ = "app_user"
    email = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(*USER_ROLES, name="app_user_role"), nullable=False, default="officer", server_default="officer")
    is_active = Column(Boolean, default=True, nullable=False, server_default="true")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, server_default=func.now())


class Notification(Base):
    __tablename__ = "notification"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(Integer, ForeignKey("incident.internal_id", ondelete="SET NULL"), nullable=True, index=True)
    report_id = Column(String, ForeignKey("report.id", ondelete="SET NULL"), nullable=True, index=True)
    channel = Column(Enum(*NOTIFICATION_CHANNELS, name="notification_channel"), nullable=False, default="push", server_default="push")
    priority = Column(Enum(*NOTIFICATION_PRIORITIES, name="notification_priority"), nullable=False, default="normal", server_default="normal")
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    payload = Column(JSONType, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, server_default=func.now())


class Dashboard(Base):
    __tablename__ = "dashboard"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("app_user.email", ondelete="CASCADE"), nullable=False, index=True)
    view_type = Column(String, nullable=True)
    last_updated = Column(DateTime, nullable=True)
    config = Column(JSONType, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, server_default=func.now())

class VideoFile(Base):
    __tablename__ = "video_file"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    camera_id = Column(String, ForeignKey("camera.id", ondelete="RESTRICT"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    duration = Column(Float, nullable=True)
    video_type = Column(String, nullable=False, index=True)
    incident_id = Column(String, ForeignKey("incident.external_id", ondelete="SET NULL"), nullable=True, index=True)
    uploaded_by = Column(String, ForeignKey("app_user.email", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False, server_default=func.now(), onupdate=func.now())
    video_metadata = Column(JSONType, nullable=True)


class AIModel(Base):
    __tablename__ = "ai_model"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    version = Column(String, nullable=True)
    type = Column(Enum(*AI_MODEL_TYPES, name="ai_model_type"), nullable=False, default="vision", server_default="vision")
    specialization = Column(Enum(*AI_SPECIALIZATIONS, name="ai_specialization"), nullable=False, default="other", server_default="other")
    trained_from_dataset_id = Column(String, ForeignKey("retraining_dataset.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False, server_default=func.now(), onupdate=func.now())


class RetrainingDataset(Base):
    __tablename__ = "retraining_dataset"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    sample_count = Column(Integer, nullable=True)
    last_updated = Column(DateTime, nullable=True)
    location = Column(String, nullable=True)  # path or URL to dataset
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, server_default=func.now())


class AIFeedback(Base):
    __tablename__ = "ai_feedback"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(Integer, ForeignKey("incident.internal_id", ondelete="SET NULL"), nullable=True, index=True)
    related_incident_id = Column(Integer, ForeignKey("incident.internal_id", ondelete="SET NULL"), nullable=True, index=True)
    ai_model_id = Column(String, ForeignKey("ai_model.id", ondelete="SET NULL"), nullable=True, index=True)
    feedback_type = Column(String, nullable=False)  # confirm / reject / other
    confidence_before = Column(Float, nullable=True)
    confidence_after = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, server_default=func.now())
