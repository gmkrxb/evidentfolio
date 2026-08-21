# Deployment and upgrades

[简体中文](DEPLOYMENT.zh-CN.md)

## Persistence contract

EvidentFolio has exactly two durable runtime paths:

- `/app/data`: SQLite database and automatic migration backups.
- `/app/uploads`: originals, thumbnails, and temporary upload workspace.

The published image contains the frontend, backend, Nginx, Python runtime, PDF tools, and ffmpeg. Replacing or removing a container does **not** remove bind-mounted host directories. Never delete the host `data/` or `uploads/` directories during an update.

First deployment with empty directories creates an empty schema and opens one-time initialization. Later deployments detect the existing database, back it up, and migrate it without injecting or replacing content.

## 1. Published all-in-one image

Generate a secret once and store it in your password manager:

```bash
mkdir -p /srv/evidentfolio/data /srv/evidentfolio/uploads
openssl rand -hex 32
```

Run on HTTP for local evaluation:

```bash
docker run -d --name evidentfolio --restart unless-stopped -p 8080:80 -e EVIDENTFOLIO_SECRET_KEY='replace-with-generated-secret' -e EVIDENTFOLIO_TRUSTED_HOSTS='localhost,127.0.0.1' -e EVIDENTFOLIO_SECURE_COOKIES=false -v /srv/evidentfolio/data:/app/data -v /srv/evidentfolio/uploads:/app/uploads ghcr.io/gmkrxb/evidentfolio:latest
```

For production HTTPS, set the real host and secure cookies:

```bash
docker run -d --name evidentfolio --restart unless-stopped -p 127.0.0.1:10010:80 -e EVIDENTFOLIO_SECRET_KEY='replace-with-generated-secret' -e EVIDENTFOLIO_TRUSTED_HOSTS='portfolio.example.com,localhost,127.0.0.1' -e EVIDENTFOLIO_SECURE_COOKIES=true -v /srv/evidentfolio/data:/app/data -v /srv/evidentfolio/uploads:/app/uploads ghcr.io/gmkrxb/evidentfolio:latest
```

Proxy the domain to `127.0.0.1:10010`, preserving `Host`, protocol, and client IP headers. Only list the real proxy network in `EVIDENTFOLIO_TRUSTED_PROXY_IPS`.

### Updating without losing data

```bash
docker pull ghcr.io/gmkrxb/evidentfolio:latest
docker rm -f evidentfolio
docker run -d --name evidentfolio --restart unless-stopped -p 127.0.0.1:10010:80 -e EVIDENTFOLIO_SECRET_KEY='the-same-existing-secret' -e EVIDENTFOLIO_TRUSTED_HOSTS='portfolio.example.com,localhost,127.0.0.1' -e EVIDENTFOLIO_SECURE_COOKIES=true -v /srv/evidentfolio/data:/app/data -v /srv/evidentfolio/uploads:/app/uploads ghcr.io/gmkrxb/evidentfolio:latest
docker logs -f --tail 160 evidentfolio
```

`docker rm -f` removes only the container. The two host directories remain. Reuse the same secret: changing it invalidates sessions and prevents decryption of a previously stored AI API key.

Startup runs `quick_check`, creates `data/migration-backups/portfolio.before-<revision>.db`, executes `alembic upgrade head`, validates foreign keys, then starts services. A migration failure leaves the service stopped and the backup available.

## 2. Build the all-in-one image yourself

```bash
git clone https://github.com/gmkrxb/evidentfolio.git
cd evidentfolio
docker build --platform linux/amd64 -f Dockerfile.unified -t evidentfolio:local .
```

Use the same run and update procedure, replacing the image name with `evidentfolio:local`.

## 3. Runtime image with external frontend/backend

Run `scripts/build-release.ps1` on Windows or `scripts/build-release.sh` on Linux. It generates stable names:

```text
release/evidentfolio-runtime-linux-amd64.tar
release/evidentfolio-frontend.zip
release/evidentfolio-backend.zip
release/SHA256SUMS.txt
```

On the server:

```bash
mkdir -p /srv/evidentfolio/frontend /srv/evidentfolio/backend /srv/evidentfolio/data /srv/evidentfolio/uploads /srv/evidentfolio/config
unzip -oq evidentfolio-frontend.zip -d /srv/evidentfolio/frontend
unzip -oq evidentfolio-backend.zip -d /srv/evidentfolio/backend
cp /srv/evidentfolio/backend/deploy/config/config.example.py /srv/evidentfolio/config/config.py
# Edit config.py and generate a unique SECRET_KEY before the first run.
docker load -i evidentfolio-runtime-linux-amd64.tar
docker run -d --name evidentfolio --restart unless-stopped -p 10010:80 -v /srv/evidentfolio/frontend:/usr/share/nginx/html:ro -v /srv/evidentfolio/backend:/app/backend:ro -v /srv/evidentfolio/data:/app/data -v /srv/evidentfolio/uploads:/app/uploads -v /srv/evidentfolio/config/config.py:/app/config/config.py:ro evidentfolio-runtime:latest
```

For an update, unzip the new frontend/backend archives over their matching code directories, load the new runtime image only when the runtime archive changed, recreate the container, and keep `data`, `uploads`, and `config` untouched. Automatic migration still runs before the API starts.

## 4. Direct source deployment

Requirements: Python 3.12, ffmpeg/ffprobe, Poppler tools, Node.js 22+, `cnpm`, and Nginx.

```bash
python3.12 -m pip install -r backend/requirements.txt
cp deploy/config/config.example.py deploy/config/config.py
# Edit config.py.
cd backend
PORTFOLIO_CONFIG=../deploy/config/config.py python3.12 -m app.startup preflight
PORTFOLIO_CONFIG=../deploy/config/config.py python3.12 -m alembic -c alembic.ini upgrade head
PORTFOLIO_CONFIG=../deploy/config/config.py python3.12 -m app.startup postflight
PORTFOLIO_CONFIG=../deploy/config/config.py python3.12 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Build the frontend with `cnpm install && cnpm run build`, serve `frontend/dist` through Nginx, proxy `/api`, `/sitemap.xml`, and `/robots.txt` to port 8000, and provide SPA fallback. `deploy/nginx/` contains working references. Always run the three startup/migration commands after pulling backend updates.

## 5. Render

Use the Render button in the README or create a Blueprint from `render.yaml`. The Blueprint builds `Dockerfile.unified` and mounts a persistent disk at `/app/storage`. Do not remove that disk during an update. Render generates the secret automatically; add custom hosts to `EVIDENTFOLIO_TRUSTED_HOSTS` when attaching a domain.

Render plans and persistent-disk availability can change. Confirm current pricing and backup options before storing production data.

## 6. Vercel frontend

Vercel deploys only `frontend/`. Set `VITE_API_BASE_URL` to the full `/api/v1` URL of an existing EvidentFolio API and add the Vercel origin to backend `CORS_ORIGINS`.

SQLite and uploads cannot live in a stateless Vercel frontend. Cross-site cookie restrictions also make the admin experience less reliable; use Vercel primarily for the public site, and use an all-in-one/same-origin deployment for administration.

## Backup and restore

For a consistent manual backup, briefly stop writes and copy both paths:

```bash
docker stop evidentfolio
cp -a /srv/evidentfolio/data /srv/backups/evidentfolio-data
cp -a /srv/evidentfolio/uploads /srv/backups/evidentfolio-uploads
docker start evidentfolio
```

To restore, stop the container, preserve the current directories under different names, restore the matching database and upload snapshots together, then start the container. The startup migration handles an older restored database.

## Verification

```bash
docker ps --filter 'name=^/evidentfolio$'
curl -fsS http://127.0.0.1:10010/api/health
docker logs --tail 160 evidentfolio
```

Also verify administrator login, one public project, an image thumbnail, a PDF, and a video Range request after each production update.
