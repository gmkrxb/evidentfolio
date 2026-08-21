#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
RELEASE="$ROOT/release"
STAGE="$RELEASE/.backend-stage"
mkdir -p "$RELEASE"
case "$STAGE" in "$RELEASE"/*) ;; *) echo "Unsafe staging path" >&2; exit 1 ;; esac
rm -rf "$STAGE"

cd "$ROOT/frontend"
cnpm run type-check
cnpm run test
cnpm run build

cd "$ROOT"
docker build --platform linux/amd64 -f Dockerfile.runtime -t evidentfolio-runtime:latest .
docker save -o "$RELEASE/evidentfolio-runtime-linux-amd64.tar" evidentfolio-runtime:latest

mkdir -p "$STAGE/deploy/config"
cp -R backend/app backend/alembic backend/tests "$STAGE/"
cp backend/alembic.ini backend/requirements.txt backend/pyproject.toml "$STAGE/"
cp deploy/config/config.example.py "$STAGE/deploy/config/config.example.py"

rm -f "$RELEASE/evidentfolio-frontend.zip" "$RELEASE/evidentfolio-backend.zip"
(cd frontend/dist && zip -qr "$RELEASE/evidentfolio-frontend.zip" . -x 'write-check.tmp')
(cd "$STAGE" && zip -qr "$RELEASE/evidentfolio-backend.zip" . -x '*/__pycache__/*' '*/.pytest_cache/*' '*/.runtime/*')
(cd "$RELEASE" && sha256sum evidentfolio-runtime-linux-amd64.tar evidentfolio-frontend.zip evidentfolio-backend.zip > SHA256SUMS.txt)
rm -rf "$STAGE"
echo "Release artifacts written to $RELEASE"
