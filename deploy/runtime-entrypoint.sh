#!/bin/sh
set -eu

required_files="/app/backend/alembic.ini /app/backend/app/main.py /usr/share/nginx/html/index.html /app/config/config.py"
for required_file in $required_files; do
    if [ ! -f "$required_file" ]; then
        echo "Required mounted file is missing: $required_file" >&2
        exit 1
    fi
done

mkdir -p /app/data /app/uploads /app/uploads/temp
chown -R portfolio:portfolio /app/data /app/uploads

cd /app/backend
gosu portfolio python -m app.startup preflight
gosu portfolio alembic -c /app/backend/alembic.ini upgrade head
gosu portfolio python -m app.startup postflight

exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/portfolio.conf
