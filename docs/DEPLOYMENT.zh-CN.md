# 部署、更新与数据保留

[English](DEPLOYMENT.md)

## 持久化约定

EvidentFolio 只有两个必须持久化的运行目录：

- `/app/data`：SQLite 数据库和自动迁移备份；
- `/app/uploads`：原始文件、缩略图和上传临时空间。

官方镜像包含前端、后端、Nginx、Python、PDF 工具和 ffmpeg。删除或替换容器**不会删除宿主机绑定目录**。二次更新时绝对不要删除宿主机的 `data/` 和 `uploads/`。

第一次运行且目录中没有数据库时，系统创建空表并进入一次性初始化；以后每次运行都会识别旧数据库、备份并增量迁移，不注入或覆盖任何内容。

## 1. 官方一体镜像

第一次部署生成一次密钥，并保存在密码管理器：

```bash
mkdir -p /srv/evidentfolio/data /srv/evidentfolio/uploads
openssl rand -hex 32
```

本机 HTTP 体验：

```bash
docker run -d --name evidentfolio --restart unless-stopped -p 8080:80 -e EVIDENTFOLIO_SECRET_KEY='替换为生成的密钥' -e EVIDENTFOLIO_TRUSTED_HOSTS='localhost,127.0.0.1' -e EVIDENTFOLIO_SECURE_COOKIES=false -v /srv/evidentfolio/data:/app/data -v /srv/evidentfolio/uploads:/app/uploads ghcr.io/gmkrxb/evidentfolio:latest
```

生产 HTTPS 部署：

```bash
docker run -d --name evidentfolio --restart unless-stopped -p 127.0.0.1:10010:80 -e EVIDENTFOLIO_SECRET_KEY='替换为生成的密钥' -e EVIDENTFOLIO_TRUSTED_HOSTS='portfolio.example.com,localhost,127.0.0.1' -e EVIDENTFOLIO_SECURE_COOKIES=true -v /srv/evidentfolio/data:/app/data -v /srv/evidentfolio/uploads:/app/uploads ghcr.io/gmkrxb/evidentfolio:latest
```

域名反代到 `127.0.0.1:10010`，并转发 Host、协议和真实 IP。`EVIDENTFOLIO_TRUSTED_PROXY_IPS` 只填写真实代理网络。

### 二次更新且保留全部数据

```bash
docker pull ghcr.io/gmkrxb/evidentfolio:latest
docker rm -f evidentfolio
docker run -d --name evidentfolio --restart unless-stopped -p 127.0.0.1:10010:80 -e EVIDENTFOLIO_SECRET_KEY='继续使用原来的密钥' -e EVIDENTFOLIO_TRUSTED_HOSTS='portfolio.example.com,localhost,127.0.0.1' -e EVIDENTFOLIO_SECURE_COOKIES=true -v /srv/evidentfolio/data:/app/data -v /srv/evidentfolio/uploads:/app/uploads ghcr.io/gmkrxb/evidentfolio:latest
docker logs -f --tail 160 evidentfolio
```

`docker rm -f` 只删除容器，不删除两个宿主机目录。必须继续使用原密钥；更换密钥会使登录 Session 失效，并导致已保存的 AI API Key 无法解密。

启动时依次执行 SQLite 完整性检查、`data/migration-backups/portfolio.before-<旧版本>.db` 备份、`alembic upgrade head` 和外键检查。迁移失败时服务不会启动，旧库备份仍然保留。

## 2. 自行构建一体镜像

```bash
git clone https://github.com/gmkrxb/evidentfolio.git
cd evidentfolio
docker build --platform linux/amd64 -f Dockerfile.unified -t evidentfolio:local .
```

运行和更新方式与官方镜像一致，只需将镜像名替换为 `evidentfolio:local`。

## 3. 外置前后端与独立运行环境

Windows 执行 `scripts/build-release.ps1`，Linux 执行 `scripts/build-release.sh`，生成无日期文件名：

```text
release/evidentfolio-runtime-linux-amd64.tar
release/evidentfolio-frontend.zip
release/evidentfolio-backend.zip
release/SHA256SUMS.txt
```

服务器首次部署：

```bash
mkdir -p /srv/evidentfolio/frontend /srv/evidentfolio/backend /srv/evidentfolio/data /srv/evidentfolio/uploads /srv/evidentfolio/config
unzip -oq evidentfolio-frontend.zip -d /srv/evidentfolio/frontend
unzip -oq evidentfolio-backend.zip -d /srv/evidentfolio/backend
cp /srv/evidentfolio/backend/deploy/config/config.example.py /srv/evidentfolio/config/config.py
# 首次启动前编辑 config.py 并生成独立 SECRET_KEY
docker load -i evidentfolio-runtime-linux-amd64.tar
docker run -d --name evidentfolio --restart unless-stopped -p 10010:80 -v /srv/evidentfolio/frontend:/usr/share/nginx/html:ro -v /srv/evidentfolio/backend:/app/backend:ro -v /srv/evidentfolio/data:/app/data -v /srv/evidentfolio/uploads:/app/uploads -v /srv/evidentfolio/config/config.py:/app/config/config.py:ro evidentfolio-runtime:latest
```

二次更新只覆盖前端和后端代码目录；运行环境有变化时再 `docker load` 新 TAR。重建容器时继续挂载原 `data`、`uploads`、`config`，不要删除这三个目录。启动时仍会自动迁移旧数据库。

## 4. 源码部署

需要 Python 3.12、ffmpeg/ffprobe、Poppler、Node.js 22+、`cnpm` 和 Nginx。

```bash
python3.12 -m pip install -r backend/requirements.txt
cp deploy/config/config.example.py deploy/config/config.py
# 编辑 config.py
cd backend
PORTFOLIO_CONFIG=../deploy/config/config.py python3.12 -m app.startup preflight
PORTFOLIO_CONFIG=../deploy/config/config.py python3.12 -m alembic -c alembic.ini upgrade head
PORTFOLIO_CONFIG=../deploy/config/config.py python3.12 -m app.startup postflight
PORTFOLIO_CONFIG=../deploy/config/config.py python3.12 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

前端执行 `cnpm install && cnpm run build`，用 Nginx 托管 `frontend/dist`，并将 `/api`、`/sitemap.xml`、`/robots.txt` 代理到 8000 端口。每次拉取新的后端代码后，都要在重启 API 前执行上述启动检查和迁移命令。

## 5. Render

使用 README 的 Render 按钮，或从 `render.yaml` 创建 Blueprint。配置会构建一体镜像，并把持久磁盘挂载到 `/app/storage`。更新时不要删除磁盘。绑定自定义域名后，将域名加入 `EVIDENTFOLIO_TRUSTED_HOSTS`。

Render 套餐和持久磁盘规则可能变化，生产使用前请确认当前价格、容量和备份能力。

## 6. Vercel 前端

Vercel 只部署 `frontend/`。把 `VITE_API_BASE_URL` 设置为已有 EvidentFolio API 的完整 `/api/v1` 地址，并将 Vercel 域名加入后端 `CORS_ORIGINS`。

SQLite 和上传目录不能放在无状态 Vercel 前端中；跨站 Cookie 也会影响后台体验。因此 Vercel 更适合公开只读展示，后台建议使用同域一体部署。

## 备份与恢复

手动一致性备份时短暂停止写入，并同时复制数据库和上传目录：

```bash
docker stop evidentfolio
cp -a /srv/evidentfolio/data /srv/backups/evidentfolio-data
cp -a /srv/evidentfolio/uploads /srv/backups/evidentfolio-uploads
docker start evidentfolio
```

恢复时先停止容器，将当前目录改名保留，再恢复同一时间点的数据库与上传目录，最后启动容器。即使恢复的是旧版本数据库，启动迁移也会自动升级。

## 更新后验证

```bash
docker ps --filter 'name=^/evidentfolio$'
curl -fsS http://127.0.0.1:10010/api/health
docker logs --tail 160 evidentfolio
```

生产更新后还应验证管理员登录、一个公开项目、图片缩略图、PDF 和视频 Range 请求。
