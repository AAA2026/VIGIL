# Vigil — Enterprise AI-Powered Surveillance Platform

An advanced surveillance system featuring real-time AI detection (violence, crashes), PostgreSQL persistence, and containerized cloud-ready architecture. Built for security professionals, law enforcement, and enterprises.

**Status:** Production-Ready | **License:** MIT | **Maintained:** ✓

---

## 🎯 Quick Start (2 minutes)

```bash
# 1. Clone repository
git clone https://github.com/your-org/vigil.git && cd vigil

# 2. Run setup script (checks dependencies, installs packages)
.\scripts\start.ps1   # Windows PowerShell

# 3. In separate terminals, start services:
# Terminal 1 - Backend
$env:DATABASE_URL="postgresql+psycopg://vigil:vigil@localhost:5432/vigil"
python -m backend.app

# Terminal 2 - Frontend 
cd frontend && npm run dev

# 4. Open dashboard
# http://localhost:5173 | use your created credentials
```

**✅ All services running!** Incidents appear in real-time as cameras detect events.

---

## 📋 Features

### AI Detection Engine
- **Violence Detection**: MobileNet-CLIP + YOLOv8 People Counter
- **Crash Detection**: MobileNetV2-LSTM specialized model
- **Real-time**: Sub-second inference on camera feeds
- **Confidence Scores**: Weighted confidence for each detection

### Enterprise Dashboard
- **Live Multi-Camera Grid**: 12+ simultaneous camera feeds
- **Real-time Alerts**: WebSocket-based incident notifications
- **Incident Management**: Acknowledge, assign, resolve incidents
- **Audit Trail**: Complete action history with timestamps
- **Report Generation**: PDF/JSON incident summaries

### Database Layer
- **PostgreSQL**: Enterprise-grade persistence
- **Auto Schema**: Tables created automatically on startup
- **Data Retention**: All incidents retained for evidence/legal
- **Demo Runs**: Group incidents logically for presentations

### Cloud-Ready
- **Docker**: Multi-stage builds for production optimization
- **Kubernetes**: Ready with manifests (in `/config/k8s/`)
- **Scalable**: Load balancing for multiple backends
- **Monitoring**: Health checks, logging, alerting built-in

---

## 🏗️ Project Structure

```
vigil/
├── backend/                    # Python Flask API
│   ├── ai/
│   │   ├── models/            # Pre-trained .pt/.pth files
│   │   ├── inference.py       # ML pipeline
│   │   ├── violence_model.py
│   │   └── accident_model.py
│   ├── db/                    # Database layer
│   │   ├── models.py          # SQLAlchemy ORM
│   │   ├── bootstrap.py       # Init & seed
│   │   └── engine.py          # Connection
│   ├── services/              # Business logic
│   │   ├── camera_simulator.py
│   │   ├── incident_service.py
│   │   └── incident_storage.py
│   ├── app.py                 # Flask entry point
│   └── config.py              # Configuration
├── frontend/                  # React/TypeScript dashboard
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── utils/
│   │   └── App.tsx
│   ├── Dockerfile             # Production image
│   ├── nginx.conf             # Reverse proxy
│   └── vite.config.ts
├── config/                    # Deployment configs
│   ├── docker-compose.yml     # Dev containers
│   ├── docker-compose.prod.yml# Prod stack
│   ├── .env.production        # Secrets template
│   └── k8s/                   # Kubernetes manifests
├── data/                      # Runtime data
│   └── videos/
│       ├── violence/
│       ├── crash/
│       ├── no_violence/
│       └── no_crash/
├── docs/                      # Documentation
│   ├── SETUP.md              # Getting started
│   ├── DEPLOYMENT.md         # Deploy to cloud
│   └── API.md                # API reference
├── scripts/                   # Utility scripts
│   └── start.ps1             # Setup script
├── Dockerfile                 # Backend production image
├── requirements.txt          # Python dependencies
├── .env.example              # Template
├── .dockerignore             # Docker optimizations
└── README.md                 # This file
```

---

## 🚀 Installation

### Prerequisites
- **Python** 3.11+
- **Node.js** 18+
- **Docker** & Docker Compose
- **PostgreSQL** 14+ (or use Docker)

### Installation Steps

1. **Clone Repository**
   ```bash
   git clone https://github.com/your-org/vigil.git
   cd vigil
   ```

2. **Run Setup Script** (auto-installs dependencies)
   ```powershell
   # Windows
   .\scripts\start.ps1
   
   # macOS/Linux
   bash scripts/start.sh  # (create if needed)
   ```

3. **Or Manual Setup**
   ```bash
   # Python
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   
   # Frontend
   cd frontend && npm install && cd ..
   
   # Database
   docker compose -f config/docker-compose.yml up -d postgres
   ```

---

## 📖 Usage

### Local Development

**Terminal 1: Backend API**
```bash
$env:DATABASE_URL="postgresql+psycopg://vigil:vigil@localhost:5432/vigil"
python -m backend.app
# 🚀 Running on http://localhost:5000
```

**Terminal 2: Frontend Dashboard**
```bash
cd frontend
npm run dev
# ➜  http://localhost:5173
```

**Terminal 3: Database (optional)**
```bash
docker exec -it vigil_postgres psql -U vigil vigil
SELECT COUNT(*) FROM incident;
```

### Production Deployment

**Docker Compose** (recommended for testing production build)
```bash
docker compose -f config/docker-compose.prod.yml up -d
```

**Kubernetes** (for scaling)
```bash
kubectl apply -f config/k8s/
```

**Cloud Platforms** (see `docs/DEPLOYMENT.md`)
- Azure Container Instances, AKS
- AWS ECS, EKS
- Google Cloud Run

---

## 🔑 Default Credentials

| Email | Password | Role |
|-------|----------|------|
| admin@vigil.com | admin123 | Admin (full access) |
| officer@vigil.com | officer123 | Officer (read incidents) |
| security@vigil.com | security123 | Security (assign) |

⚠️ **Change these in production!** See `.env.production` template.

---

## 💾 Database Management

### Adding Videos

**Method 1: File System (Automatic)**
```
data/videos/
├── violence/        # Violence examples
├── crash/           # Crash examples
├── no_violence/     # Normal surveillance
└── no_crash/        # Normal traffic
```
Place `.mp4` files, restart backend, camera simulator auto-discovers.

**Method 2: Python**
```python
from backend.db.session import db_session
from backend.db.models import VideoFile

with db_session() as session:
    video = VideoFile(
        camera_id="CAM-001",
        filename="fight.mp4",
        file_path="data/videos/violence/fight.mp4",
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
from backend.db.models import Incident

# Recent violent incidents
with db_session() as session:
    incidents = session.query(Incident)\
        .filter(Incident.type == "violence")\
        .order_by(Incident.timestamp.desc())\
        .limit(10).all()
    
    for inc in incidents:
        print(f"{inc.external_id}: {inc.confidence*100:.1f}%")
```

### Backup & Restore

```bash
# Backup
docker exec vigil_postgres pg_dump -U vigil vigil > backup.sql

# Restore
docker exec -i vigil_postgres psql -U vigil vigil < backup.sql
```

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Database health check |
| `/api/incidents` | GET | List incidents (filterable) |
| `/api/incidents/{id}` | GET | Incident details |
| `/api/incidents/{id}/ack` | POST | Acknowledge incident |
| `/api/incidents/clear` | POST | Clear incidents, new run |
| `/api/cameras` | GET | List cameras |
| `/api/reports/incidents` | GET | Generate report |
| `/videos/{filename}` | GET | Stream video |

See **`docs/API.md`** for full reference.

---

## 🐳 Docker Deployment

### Development
```bash
docker compose -f config/docker-compose.yml up -d
```

### Production
```bash
# Build images
docker compose -f config/docker-compose.prod.yml build

# Start stack
docker compose -f config/docker-compose.prod.yml up -d

# Logs
docker compose -f config/docker-compose.prod.yml logs -f backend
```

### Custom Environment
```bash
cp .env.example .env
# Edit .env with your settings
docker compose -f config/docker-compose.yml up -d
```

---

## ⚙️ Configuration

### AI Thresholds (`backend/config.py`)
```python
VIOLENCE_THRESHOLD = 0.70      # 70% confidence to flag
ACCIDENT_THRESHOLD = 0.30      # 30% confidence to flag
```

### Database Logging
```env
DB_ECHO=0   # Production (no logs)
DB_ECHO=1   # Development (SQL logging)
```

### Camera List
Edit `backend/config.py` to add/remove cameras:
```python
DEFAULT_CAMERAS = ["CAM-001", "CAM-002", ...]
```

---

## 📊 Monitoring & Scaling

### Health Endpoints
```bash
# Backend
curl http://localhost:5000/api/health

# Check database
curl http://localhost:5000/api/health | jq '.db'
```

### Horizontal Scaling
```yaml
# config/docker-compose.prod.yml
services:
  backend:
    deploy:
      replicas: 3  # Scale to 3 instances
```

### Logging & Alerting
- Docker logs: `docker logs -f vigil_backend`
- Centralized: Push to Datadog, New Relic, Splunk
- Monitoring: Prometheus, Grafana (optional)

---

## 🛠️ Troubleshooting

### Backend won't start
```bash
# Check port 5000
netstat -ano | findstr :5000

# Check database
docker exec vigil_postgres pg_isready -U vigil
```

### Frontend build issues
```bash
cd frontend
rm -rf node_modules
npm install
npm run build
```

### Database problems
```bash
# Connect directly
docker exec -it vigil_postgres psql -U vigil vigil

# Check tables
\dt

# Restart container
docker restart vigil_postgres
```

---

## 📚 Documentation

- **[SETUP.md](docs/SETUP.md)** — Detailed installation & development
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** — Cloud & production setup
- **[API.md](docs/API.md)** — Complete API reference

---

## 🔒 Security Best Practices

1. **Change Default Passwords** before production
2. **Use Strong Secrets** — Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`
3. **Enable HTTPS** — Use Let's Encrypt in production
4. **Database Access** — Restrict to VPC/private networks
5. **API Keys** — Implement authentication for external integrations
6. **Backups** — Schedule daily automated backups
7. **Updates** — Keep dependencies updated (`pip-audit`, `npm audit`)

---

## 💡 Common Tasks

### Clear Incidents for Demo
```bash
curl -X POST http://localhost:5000/api/incidents/clear
```

### Export All Incidents
```bash
curl http://localhost:5000/api/incidents?limit=1000 | jq > incidents.json
```

### Check System Status
```bash
docker compose -f config/docker-compose.yml ps
docker compose -f config/docker-compose.yml stats
```

### Restart All Services
```bash
docker compose -f config/docker-compose.yml restart
```

---

## 🚢 Deployment Targets

| Platform | Guide | Time |
|----------|-------|------|
| Docker Compose | [DEPLOYMENT.md](docs/DEPLOYMENT.md) | 5 min |
| Azure AKS | [DEPLOYMENT.md](docs/DEPLOYMENT.md) | 20 min |
| AWS ECS | [DEPLOYMENT.md](docs/DEPLOYMENT.md) | 20 min |
| Google Cloud Run | [DEPLOYMENT.md](docs/DEPLOYMENT.md) | 10 min |

---

## 📈 Performance

- **Backend**: Flask + Gunicorn (WSGI)
- **Frontend**: Vite + SPA (optimized bundles)
- **Database**: PostgreSQL with connection pooling
- **Inference**: Sub-second on modern hardware
- **Real-time**: WebSocket for live updates

**Scalability**: Load balance multiple backends, separate read replicas for reporting.

---

## 🤝 Contributing

1. Fork repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

---

## 📝 License

MIT License — See LICENSE file for details

---

## 📞 Support

- **Issues**: GitHub Issues
- **Docs**: Read [docs/](docs/)
- **Email**: support@vigil.example.com (customize)

---

## 🎓 Key Technologies

- **Backend**: Python, Flask, PostgreSQL
- **Frontend**: React, TypeScript, Vite
- **AI/ML**: PyTorch, YOLOv8, MobileNet
- **DevOps**: Docker, Docker Compose, Kubernetes
- **Real-time**: Socket.IO WebSockets
- **Cloud**: Azure, AWS, GCP ready

---

## 🎯 Roadmap

- [ ] Multi-tenant support
- [ ] Advanced analytics dashboard
- [ ] Custom model training UI
- [ ] Mobile app (iOS/Android)
- [ ] RTSP stream ingestion
- [ ] ML model serving
- [ ] API rate limiting
- [ ] OIDC/SAML authentication

---

**Made for security professionals who need reliable, scalable threat detection.** 🛡️

Last Updated: February 8, 2026 | Version: 2.0
