# Vigil Setup Guide

## Project Structure

```
vigil/
├── backend/                    # Flask Python API
│   ├── ai/                     # AI/ML models
│   │   ├── models/             # Pre-trained model files
│   │   ├── inference.py        # Model inference pipeline
│   │   ├── violence_model.py
│   │   └── accident_model.py
│   ├── db/                     # Database layer
│   │   ├── models.py           # SQLAlchemy ORM models
│   │   ├── bootstrap.py        # Database initialization
│   │   ├── session.py          # DB session management
│   │   └── engine.py           # Connection setup
│   ├── services/               # Business logic
│   │   ├── camera_simulator.py # Video rotation
│   │   ├── incident_service.py # Incident handling
│   │   ├── camera_manager.py   # Camera management
│   │   └── incident_storage.py # Database queries
│   ├── app.py                  # Flask entry point
│   ├── config.py               # Configuration
│   └── __init__.py
├── frontend/                   # React Vite dashboard
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── hooks/              # Custom hooks
│   │   ├── utils/              # Utility functions
│   │   ├── styles/             # CSS styling
│   │   ├── App.tsx             # Main component
│   │   └── main.tsx            # Entry point
│   ├── public/                 # Static assets
│   ├── index.html              # HTML template
│   ├── vite.config.ts          # Vite configuration
│   ├── tsconfig.json           # TypeScript config
│   ├── package.json            # NPM dependencies
│   ├── Dockerfile              # Production image
│   └── nginx.conf              # Nginx reverse proxy
├── config/                     # Configuration files
│   ├── docker-compose.yml      # Development containers
│   ├── docker-compose.prod.yml # Production stack
│   ├── .env.production         # Production secrets template
│   └── k8s/                    # Kubernetes manifests (optional)
├── data/                       # Runtime data
│   └── videos/                 # Video files
│       ├── violence/
│       ├── crash/
│       ├── no_violence/
│       └── no_crash/
├── docs/                       # Documentation
│   ├── SETUP.md               # This file
│   ├── DEPLOYMENT.md          # Deploy guide
│   └── API.md                 # API reference
├── scripts/                   # Utility scripts
│   └── start.ps1              # Startup script
├── .env                       # Development environment
├── .env.example               # Template
├── .dockerignore              # Docker build exclusions
├── .gitignore                 # Git exclusions
├── Dockerfile                 # Backend image
├── docker-compose.yml         # Quick start (symlink to config/)
├── requirements.txt           # Python packages
├── README.md                  # Project overview
└── LICENSE                    # License
```

---

## Prerequisites

### System Requirements
- **OS**: Windows 10+, macOS 10.14+, Ubuntu 18.04+
- **CPU**: 2+ cores recommended
- **RAM**: 4GB minimum (8GB recommended)
- **Disk**: 10GB free space

### Required Software

#### Windows
```powershell
# Verify Python
python --version  # 3.11+

# Verify Node.js
node --version    # 18+

# Verify Docker
docker --version  # 20.10+

# Verify PostgreSQL (if not using Docker)
psql --version    # 14+
```

#### macOS
```bash
brew install python@3.11
brew install node
brew install docker
brew install postgresql@14
```

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv
sudo apt install nodejs npm
sudo apt install docker.io docker-compose
sudo apt install postgresql-14
```

---

## Installation

### 1. Clone Repository
```bash
git clone https://github.com/your-org/vigil.git
cd vigil
```

### 2. Install Backend Dependencies
```bash
# Create virtual environment
python -m venv venv

# Activate
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### 3. Install Frontend Dependencies
```bash
cd frontend
npm install
cd ..
```

### 4. Configure Environment

```bash
# Copy development template
cp .env.example .env

# Edit .env with your settings
# Development uses localhost:5432 by default
```

### 5. Start Database

```bash
# Option A: Docker (recommended)
docker compose -f config/docker-compose.yml up -d postgres

# Option B: Local PostgreSQL
createdb vigil
```

### 6. Initialize Database

```bash
# Backend will auto-create tables on first run
# Or manually:
python -c "from backend.db.bootstrap import init_db_and_seed; init_db_and_seed()"
```

---

## Running Locally

### Terminal 1: Backend
```bash
# Activate virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Set environment
export DATABASE_URL="postgresql+psycopg://vigil:vigil@localhost:5432/vigil"

# Run
python -m backend.app

# Expected output:
# 🚀 Starting VIGIL Backend on http://127.0.0.1:5000
# ✅ System ready - cameras are now 'live'
```

### Terminal 2: Frontend
```bash
cd frontend
npm run dev

# Expected output:
# ➜  Local:   http://localhost:5173/
# ➜  press h to show help
```

### Terminal 3: Monitor Database
```bash
docker exec -it vigil_postgres psql -U vigil vigil

# Useful queries:
SELECT COUNT(*) FROM incident;
SELECT * FROM camera;
```

---

## Accessing the Application

| Service | URL | Port |
|---------|-----|------|
| **Dashboard** | http://localhost:5173 | 5173 |
| **API** | http://localhost:5000 | 5000 |
| **Database** | localhost:5432 | 5432 |

### Login Credentials

| Email | Password | Role |
|-------|----------|------|
| admin@vigil.com | admin123 | Admin |
| officer@vigil.com | officer123 | Officer |
| security@vigil.com | security123 | Security |

---

## Common Tasks

### Adding Videos

#### Method 1: File System
Place `.mp4` files in `data/videos/` subdirectories:
```
data/videos/
├── violence/          # Violence examples
├── crash/             # Crash examples  
├── no_violence/       # Normal surveillance
└── no_crash/          # Normal traffic
```

Camera simulator auto-discovers files and rotates every 5 seconds.

#### Method 2: Database
```python
from backend.db.session import db_session
from backend.db.models import VideoFile

with db_session() as session:
    video = VideoFile(
        camera_id="CAM-001",
        filename="fight.mp4",
        file_path="/path/to/fight.mp4",
        file_size=52428800,
        video_type="violence",
        uploaded_by="admin@vigil.com"
    )
    session.add(video)
    session.commit()
```

### Database Queries

```python
from backend.db.session import db_session
from backend.db.models import Incident, Camera

# Get recent incidents
with db_session() as session:
    incidents = session.query(Incident)\
        .filter(Incident.type == "violence")\
        .order_by(Incident.timestamp.desc())\
        .limit(10)\
        .all()

# Count by camera
with db_session() as session:
    from sqlalchemy import func
    counts = session.query(
        Incident.camera_id,
        func.count(Incident.external_id)
    ).group_by(Incident.camera_id).all()
```

### Clearing Demo Data

```bash
# API endpoint
curl -X POST http://localhost:5000/api/incidents/clear

# Or to see incidents before clear
curl http://localhost:5000/api/incidents | jq
```

### Restarting Services

```bash
# Stop all
docker compose -f config/docker-compose.yml down

# Start all
docker compose -f config/docker-compose.yml up -d

# View logs
docker compose -f config/docker-compose.yml logs -f backend
```

---

## Troubleshooting

### Backend won't start

```bash
# Check if port 5000 is in use
lsof -i :5000  # macOS/Linux
netstat -ano | findstr :5000  # Windows

# Kill process if needed
kill -9 <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows
```

### Database connection failed

```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Test connection
psql -h localhost -U vigil -d vigil -c "SELECT 1"

# Check credentials
echo $DATABASE_URL
```

### Frontend build issues

```bash
# Clear node_modules and reinstall
rm -rf frontend/node_modules
cd frontend && npm install

# Update vite config
npm run build

# Check for TypeScript errors
npm run type-check
```

### Port conflicts

```bash
# Change ports in .env or directly
# Frontend: vite.config.ts (server.port)
# Backend: app.py (port parameter)
# Database: docker-compose.yml
```

---

## Development Tips

### Hot Reload
- **Frontend**: Vite provides hot reload on file changes
- **Backend**: Use Flask debug mode (set FLASK_DEBUG=1)

### Database Migrations
```bash
# Export schema
pg_dump -h localhost -U vigil --schema-only vigil > schema.sql

# Apply changes
psql -h localhost -U vigil vigil < schema.sql
```

### Testing Backend
```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest tests/

# With coverage
pytest --cov=backend tests/
```

### Testing Frontend
```bash
cd frontend

# Unit tests
npm run test

# E2E tests
npm run test:e2e

# Build production
npm run build
```

---

## Performance Optimization

### Backend
- Use connection pooling (SQLAlchemy)
- Enable query caching
- Compress JSON responses (Flask-Compress)

### Frontend
- Code splitting in Vite
- Image optimization
- Service worker for offline

### Database
- Index frequently queried columns (timestamp, camera_id)
- Archive old incidents
- Vacuum and analyze regularly

```sql
-- Optimize database
VACUUM ANALYZE;

-- Check slow queries
EXPLAIN ANALYZE SELECT * FROM incident_huge_query;

-- Create indexes
CREATE INDEX idx_incident_timestamp ON incident(timestamp DESC);
CREATE INDEX idx_incident_camera_type ON incident(camera_id, type);
```

---

## Next Steps

1. **Read** [DEPLOYMENT.md](DEPLOYMENT.md) for production setup
2. **Read** [API.md](API.md) for endpoint documentation
3. **Configure** AI thresholds in `backend/config.py`
4. **Add** your own videos to `data/videos/`
5. **Deploy** using Docker or cloud platform

