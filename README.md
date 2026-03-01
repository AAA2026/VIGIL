# VIGIL

AI-powered surveillance platform for:
- violence detection
- crash detection
- people counting
- live camera wall + incident operations dashboard

Backend is Flask + SQLAlchemy + Alembic. Frontend is React + Vite.

## Quick Start

### One command (Windows PowerShell)
```powershell
.\start-vigil.ps1
```

### Manual start
Backend:
```powershell
pip install -r requirements.txt
python -m alembic upgrade head
python -m backend.app
```

Frontend:
```powershell
cd frontend
npm install
npm run dev
```

### Default URLs
- Backend API: `http://127.0.0.1:5000`
- Health: `http://127.0.0.1:5000/api/health`
- Frontend: `http://localhost:3000`

## Database Setup (Production)

- Set `DATABASE_URL`:
  - `postgresql+psycopg://user:pass@host:5432/vigil`
- Apply migrations:
  - `python -m alembic upgrade head`
- Check revision:
  - `python -m alembic current`

Important:
- `DB_AUTO_CREATE` defaults to `0` in production paths.
- Schema should be managed by Alembic migrations, not runtime table creation.
- Full DB guidance: [docs/DB_SETUP.md](docs/DB_SETUP.md)

## Configuration

Primary runtime configuration lives in [backend/config.py](backend/config.py):
- camera groups (`VIOLENCE_CAMERAS`, `CRASH_CAMERAS`)
- thresholds (`VIOLENCE_THRESHOLD`, `ACCIDENT_THRESHOLD`)
- model paths (`MODEL_PATHS`)

DB engine tuning env vars (optional):
- `DB_POOL_SIZE`
- `DB_MAX_OVERFLOW`
- `DB_POOL_TIMEOUT`
- `DB_POOL_RECYCLE`
- `DB_ECHO`

API runtime safety env vars:
- `CORS_ALLOWED_ORIGINS` (comma-separated; default local dev origins)
- `DEMO_AUTH_ENABLED` (`1`/`0`, default `1`)
- `MAX_UPLOAD_MB` (request body limit in MB, default `200`)

## File-by-File Guide (Main Files)

This section explains what each important project file actually does in runtime.

### Root

| File | Purpose |
|---|---|
| [start-vigil.ps1](start-vigil.ps1) | Launch script: validates tooling, installs deps if needed, runs migrations, starts backend + frontend. |
| [requirements.txt](requirements.txt) | Python dependency lock list for backend/runtime. |
| [alembic.ini](alembic.ini) | Alembic config entrypoint used by migration commands. |
| [pytest.ini](pytest.ini) | Pytest configuration. |
| [.env](.env) | Local environment variables (not committed for production secrets). |
| [README.md](README.md) | Main project documentation. |

### Backend API and App Wiring

| File | Purpose |
|---|---|
| [backend/app.py](backend/app.py) | Main Flask app: routes, health, metrics, auth demo endpoints, incident/report/demo APIs, websocket emits, simulator startup. |
| [backend/config.py](backend/config.py) | Static runtime configuration: camera groups, thresholds, default cameras, model path map. |
| [backend/__init__.py](backend/__init__.py) | Package marker for backend module imports. |

### Backend Database Layer

| File | Purpose |
|---|---|
| [backend/db/engine.py](backend/db/engine.py) | Creates SQLAlchemy engine/sessionmaker, handles URL normalization, pooling config, SQLite pragmas. |
| [backend/db/models.py](backend/db/models.py) | ORM models (currently `Incident`) with indexes/constraints and serializer (`to_dict`). |
| [backend/db/__init__.py](backend/db/__init__.py) | Exports DB helpers (`get_engine`, `get_sessionmaker`, `get_session`, `Base`, `Incident`). |

### Backend Services

| File | Purpose |
|---|---|
| [backend/services/camera_manager.py](backend/services/camera_manager.py) | Thread-safe camera state store + video rotation helpers + offline mode state. |
| [backend/services/camera_simulator.py](backend/services/camera_simulator.py) | Background simulator loop that rotates videos, calls inference, updates camera states, creates incidents with cooldowns. |
| [backend/services/incident_storage.py](backend/services/incident_storage.py) | Database CRUD/service layer for incidents (create/merge/list/ack/resolve/dispatch/stats). |
| [backend/services/incident_service.py](backend/services/incident_service.py) | Additional orchestration path for per-video detection pipelines. |
| [backend/services/demo_service.py](backend/services/demo_service.py) | Persists and updates demo booking requests in JSON storage. |
| [backend/services/camera_service.py](backend/services/camera_service.py) | Legacy/simple camera state helper kept for compatibility. |

### Backend AI Layer

| File | Purpose |
|---|---|
| [backend/ai/inference.py](backend/ai/inference.py) | Unified AI entrypoint. Routes to violence/crash detectors by camera role and attaches people count where applicable. |
| [backend/ai/violence_detector/inference.py](backend/ai/violence_detector/inference.py) | V6 TorchScript violence inference (frame extraction, preprocessing, threshold profiles, prediction payload). |
| [backend/ai/violence_detector/__init__.py](backend/ai/violence_detector/__init__.py) | Violence detector wrapper + fallback behavior if model loading fails. |
| [backend/ai/people_counter/yolov8.py](backend/ai/people_counter/yolov8.py) | YOLOv8 people counting inference integration. |
| [backend/ai/people_counter/__init__.py](backend/ai/people_counter/__init__.py) | Exports people counting function. |
| [backend/ai/crash_detector/__init__.py](backend/ai/crash_detector/__init__.py) | Crash model load + inference entrypoint and output normalization. |
| [backend/ai/crash_detector/model_architecture.py](backend/ai/crash_detector/model_architecture.py) | Crash model network definition. |
| [backend/ai/crash_detector/sampling.py](backend/ai/crash_detector/sampling.py) | Video frame sampling utility for crash model. |
| [backend/ai/crash_detector/transforms_setup.py](backend/ai/crash_detector/transforms_setup.py) | Crash model preprocessing transforms. |
| [backend/ai/retrainer.py](backend/ai/retrainer.py) | Simulated retraining pipeline endpoint backend (currently demo behavior). |

### Backend Utilities and Assets

| Path | Purpose |
|---|---|
| `backend/models/` | Active runtime model files (`violence_detector_v6_ts.pt`, config JSON, `yolov8n.pt`). |
| `backend/models/deprecated/` | Old model files kept for reference, not used by active inference path. |
| `backend/models/retrained/` | Output folder for retraining pipeline artifacts. |
| `backend/data/` | Local JSON and retraining sample media used by demo/retrain flows. |
| `backend/reports/` | Generated report JSON outputs. |
| [backend/utils/smoothing.py](backend/utils/smoothing.py) | Confidence smoothing helpers. |
| [backend/utils/video_utils.py](backend/utils/video_utils.py) | Video utility functions used by pipelines. |

### Migrations (Alembic)

| File | Purpose |
|---|---|
| [alembic/env.py](alembic/env.py) | Alembic runtime environment setup for offline/online migration execution. |
| [alembic/versions/20260215_01_create_incidents.py](alembic/versions/20260215_01_create_incidents.py) | Base incidents table migration (idempotent-safe). |
| [alembic/versions/20260301_02_add_incident_indexes.py](alembic/versions/20260301_02_add_incident_indexes.py) | Adds production query indexes on incidents table. |
| [alembic/versions/20260301_03_add_incident_status_constraint.py](alembic/versions/20260301_03_add_incident_status_constraint.py) | Adds status check constraint for production DBs (non-SQLite). |

### Frontend Main Runtime Files

| File | Purpose |
|---|---|
| [frontend/package.json](frontend/package.json) | Frontend scripts/dependencies (`dev`, `build`, `lint`). |
| [frontend/vite.config.ts](frontend/vite.config.ts) | Vite bundler config. |
| [frontend/src/main.tsx](frontend/src/main.tsx) | React app bootstrap (mount point + global CSS). |
| [frontend/src/App.tsx](frontend/src/App.tsx) | Router root (`/` landing page, `/app` main authenticated app shell). |
| [frontend/src/components/ModernSecurityLayout.tsx](frontend/src/components/ModernSecurityLayout.tsx) | Main application shell/nav + role-based view switching + live hooks integration. |
| [frontend/src/hooks/useLiveStatus.ts](frontend/src/hooks/useLiveStatus.ts) | Polls `/api/live-status` and controls offline mode API state. |
| [frontend/src/hooks/useRealtimeIncidents.tsx](frontend/src/hooks/useRealtimeIncidents.tsx) | Incident feed + websocket updates + incident actions. |
| [frontend/src/hooks/useIncidentWebSocket.ts](frontend/src/hooks/useIncidentWebSocket.ts) | Websocket hook for incident/camera stream events. |
| [frontend/src/utils/exportUtils.ts](frontend/src/utils/exportUtils.ts) | CSV/PDF/export helpers used by reporting UI flows. |
| [frontend/src/components/DVRCameraGrid.tsx](frontend/src/components/DVRCameraGrid.tsx) | Live camera grid view rendered in core dashboard. |
| [frontend/src/components/IncidentsView.tsx](frontend/src/components/IncidentsView.tsx) | Incident management UI. |
| [frontend/src/components/DispatchesView.tsx](frontend/src/components/DispatchesView.tsx) | Dispatch workflow UI for officers/security. |
| [frontend/src/components/SystemHealthView.tsx](frontend/src/components/SystemHealthView.tsx) | System status and model health dashboard UI. |
| [frontend/src/components/AIModelManagement.tsx](frontend/src/components/AIModelManagement.tsx) | AI model management panel UI. |
| [frontend/src/components/AIFeedbackSection.tsx](frontend/src/components/AIFeedbackSection.tsx) | Feedback/retrain operations UI integration. |
| [frontend/src/components/landing/LandingPage.tsx](frontend/src/components/landing/LandingPage.tsx) | Public landing page. |

Notes:
- `frontend/src/components/ui/*` and `frontend/src/components/landing/ui/*` are reusable UI primitives.
- `frontend/src/components/*` contains role views, dashboards, and modals.
- `frontend/src/data/*` contains static sample data used by specific panels.

### Tests

| File | Purpose |
|---|---|
| [tests/test_health.py](tests/test_health.py) | Backend health endpoint test. |
| [tests/test_incidents.py](tests/test_incidents.py) | Incident storage behavior tests (CRUD/status/edge cases). |
| [tests/test_db_schema.py](tests/test_db_schema.py) | Ensures incident indexes exist. |
| [tests/test_db_engine.py](tests/test_db_engine.py) | Engine/session URL normalization and binding consistency tests. |

## Run Quality Checks

Backend tests:
```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Migration state:
```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
```

Frontend quality:
```powershell
cd frontend
npm run lint
npm run build
```

## Current Known Production Gaps

- Auth is still demo-level (hardcoded users/plain password flow). You can disable the demo endpoints via `DEMO_AUTH_ENABLED=0` and replace with a real auth system.
- Retraining endpoint currently simulates training; wire it to a real training pipeline before production.
- Flask builtin server is for development; use gunicorn/uvicorn with proper reverse proxy in production.
