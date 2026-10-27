#!/bin/sh
set -e
# Migrations run before the server starts. In production this must be
# verified against an empty database first (see ARCHITECTURE.md).
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
