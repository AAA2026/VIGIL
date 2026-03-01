"""
Data Retention & Archival Policy for Vigil

Manages incident lifecycle and data cleanup to prevent unbounded table growth.
Configurable via environment variables for different retention requirements:
- Law enforcement: Longer retention (90+ days)
- Enterprise: Standard retention (30 days)
- High-volume deployments: Archive to cold storage
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from backend.db.session import db_session
from backend.db.models import Incident, IncidentAction


def get_retention_days() -> int:
    """Get incident retention period in days (default 30)."""
    return int(os.getenv("INCIDENT_RETENTION_DAYS", "30"))


def get_archive_path() -> Path:
    """Get path to cold storage archive directory."""
    archive_dir = Path(os.getenv("INCIDENT_ARCHIVE_PATH", "/data/archives"))
    archive_dir.mkdir(parents=True, exist_ok=True)
    return archive_dir


def archive_old_incidents(days_old: int = None) -> dict:
    """
    Archive resolved incidents older than retention period.
    
    Args:
        days_old: Days threshold (default from get_retention_days())
    
    Returns:
        dict with archived_count, deleted_count, archive_file
    """
    if days_old is None:
        days_old = get_retention_days()
    
    cutoff_date = datetime.utcnow() - timedelta(days=days_old)
    archived_count = 0
    deleted_count = 0
    archive_file = None
    
    with db_session() as s:
        # Find old, resolved incidents
        old_incidents = (
            s.query(Incident)
            .filter(Incident.status == "resolved")
            .filter(Incident.updated_at < cutoff_date)
            .all()
        )
        
        if old_incidents:
            # Export to JSON archive before deletion
            archive_data = []
            for inc in old_incidents:
                archive_data.append({
                    "internal_id": inc.internal_id,
                    "external_id": inc.external_id,
                    "camera_id": inc.camera_id,
                    "type": inc.type,
                    "confidence": inc.confidence,
                    "timestamp": inc.timestamp.isoformat() if inc.timestamp else None,
                    "status": inc.status,
                    "actions_count": len(inc.actions),
                    "archived_at": datetime.utcnow().isoformat(),
                })
            
            # Write to archive file
            archive_dir = get_archive_path()
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            archive_file = archive_dir / f"incidents_archive_{timestamp}.json"
            
            with open(archive_file, "w") as f:
                json.dump(archive_data, f, indent=2)
            
            archived_count = len(old_incidents)
            
            # Delete from active DB (with cascade to IncidentAction)
            for inc in old_incidents:
                s.delete(inc)
            
            deleted_count = archived_count
    
    return {
        "archived_count": archived_count,
        "deleted_count": deleted_count,
        "archive_file": str(archive_file) if archive_file else None,
        "cutoff_date": cutoff_date.isoformat(),
    }


def cleanup_demo_runs(keep_active: bool = True) -> dict:
    """
    Clean up old demo runs and their incidents.
    
    Args:
        keep_active: If True, only delete ended demo runs
    
    Returns:
        dict with deleted_count
    """
    from backend.db.models import DemoRun
    
    deleted_count = 0
    with db_session() as s:
        if keep_active:
            # Delete ended demo runs older than 7 days
            cutoff = datetime.utcnow() - timedelta(days=7)
            old_runs = (
                s.query(DemoRun)
                .filter(DemoRun.is_active == False)
                .filter(DemoRun.ended_at < cutoff)
                .all()
            )
        else:
            # Delete all old runs
            cutoff = datetime.utcnow() - timedelta(days=30)
            old_runs = (
                s.query(DemoRun)
                .filter(DemoRun.started_at < cutoff)
                .all()
            )
        
        for run in old_runs:
            # Cascade deletes incidents for this run
            s.delete(run)
            deleted_count += 1
    
    return {"deleted_count": deleted_count}


def get_table_stats() -> dict:
    """Get database statistics for monitoring."""
    from sqlalchemy import func, text
    
    stats = {}
    with db_session() as s:
        try:
            # Incident counts by status
            incident_by_status = (
                s.query(Incident.status, func.count(Incident.internal_id))
                .group_by(Incident.status)
                .all()
            )
            stats["incidents_by_status"] = {status: count for status, count in incident_by_status}
            
            # Total incident count
            total_incidents = s.query(func.count(Incident.internal_id)).scalar()
            stats["total_incidents"] = total_incidents
            
            # Incidents in last 24h
            cutoff_24h = datetime.utcnow() - timedelta(hours=24)
            recent_incidents = (
                s.query(func.count(Incident.internal_id))
                .filter(Incident.created_at > cutoff_24h)
                .scalar()
            )
            stats["incidents_24h"] = recent_incidents
            
            # DB size (PostgreSQL only)
            try:
                size_result = s.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()))")).scalar()
                if size_result:
                    stats["database_size"] = size_result
            except:
                pass  # Not PostgreSQL or no permission
            
            # Oldest incident
            oldest = s.query(Incident.created_at).order_by(Incident.created_at).first()
            if oldest:
                stats["oldest_incident"] = oldest[0].isoformat() if oldest[0] else None
            
        except Exception as e:
            stats["error"] = str(e)
    
    return stats


# Optional: Schedule archival as background job (example)
def schedule_archival(interval_hours: int = 24):
    """
    Schedule automatic archival every N hours.
    Call this once at startup if you want automatic cleanup.
    """
    import threading
    import time
    
    def archival_loop():
        while True:
            try:
                result = archive_old_incidents()
                if result["archived_count"] > 0:
                    print(f"[ARCHIVE] Archived {result['archived_count']} incidents to {result['archive_file']}")
                time.sleep(interval_hours * 3600)
            except Exception as e:
                print(f"[ARCHIVE] Archival error: {e}")
                time.sleep(60)  # Retry after 1 minute
    
    if os.getenv("ENABLE_AUTO_ARCHIVAL", "0") == "1":
        thread = threading.Thread(target=archival_loop, daemon=True)
        thread.start()
        print(f"[ARCHIVE] Auto-archival enabled (every {interval_hours}h)")