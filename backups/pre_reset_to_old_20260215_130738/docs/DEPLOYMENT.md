# Vigil Deployment Guide

## Table of Contents
1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [Production Deployment](#production-deployment)
4. [Database Management](#database-management)
5. [Scaling & Monitoring](#scaling-monitoring)

---

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Docker & Docker Compose

### Quick Start

```bash
# 1. Start PostgreSQL
docker compose -f config/docker-compose.yml up -d

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Set development environment
export DATABASE_URL="postgresql+psycopg://vigil:vigil@localhost:5432/vigil"

# 4. Start backend (Terminal 1)
python -m backend.app

# 5. Start frontend (Terminal 2)
cd frontend && npm run dev

# 6. Access dashboard
# Frontend: http://localhost:5173 (Vite dev)
# Backend API: http://localhost:5000
```

---

## Docker Deployment

### Development Docker Setup

```bash
# Start all services
docker compose -f config/docker-compose.yml up -d

# View logs
docker compose -f config/docker-compose.yml logs -f backend
docker compose -f config/docker-compose.yml logs -f postgres

# Stop all services
docker compose -f config/docker-compose.yml down
```

### Production Docker Composition

```bash
# Start full production stack
docker compose -f config/docker-compose.prod.yml up -d

# Scale backend (if using Kubernetes)
# Edit docker-compose.prod.yml and set replicas
```

---

## Production Deployment

### Azure Deployment

#### Option 1: Azure Container Instances
```bash
# Create resource group
az group create --name vigil-rg --location eastus

# Build and push images
docker build -t vigilacr.azurecr.io/vigil-backend:latest .
docker push vigilacr.azurecr.io/vigil-backend:latest

# Deploy using Azure CLI
az container create \
  --resource-group vigil-rg \
  --name vigil-app \
  --image vigilacr.azurecr.io/vigil-backend:latest \
  --cpu 2 --memory 4
```

#### Option 2: Azure Kubernetes Service (AKS)
```bash
# Create AKS cluster
az aks create -g vigil-rg -n vigil-aks --node-count 3

# Get credentials
az aks get-credentials -n vigil-aks -g vigil-rg

# Deploy using Kubernetes manifests (in production/)
kubectl apply -f config/k8s/
```

### AWS Deployment

#### Using ECS Fargate
```bash
# Create ECR repository
aws ecr create-repository --repository-name vigil-backend

# Build and push
docker build -t vigil-backend:latest .
docker tag vigil-backend:latest <aws-account>.dkr.ecr.<region>.amazonaws.com/vigil-backend:latest
docker push <aws-account>.dkr.ecr.<region>.amazonaws.com/vigil-backend:latest

# Deploy with CloudFormation or Terraform
terraform apply -var-file=production.tfvars
```

### GCP Deployment

#### Using Cloud Run
```bash
# Build and deploy
gcloud run deploy vigil-backend \
  --source . \
  --platform managed \
  --region us-central1 \
  --set-env-vars DATABASE_URL=$DB_URL
```

---

## Database Management

### PostgreSQL Backup & Restore

```bash
# Backup
docker exec vigil_postgres pg_dump -U vigil vigil > backup-$(date +%Y%m%d-%H%M%S).sql

# Restore
docker exec -i vigil_postgres psql -U vigil vigil < backup-20260208-120000.sql

# Automated backups (cron job)
0 2 * * * docker exec vigil_postgres pg_dump -U vigil vigil > /backups/vigil-$(date +\%Y\%m\%d).sql
```

### Database Migrations

```bash
# Connect to database
docker exec -it vigil_postgres psql -U vigil vigil

# Add new incident type
ALTER TABLE incident ADD COLUMN fire_score FLOAT;
ALTER TABLE incident ADD COLUMN vehicle_count INT;

# Export schema
docker exec vigil_postgres pg_dump -U vigil --schema-only vigil > schema.sql
```

### Monitoring Database

```sql
-- Check database size
SELECT pg_size_pretty(pg_database_size('vigil'));

-- Check active connections
SELECT datname, usename, application_name, state FROM pg_stat_activity;

-- Check slow queries (if needed)
SELECT query, calls, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;
```

---

## Scaling & Monitoring

### Horizontal Scaling (Multiple Backends)

```yaml
# config/docker-compose.prod.yml
services:
  backend:
    deploy:
      replicas: 3  # Three backend instances
  
  load-balancer:
    image: nginx:latest
    ports:
      - "5000:5000"
    volumes:
      - ./config/nginx-lb.conf:/etc/nginx/nginx.conf:ro
```

### Monitoring with Prometheus

```yaml
# config/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'vigil-backend'
    static_configs:
      - targets: ['localhost:5000']
  
  - job_name: 'postgresql'
    static_configs:
      - targets: ['localhost:9187']
```

### Logging Stack (ELK)

```bash
# Start with logging enabled
docker compose -f config/docker-compose.prod.yml up -d

# Stream logs
docker logs -f vigil_backend

# Integration with centralized logging (e.g., Datadog, New Relic)
# Set environment variables for agent configuration
```

---

## Health Checks & Validations

```bash
# Backend health
curl http://localhost:5000/api/health

# Database connectivity
curl http://localhost:5000/api/health | jq '.db'

# Frontend accessibility
curl -I http://localhost:3000

# WebSocket connection
wscat -c ws://localhost:5000/socket.io/?transport=websocket
```

---

## CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/deploy.yml
name: Deploy Vigil

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker images
        run: docker compose -f config/docker-compose.prod.yml build
      - name: Push to registry
        run: docker compose -f config/docker-compose.prod.yml push
      - name: Deploy to production
        run: |
          # Your deployment commands here
          kubectl apply -f config/k8s/
```

---

## Security Best Practices

1. **Database Passwords**: Use strong, unique passwords in production
2. **Environment Variables**: Never commit `.env` files with secrets
3. **Network**: Use VPC and security groups to restrict access
4. **SSL/TLS**: Use HTTPS in production
5. **Secrets Management**: Use AWS Secrets Manager, Azure Key Vault, or similar
6. **Regular Backups**: Schedule daily backups and test restoration
7. **Update Dependencies**: Keep all packages updated

```bash
# Generate secure password
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Scan for vulnerabilities
npm audit
pip-audit
```

---

## Troubleshooting

### Container won't start
```bash
docker logs vigil_backend
docker logs vigil_postgres
```

### Database connection fails
```bash
# Test connection
docker exec vigil_postgres psql -U vigil -d vigil -c "SELECT 1"

# Check environment variables
docker inspect vigil_backend | grep Environment
```

### Out of memory
```bash
# Check resource usage
docker stats vigil_backend vigil_postgres

# Increase limits in docker-compose.prod.yml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

---

## Rollback Procedure

```bash
# If deployment fails, use previous image
docker pull vigilacr.azurecr.io/vigil-backend:v1.0.0
docker tag vigilacr.azurecr.io/vigil-backend:v1.0.0 vigil-backend:latest
docker compose -f config/docker-compose.prod.yml up -d
```

---

## Support & Monitoring

- **Backend Logs**: Check `docker logs` or centralized logging service
- **Database Monitoring**: Use PostgreSQL's built-in tools or cloud provider dashboard
- **Uptime Monitoring**: Configure health check endpoints with external service
- **Alerting**: Set up alerts for failed health checks, high CPU/memory usage, database errors

