# Contributing to EvidentFolio

[简体中文](CONTRIBUTING.zh-CN.md)

Thanks for helping build a portfolio system that values evidence, clarity, privacy, and maintainability.

## Before coding

- Search existing issues and pull requests.
- Open an issue before a large feature, schema redesign, new dependency, or breaking API change.
- Security reports must follow [SECURITY.md](SECURITY.md).
- Never use a real résumé, production database, API key, visitor log, or personal upload as test data.

## Branch and commit conventions

- Branches: `feat/short-name`, `fix/short-name`, `docs/short-name`, `refactor/short-name`.
- Commits follow Conventional Commits, for example `feat(assets): add dependency preflight`.
- Keep each commit reviewable. Do not mix formatting-only rewrites with behavior changes.

## Development rules

- Python code targets 3.12, includes type annotations, and keeps routes, services, repositories, models, and schemas separated.
- Vue code uses TypeScript, Composition API, isolated API clients, and reusable components.
- Fixed interface copy must be added to both `frontend/src/i18n/messages/zh-CN.ts` and `en.ts`. User-authored translations belong in database `translations` fields.
- Public identifiers must remain UUIDs. Integer database IDs must never enter public URLs or API payloads.
- New database changes require an Alembic migration that upgrades an existing database without deleting user content.
- Upload changes require extension, MIME, size, path traversal, and authorization tests.
- Motion must respect `prefers-reduced-motion`; controls must remain keyboard accessible.
- Do not add a third-party CMS, remote font, or analytics tracker without prior discussion.

## Required checks

```bash
cd frontend
cnpm run type-check
cnpm run test
cnpm run build

cd ../backend
pytest

cd ..
docker build --platform linux/amd64 -f Dockerfile.unified -t evidentfolio:pr .
```

For UI changes, include desktop and mobile screenshots. For migrations, add a test that upgrades from the previous revision and verifies preserved content.

## Pull request format

A PR should contain:

1. Problem and user impact.
2. What changed and what intentionally did not change.
3. Verification commands and results.
4. Screenshots or API examples when relevant.
5. Migration, security, accessibility, and rollback notes.

PRs may be closed when they include secrets or personal data, bypass migrations, weaken file security, store auth tokens in LocalStorage, or introduce unexplained generated code. Maintainers may ask for a smaller scope before review.

By contributing, you agree that your contribution is licensed under the repository's MIT License and to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
