#!/bin/sh
set -eu

python -m app.startup preflight
alembic -c alembic.ini upgrade head
python -m app.startup postflight
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --proxy-headers
