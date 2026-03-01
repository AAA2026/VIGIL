# Gunicorn configuration for Vigil backend (SocketIO + eventlet)
#
# Environment variables you should set in production:
#   FLASK_ENV=production
#   DATABASE_URL=postgresql+psycopg://user:pass@host:5432/vigil_prod
#   JWT_SECRET=<strong secret>
#   S3_BUCKET, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_REGION (and optional S3_ENDPOINT_URL, S3_SIGNED_URL_EXPIRES)
#   ALLOW_SQLITE_FALLBACK should remain unset in production.
#
# To run:
#   gunicorn -c config/gunicorn.conf.py backend.app:app

import multiprocessing
import os

bind = os.getenv("GUNICORN_BIND", "0.0.0.0:5000")
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() or 2))
worker_class = "eventlet"
threads = int(os.getenv("GUNICORN_THREADS", "1"))  # eventlet uses cooperative threads
loglevel = os.getenv("GUNICORN_LOGLEVEL", "info")
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))
accesslog = "-"
errorlog = "-"
preload_app = False  # SocketIO + eventlet: avoid preload

# Max requests to recycle workers (helps with leaks)
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "100"))
