# Project structure

[简体中文](PROJECT_STRUCTURE.md)

This page describes the responsibilities of the repository's first-party top-level files and code areas. Large PDF.js CMap/font/WASM collections are vendored runtime assets and are documented as groups rather than item by item.

## Root

| Path | Responsibility |
| --- | --- |
| `README.md`, `README.en.md` | Chinese default project entry and English companion |
| `LICENSE` | MIT license |
| `CHANGELOG.md` | Semantic release history |
| `CONTRIBUTING.md`, `CONTRIBUTING.en.md` | Contribution and PR rules |
| `CODE_OF_CONDUCT.md` | Community behavior policy |
| `SECURITY.md` | Vulnerability reporting and operator checklist |
| `.gitignore` | Excludes secrets, databases, uploads, builds, caches, and release binaries |
| `.dockerignore` | Keeps local data and release artifacts out of image layers |
| `.editorconfig`, `.gitattributes` | Cross-platform formatting and line endings |
| `Dockerfile.unified` | Published all-in-one frontend + API + Nginx image |
| `Dockerfile.frontend` | Standalone static frontend image |
| `Dockerfile.backend` | Standalone FastAPI image |
| `Dockerfile.runtime` | Runtime-only image for externally mounted frontend/backend |
| `render.yaml` | Render Blueprint with persistent disk |

## `frontend/`

Contains the Vue 3 + TypeScript public site and administration interface, including routing, typed API clients, state management, internationalization, views, reusable components, PDF viewing, analytics interactions, and responsive styles. See `frontend/FRONTEND_APP_v1.0.0.md`.

## `backend/`

Contains the FastAPI application, SQLAlchemy models, Pydantic schemas, repositories, services, API routes, file processing, analytics, security helpers, Alembic migrations, and backend tests. See `backend/BACKEND_SERVICE_v1.0.0.md`.

## `deploy/`

Contains Python configuration templates, Nginx and Supervisor configuration, container entrypoints, and PowerShell run/backup/restore helpers. See `deploy/DEPLOY_TOOLKIT_v1.0.0.md`.

## `docs/`

Contains architecture, API, deployment, project-structure documents, and sanitized screenshots. Chinese is the default language for un-suffixed documents; English companions use `.en.md`. See `docs/DOCUMENTATION_INDEX_v1.0.0.md`.

## `data/`

Runtime SQLite data and migration backups. Real databases are ignored and must not be committed. See `data/DATA_RUNTIME_v1.0.0.md`.

## `scripts/`

Reproducible release-packaging helpers for Windows and Unix-like systems. See `scripts/RELEASE_TOOLING_v1.0.0.md`.

## `.github/`

GitHub Actions, Issue/PR templates, Dependabot, and repository-governance guidance. See `.github/REPOSITORY_GOVERNANCE_v1.0.0.md`.
