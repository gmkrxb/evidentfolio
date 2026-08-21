#!/bin/sh
set -eu

mkdir -p /app/data /app/uploads /app/config

if [ -f /app/config/config.py ]; then
    export PORTFOLIO_CONFIG=/app/config/config.py
fi

# Make bind-mounted data writable by the unprivileged API process. This runs
# before the service starts so a restored database and upload tree work with a
# single docker run command.
chown -R portfolio:portfolio /app/data /app/uploads

cd /app/backend
gosu portfolio python -m app.startup preflight
gosu portfolio alembic -c /app/backend/alembic.ini upgrade head
gosu portfolio python -m app.startup postflight

exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/portfolio.conf
