# System architecture

[简体中文](ARCHITECTURE.md)

## Runtime flow

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

## Module boundaries

- `frontend/src/` is organized around public/admin views, reusable components, stores, composables, routing, and a typed API client.
- `backend/app/api` owns HTTP concerns only; business behavior belongs in services and repositories.
- `backend/app/models` defines persistence; `schemas` defines API input/output contracts.
- `file_processing` validates and derives media without exposing physical paths.
- `analytics` records pseudonymous signals and computes rule-based, explainable attention scores.
- `security` centralizes trusted-proxy, client-IP, SVG, and related safety rules.

## Data ownership

All durable state lives outside the container:

```text
data/portfolio.db       SQLite database
data/migration-backups  one backup per source migration revision
uploads/                UUID-named originals, thumbnails, and temporary files
```

Removing or replacing a container does not delete bind-mounted host directories. A clean first launch creates an empty schema; subsequent launches migrate the existing database in place and never inject demo content.

## Startup state machine

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

## Public identifiers and files

Database relations may use integer primary keys internally, but every externally visible entity uses UUID. Asset URLs resolve UUIDs through authorization checks; storage paths and original physical names are never exposed. Renaming a display name does not change its URL.

## Internationalization

- Fixed product copy: `frontend/src/i18n/messages/zh-CN.ts` and `en.ts`.
- User content: JSON translation objects in the database.
- English public URLs: `/en/...`; selected language is cached in the browser.
- API errors: localized from `Accept-Language` without leaking stack traces.

Adding another interface language requires a message package and locale routing. Adding user-content languages also requires extending the translation editor and serializer locale selection.

## AI boundary

AI is optional and OpenAI API-compatible. Provider URL, encrypted key, and chosen model are configured in the admin. Parsing and translation use streamed output and structured JSON validation; generated projects remain drafts until the administrator confirms them. No AI provider is required for core portfolio features.

## Security assumptions

- Only configured trusted proxies may supply forwarded IP headers.
- Uploaded HTML or JavaScript is never executed.
- Private UUID resources still require authorization; UUID obscurity is not access control.
- Docker bind mounts and backups are protected by the operator's host permissions.
