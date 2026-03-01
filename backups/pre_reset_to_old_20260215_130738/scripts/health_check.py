"""
Simple health/regression check for the Vigil backend.

Usage:
  python -X utf8 scripts/health_check.py --base http://127.0.0.1:5000 --token <JWT>

Checks performed:
  - /api/health
  - /api/incidents (first page, requires token)
  - Optional: /api/ai-models (if token supplied)
Exits non-zero on failure.
"""

import argparse
import sys
import os
import requests


def check_health(base):
    url = f"{base}/api/health"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Health not ok: {data}")
    return data


def check_incidents(base, token=None):
    url = f"{base}/api/incidents"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()


def login_and_get_token(base, email, password, role=None):
    url = f"{base}/auth/login"
    payload = {"email": email, "password": password}
    if role:
        payload["role"] = role
    r = requests.post(url, json=payload, timeout=10)
    r.raise_for_status()
    data = r.json()
    return data.get("token")


def check_ai_models(base, token=None):
    url = f"{base}/api/ai-models"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:5000", help="Base URL of backend")
    ap.add_argument("--token", default=None, help="JWT bearer token (optional; will auto-login if not provided)")
    ap.add_argument("--email", default=os.getenv("HC_EMAIL", "admin@vigil.com"), help="Login email (fallback to HC_EMAIL env)")
    ap.add_argument("--password", default=os.getenv("HC_PASSWORD", "admin123"), help="Login password (fallback to HC_PASSWORD env)")
    ap.add_argument("--role", default=os.getenv("HC_ROLE", None), help="Optional role for login")
    args = ap.parse_args()

    try:
        h = check_health(args.base)
        print("[OK] /api/health", h)

        token = args.token
        if not token:
            token = login_and_get_token(args.base, args.email, args.password, args.role)
        inc = check_incidents(args.base, token)
        print(f"[OK] /api/incidents count={len(inc.get('cameras', [])) if 'cameras' in inc else len(inc)}")

        if token:
            models = check_ai_models(args.base, token)
            print(f"[OK] /api/ai-models count={len(models)}")

    except Exception as e:
        print(f"[FAIL] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
