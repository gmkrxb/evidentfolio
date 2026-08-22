# Changelog / 更新记录

All notable changes follow [Keep a Changelog](https://keepachangelog.com/) and semantic versioning.

## [Unreleased] / 未发布

### Documentation / 文档

- 将仓库默认 `README.md` 调整为中文，并将完整英文说明迁移到 `README.en.md`。
- 保留 `README.zh-CN.md` 作为旧链接兼容入口。
- 为 `.github/`、`backend/`、`data/`、`deploy/`、`docs/`、`frontend/`、`scripts/` 增加独立命名、带版本号的目录职责说明。
- 增加 `main` 分支保护与必需 CI 检查的仓库治理说明。

## [1.0.0] - 2026-08-21

### Added / 新增

- Evidence-first public portfolio and case-study presentation.
- Project, taxonomy, asset, folder, album, résumé, credential, settings, analytics, and audit management.
- Chinese/English routes, UI language packs, and database-backed content translations.
- OpenAI-compatible model configuration, streaming translation, and résumé parsing.
- Docker all-in-one, external-runtime, Render, Vercel-frontend, and source deployment paths.
- Startup SQLite integrity checks, automatic Alembic upgrades, and pre-migration backups.

### Changed / 调整

- Open-source installations now start completely empty and enter one-time setup.
- Package and image names no longer contain build dates; releases are identified by semantic versions and Git tags.

### Security / 安全

- No maintainer résumé, project database, uploaded media, API key, or visitor record is included in source or images.
