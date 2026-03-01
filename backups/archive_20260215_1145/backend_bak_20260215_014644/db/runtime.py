import threading
from datetime import datetime
from backend.db.session import db_session
from backend.db.models import DemoRun

_lock = threading.Lock()
_current_run_id = None

def get_or_create_active_run_id(name: str = "Demo Run") -> str:
    global _current_run_id
    with _lock:
        if _current_run_id:
            return _current_run_id

        with db_session() as s:
            active = s.query(DemoRun).filter(DemoRun.is_active == True, DemoRun.ended_at.is_(None)).order_by(DemoRun.started_at.desc()).first()
            if active:
                _current_run_id = active.id
                return _current_run_id

            run = DemoRun(name=name, is_active=True, started_at=datetime.utcnow())
            s.add(run)
            s.flush()
            _current_run_id = run.id
            return _current_run_id

def start_new_run(name: str = "Demo Run") -> str:
    """End current active run (if any) and start a new run."""
    global _current_run_id
    with _lock:
        with db_session() as s:
            active = s.query(DemoRun).filter(DemoRun.is_active == True, DemoRun.ended_at.is_(None)).order_by(DemoRun.started_at.desc()).first()
            if active:
                active.ended_at = datetime.utcnow()
                active.is_active = False
                s.add(active)

            run = DemoRun(name=name, is_active=True, started_at=datetime.utcnow())
            s.add(run)
            s.flush()
            _current_run_id = run.id
            return _current_run_id

def set_active_run_id(run_id: str):
    global _current_run_id
    with _lock:
        _current_run_id = run_id
