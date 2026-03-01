# Vigil Production Deployment Checklist

## Pre-Deployment

- [ ] All code committed to git
- [ ] Tests passing locally (`pytest`, `npm test`)
- [ ] Dependencies updated (`pip-audit`, `npm audit`)
- [ ] Environment variables configured
- [ ] Database backups scheduled
- [ ] Logging configured (Datadog, CloudWatch, etc.)
- [ ] SSL/TLS certificates obtained

## Infrastructure Setup

### Database
- [ ] PostgreSQL deployed (managed service recommended)
- [ ] Database created: `vigil`
- [ ] User created: `vigil` with strong password
- [ ] Backups enabled
- [ ] Monitoring enabled (query logs, slow queries)
- [ ] Connection pooling configured

### Backend
- [ ] Docker image built and tested
- [ ] Image pushed to registry (ECR, ACR, GCR)
- [ ] Environment variables set
- [ ] Health check endpoint responding
- [ ] Logs configured (stdout for container logging)
- [ ] Resource limits set (CPU, memory)
- [ ] Auto-scaling policy configured (if needed)

### Frontend
- [ ] Node build optimized
- [ ] Assets minified
- [ ] CDN configured (optional)
- [ ] Service worker enabled (optional)
- [ ] Browser compatibility tested

### Networking
- [ ] Firewall rules configured
- [ ] Load balancer health checks working
- [ ] SSL/TLS termination configured
- [ ] CORS headers set correctly
- [ ] Rate limiting enabled
- [ ] DDoS protection enabled

## Security

- [ ] Default credentials changed
- [ ] API keys regenerated
- [ ] Secrets in secure vault (AWS Secrets, Azure Key Vault)
- [ ] Database encrypted at rest
- [ ] Connections use HTTPS/TLS
- [ ] CORS properly restricted
- [ ] CSRF protection enabled
- [ ] SQL injection prevention verified
- [ ] XSS protection enabled

## Monitoring & Alerts

- [ ] Health check endpoint monitoring
- [ ] Error rate alerting (>1% threshold)
- [ ] Latency monitoring (p95 < 500ms)
- [ ] Database connection alerts
- [ ] Disk space alerts
- [ ] Memory usage alerts
- [ ] CPU alerts
- [ ] Uptime monitoring (external service)

## Data & Backups

- [ ] Database backup schedule: daily
- [ ] Backup retention: 30 days
- [ ] Backup encryption: enabled
- [ ] Restore tested: weekly
- [ ] Video storage backup plan
- [ ] Disaster recovery plan documented

## Documentation

- [ ] Runbook created (how to operate)
- [ ] Troubleshooting guide completed
- [ ] API documentation up to date
- [ ] Architecture diagrams created
- [ ] Security policies documented
- [ ] Incident response plan created

## Load Testing

- [ ] Baseline performance tested
- [ ] Stress test completed (100+ concurrent users)
- [ ] Database connections under load tested
- [ ] WebSocket message throughput tested
- [ ] Video streaming capacity tested
- [ ] Bottlenecks identified and addressed

## Deployment

- [ ] Database migrations ready
- [ ] Schema changes tested
- [ ] Rollback plan documented
- [ ] Deployment runbook created
- [ ] Blue-green deployment configured
- [ ] Feature flags ready (if needed)

## Post-Deployment

- [ ] Smoke tests passed
- [ ] Health checks green
- [ ] Users can login
- [ ] Incidents detected correctly
- [ ] Reports generating
- [ ] Logs flowing properly
- [ ] Monitoring dashboard accessible
- [ ] Performance baseline met

## Performance Acceptance Criteria

- [ ] API response time: < 200ms (p95)
- [ ] Dashboard load time: < 2s
- [ ] Video streaming: no buffering at scale
- [ ] Database queries: < 50ms (p95)
- [ ] WebSocket latency: < 100ms
- [ ] Error rate: < 0.1%
- [ ] Memory usage: < 80% of limit
- [ ] CPU usage: < 80% of limit

## Rollback Plan

- [ ] Previous version container image tagged
- [ ] Database rollback steps documented
- [ ] Configuration rollback steps
- [ ] Communication plan for incidents
- [ ] Rollback success criteria defined

## Post-Launch (1 Week)

- [ ] Monitor error rates daily
- [ ] Review slow query logs
- [ ] Validate data integrity
- [ ] Check backup integrity
- [ ] Gather user feedback
- [ ] Performance review
- [ ] Security scan results reviewed
- [ ] Plan next improvements

---

## Deployment Commands

```bash
# Backup before deployment
docker exec vigil_postgres pg_dump -U vigil vigil > backup-pre-deploy.sql

# Build production images
docker compose -f config/docker-compose.prod.yml build

# Stop current deployment
docker compose -f config/docker-compose.prod.yml down

# Start new deployment
docker compose -f config/docker-compose.prod.yml up -d

# Verify health
curl https://your-domain/api/health

# Check logs
docker compose -f config/docker-compose.prod.yml logs -f
```

## Emergency Rollback

```bash
# Restore database from backup
docker exec -i vigil_postgres psql -U vigil vigil < backup-pre-deploy.sql

# Restart with tagged image
docker compose -f config/docker-compose.prod.yml down
# Edit docker-compose.prod.yml to use previous image tag
docker compose -f config/docker-compose.prod.yml up -d
```

---

**Status**: ⬜ Not Started | ⏳ In Progress | ✅ Complete
