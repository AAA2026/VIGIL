# Vigil Production Database Guide

## Table of Contents
1. [Database Comparison](#database-comparison)
2. [Connection Pooling](#connection-pooling)
3. [Performance Optimization](#performance-optimization)
4. [Data Retention & Archival](#data-retention--archival)
5. [Backup Strategy](#backup-strategy)
6. [Monitoring](#monitoring)
7. [Migration Path](#migration-path)

---

## Database Comparison

| Criteria | SQLite (Dev) | PostgreSQL (Prod) |
|----------|-----------|-------------------|
| **Best For** | Local dev, demos | Enterprise, high volume |
| **Connections** | Single thread | 100+ concurrent |
| **Data Size** | <1GB | Unlimited |
| **Queries/sec** | <100 | 10,000+ |
| **Backup Strategy** | File copy | pg_dump, replication |
| **Scaling** | Read-only replicas | Read replicas, sharding |
| **Recommendation** | ✅ Vigil default | ✅ Use for production |

---

## Connection Pooling

The updated `engine.py` now includes proper connection pooling:

```python
# Automatically configured based on DATABASE_URL
DB_POOL_SIZE=20        # Connections to keep open
DB_MAX_OVERFLOW=10     # Allow 10 extra when needed (total 30)
DB_POOL_RECYCLE=3600   # Recycle stale connections after 1 hour
DB_POOL_PRE_PING=1     # Test connection before use
```

### Why This Matters
- **Without pooling**: Each request creates a new connection → connection exhaustion → slow dashboards
- **With pooling**: Connections reused → 10-100x faster response times

### Sizing for Your Deployment

```python
# Small deployment (< 100 users)
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=5

# Medium deployment (100-1000 users)
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

# Large deployment (1000+ users)
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=20
```

### Connection Monitoring

Monitor PostgreSQL connections:

```bash
# Check active connections
docker exec vigil_postgres psql -U vigil -c "
  SELECT datname, usename, count(*) FROM pg_stat_activity 
  GROUP BY datname, usename;
"

# Check max connections limit
docker exec vigil_postgres psql -U vigil -c "SHOW max_connections;"
```

If you see:
```
 datname | usename | count
---------|---------|-------
 vigil   | vigil   | 30
```

And `max_connections` is only `100`, then increase both:

```bash
# In docker-compose.prod.yml PostgreSQL service:
environment:
  POSTGRES_INIT_ARGS: "-c max_connections=200"
```

---

## Performance Optimization

### 1. Database Indexes (Added)

Composite indexes now created automatically for common queries:

```python
# Deduplication lookup: (run_id, camera_id, type, timestamp DESC)
idx_incident_dedup

# Recent incidents lookup: (status, timestamp DESC)
idx_incident_recent

# Camera timeline lookup: (camera_id, timestamp DESC)
idx_incident_camera_time

# Type timeline lookup: (type, timestamp DESC)
idx_incident_type_time
```

### 2. Query Optimization

Before:
```python
# SLOW: Full table scan
incidents = s.query(Incident).filter(Incident.timestamp > cutoff).all()
```

After:
```python
# FAST: Uses idx_incident_recent + idx_incident_camera_time
incidents = (
    s.query(Incident)
    .filter(Incident.camera_id == camera_id)
    .filter(Incident.timestamp > cutoff)
    .order_by(Incident.timestamp.desc())
    .limit(100)
    .all()
)
```

### 3. Check Index Health

```sql
-- See which indexes are unused
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;

-- See index size
SELECT indexname, pg_size_pretty(pg_relation_size(indexrelname))
FROM pg_indexes
WHERE tablename = 'incident'
ORDER BY pg_relation_size(indexrelname) DESC;
```

---

## Data Retention & Archival

### Problem: Unbounded Growth

Without archival, your incident table grows:
- 1000 incidents/day × 365 days = **365K incidents**
- At ~2KB/incident = **730 MB** just for incidents
- Queries get slower as table grows

### Solution: Automatic Archival

New `backend/db/retention.py` module provides:

```python
# Archive incidents > 30 days old
result = archive_old_incidents(days_old=30)
# Returns:
# {
#   "archived_count": 15420,
#   "deleted_count": 15420,
#   "archive_file": "/data/archives/incidents_archive_20260208_120000.json"
# }

# Schedule automatic archival
ENABLE_AUTO_ARCHIVAL=1  # In .env.production
```

### Manual Archival (API Endpoint)

Add this to `backend/app.py` to expose as REST API:

```python
@app.route("/api/admin/archive-incidents", methods=["POST"])
def api_archive_incidents():
    """Archive old incidents (admin only)."""
    # TODO: Add auth check
    days = request.json.get("days", 30)
    result = archive_old_incidents(days_old=days)
    emit_system_event("incidents_archived", result)
    return jsonify(result)
```

### Archive File Format

Original incidents exported as JSON before deletion:

```json
[
  {
    "internal_id": 12345,
    "external_id": "inc-abc123",
    "camera_id": "CAM-042",
    "type": "violence",
    "confidence": 0.87,
    "timestamp": "2026-01-08T12:00:00",
    "status": "resolved",
    "actions_count": 3,
    "archived_at": "2026-02-08T12:00:00"
  },
  ...
]
```

### Long-Term Storage

For legal/audit requirements, move archives to cold storage:

```bash
# Daily cron job: Archive to S3/Azure Blob Storage
0 2 * * * aws s3 sync /data/archives s3://vigil-archives/$(date +%Y/%m)/ --delete

# Or Azure
0 2 * * * az storage blob upload-batch -s /data/archives -d vigil-archives --account-name vigilstorage
```

---

## Backup Strategy

### Daily Backups

```bash
# docker-compose.prod.yml: Add backup service
services:
  postgres-backup:
    image: postgres:16-alpine
    container_name: vigil_backup
    environment:
      PGPASSWORD: ${DB_PASSWORD}
    volumes:
      - ./backups:/backups
      - /etc/localtime:/etc/localtime:ro
    command: |
      bash -c 'while true; do
        pg_dump -h postgres -U vigil vigil | gzip > /backups/vigil-$(date +%Y%m%d).sql.gz
        find /backups -name "vigil-*.sql.gz" -mtime +30 -delete
        sleep 86400
      done'
    depends_on:
      - postgres
    networks:
      - vigil-network
```

### Backup Verification

```bash
# Check backup size and integrity
ls -lh backups/

# Test restore (on separate DB instance)
gunzip < backups/vigil-20260208.sql.gz | psql -U vigil -d test_vigil
```

### Point-in-Time Recovery

Enable PostgreSQL WAL archiving for recovery to any point in time:

```sql
-- In PostgreSQL server
ALTER SYSTEM SET wal_level = replica;
ALTER SYSTEM SET archive_mode = on;
ALTER SYSTEM SET archive_command = 'cp %p /pgwal_archive/%f';

-- Reload config
SELECT pg_reload_conf();
```

---

## Monitoring

### Health Check Endpoint

Already implemented in `backend/app.py`:

```python
GET /api/health
# Returns
{
  "ok": true,
  "db": "ok"
}
```

Monitor this endpoint every 10 seconds.

### Key Metrics to Track

```python
from backend.db.retention import get_table_stats

stats = get_table_stats()
# {
#   "incidents_by_status": {"active": 150, "resolved": 8920},
#   "total_incidents": 9070,
#   "incidents_24h": 85,
#   "database_size": "245 MB",
#   "oldest_incident": "2026-01-10T08:00:00"
# }
```

Set alerts:
- **Active incidents > 500**: Too many unresolved incidents
- **DB size > 5GB**: Consider archival
- **Connections > 25**: Running low on pool
- **Response time > 500ms**: Query optimization needed

### Query Slow Log

```sql
-- Enable query logging (production impact: 5-10%)
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- Log queries > 1 second

-- View slow queries
SELECT query, calls, mean_time FROM pg_stat_statements 
ORDER BY mean_time DESC LIMIT 10;
```

---

## Migration Path

### From SQLite to PostgreSQL

1. **Export SQLite data**:
```bash
# Dump SQLite to SQL
sqlite3 backend/data/vigil.db ".dump" > sqlite_dump.sql
```

2. **Transform & Import**:
```bash
# PostgreSQL has slightly different SQL syntax
# Use pgloader for automatic conversion:
docker run --rm -it dimkal/pgloader pgloader sqlite:///path/to/vigil.db postgresql://vigil:pass@postgres/vigil
```

3. **Verify**:
```bash
docker exec vigil_postgres psql -U vigil -c "SELECT COUNT(*) FROM incident;"
```

4. **Update environment**:
```bash
# Switch DATABASE_URL to PostgreSQL
export DATABASE_URL="postgresql+psycopg://vigil:pass@postgres:5432/vigil"

# Restart backend
docker restart vigil_backend
```

---

## Summary: Recommended Production Setup

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports: ["5432:5432"]
    volumes:
      - vigil_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U vigil"]

  backend:
    environment:
      DATABASE_URL: postgresql+psycopg://vigil:${DB_PASSWORD}@postgres:5432/vigil
      DB_POOL_SIZE: 20
      DB_MAX_OVERFLOW: 10
      DB_POOL_RECYCLE: 3600
      INCIDENT_RETENTION_DAYS: 30
      ENABLE_AUTO_ARCHIVAL: 1
      FLASK_ENV: production

  postgres-backup:
    # See "Daily Backups" section above
    
volumes:
  vigil_pgdata:
    driver: local
```

This gives you:
- ✅ **Connection pooling** for 100+ concurrent users
- ✅ **Optimized indexes** for fast queries
- ✅ **Automatic data archival** to prevent table bloat
- ✅ **Daily backups** with 30-day retention
- ✅ **Monitoring hooks** for alerting
