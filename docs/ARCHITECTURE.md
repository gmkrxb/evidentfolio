# Architecture / 系统架构

## Runtime flow / 运行链路

```text
Browser
  └─ Nginx :80
      ├─ Vue SPA and immutable assets
      ├─ /api, /sitemap.xml, /robots.txt → FastAPI :8000
      └─ protected thumbnails → internal X-Accel redirect

FastAPI (one Uvicorn worker)
  ├─ routers → services → repositories → SQLAlchemy → SQLite WAL
  ├─ upload validation → UUID storage → thumbnails / metadata
  ├─ HttpOnly session + CSRF + audit log
  └─ anonymous analytics → events → explainable aggregates
```

Nginx and a single Uvicorn worker run together in the published image. The single writer is intentional: SQLite remains simple and portable without pretending to be a horizontally scaled database.

发布镜像内同时运行 Nginx 与单个 Uvicorn Worker。单写入实例是明确设计选择，避免 SQLite 在多实例并发写入下出现不可预期行为。

## Boundaries / 模块边界

- `frontend/src/modules` is represented by route-level public/admin views plus reusable components, stores, composables, and a single API client.
- `backend/app/api` owns HTTP concerns only; business behavior belongs in services and repositories.
- `backend/app/models` defines persistence; `schemas` defines API input/output contracts.
- `file_processing` validates and derives media without exposing physical paths.
- `analytics` records pseudonymous signals. Scores are rule-based and never claim to identify a person or hiring intent.
- `security` centralizes network and SVG safety rules.

## Data ownership / 数据所有权

All durable state lives outside the container:

```text
data/portfolio.db       SQLite database
data/migration-backups  one backup per source migration revision
uploads/                UUID-named originals, thumbnails, and temporary files
```

Removing or replacing a container does not delete bind-mounted host directories. A clean first launch creates an empty schema; subsequent launches migrate the existing database in place and never inject demo content.

所有持久数据位于容器外。删除并重建容器不会删除宿主机绑定目录。第一次启动只创建空表；后续启动只迁移已有数据库，不注入示例内容。

## Startup state machine / 启动状态机

```text
mounted paths
  → writable checks
  → SQLite quick_check
  → revision-named backup (existing DB only)
  → alembic upgrade head
  → foreign_key_check + ffmpeg check
  → supervisor starts API and Nginx
  → health check becomes healthy
```

Any failure stops startup. The previous database backup remains in `data/migration-backups/` for operator-controlled rollback.

## Public identifiers and files / 公开标识与文件

Database relations may use integer primary keys internally, but every externally visible entity uses UUID. Asset URLs resolve UUIDs through authorization checks; storage paths and original physical names are never exposed. Renaming a display name does not change its URL.

## Internationalization / 国际化

- Fixed product copy: `frontend/src/i18n/messages/zh-CN.ts` and `en.ts`.
- User content: JSON translation objects in the database.
- English public URLs: `/en/...`; selected language is cached in the browser.
- API errors: localized from `Accept-Language` without leaking stack traces.

Adding another interface language means adding a message package and locale routing. Adding user-content languages also requires extending the translation editor and serializer locale selection.

## AI boundary / AI 边界

AI is optional and OpenAI API-compatible. Provider URL, encrypted key, and chosen model are configured in the admin. Parsing and translation use streamed output and structured JSON validation; generated projects remain drafts until the administrator confirms them. No AI provider is required for core portfolio features.

## Security assumptions / 安全假设

- Production runs behind HTTPS with secure cookies.
- Only configured trusted proxies may supply forwarded IP headers.
- Uploaded HTML or JavaScript is never executed.
- Private UUID resources still require authorization; UUID obscurity is not access control.
- Docker bind mounts and backups are protected by the operator's host permissions.
