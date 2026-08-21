# Project structure / 项目目录说明

This map describes every first-party top-level file and code area. Large PDF.js CMap/font/WASM collections are vendored runtime assets and are documented as a group rather than listing hundreds of upstream files individually.

本页说明所有一方顶层文件和代码区域。PDF.js 的 CMap、字体和 WASM 属于上游运行资源，因此按资源组说明，不逐个重复列出数百个文件。

## Root / 根目录

| Path | Responsibility / 职责 |
| --- | --- |
| `README.md`, `README.zh-CN.md` | English and Chinese project entry documents / 中英文项目入口 |
| `LICENSE` | MIT license / MIT 许可证 |
| `CHANGELOG.md` | Semantic release history / 语义化版本记录 |
| `CONTRIBUTING*.md` | Contribution and PR rules / 贡献与 PR 规范 |
| `CODE_OF_CONDUCT.md` | Community behavior policy / 社区行为准则 |
| `SECURITY.md` | Private vulnerability reporting and operator checklist / 安全报告与部署者清单 |
| `.gitignore` | Excludes secrets, databases, uploads, builds, caches, and release binaries / 排除敏感和生成文件 |
| `.dockerignore` | Keeps local data and release artifacts out of image layers / 防止本地数据进入镜像 |
| `.editorconfig`, `.gitattributes` | Cross-platform formatting and line endings / 跨平台格式规则 |
| `Dockerfile.unified` | Published all-in-one frontend + API + Nginx image / 官方一体镜像 |
| `Dockerfile.frontend` | Standalone static frontend image / 独立前端镜像 |
| `Dockerfile.backend` | Standalone FastAPI image / 独立后端镜像 |
| `Dockerfile.runtime` | Runtime-only image for externally mounted frontend/backend / 外置代码运行环境镜像 |
| `render.yaml` | Render Blueprint with persistent disk / Render 一键部署配置 |

## `frontend/`

| Path | Responsibility / 职责 |
| --- | --- |
| `package.json` | Dependencies and `cnpm`-compatible scripts / 依赖和脚本 |
| `vite.config.ts` | Build chunks, development proxy, and Vitest / 构建、代理和测试配置 |
| `tsconfig.json`, `src/env.d.ts` | TypeScript and optional API build variable types / TypeScript 配置 |
| `index.html` | Generic non-personalized application shell / 通用入口页面 |
| `vercel.json` | Vercel frontend-only deployment / Vercel 前端部署 |
| `public/favicon.svg` | Generic EvidentFolio mark / 通用图标 |
| `public/pdfjs/` | Vendored PDF.js CMaps, fonts, WASM, and upstream licenses / PDF 中文与渲染资源 |
| `src/main.ts`, `src/App.vue` | Vue bootstrap, global transitions, and toast host / Vue 启动与全局容器 |
| `src/router/` | Lazy public/admin routes, `/en`, auth and first-setup guards / 路由与守卫 |
| `src/api/` | Typed HTTP clients for public, admin, upload, and SSE APIs / API 封装 |
| `src/stores/` | Pinia auth, site, locale, and toast state / 全局状态 |
| `src/i18n/` | Fixed Chinese/English UI message packages / 固定界面语言包 |
| `src/types/` | Shared TypeScript domain contracts / 领域类型 |
| `src/layouts/` | Independent public and admin shells / 公开端与后台布局 |
| `src/views/public/` | Home, project, résumé, credential, contact, and asset pages / 公开页面 |
| `src/views/admin/` | Dashboard and all content/settings/analytics editors / 后台页面 |
| `src/components/public/` | Header, footer, project cards, coding and pointer interactions / 公开组件 |
| `src/components/admin/` | Folder-aware reusable resource picker / 后台资源选择器 |
| `src/components/content/` | PDF viewer, Markdown renderer, and image lightbox / 内容预览组件 |
| `src/components/icons/`, `src/icons/` | Uploaded SVG/image icons and searchable icon registry / 图标系统 |
| `src/components/ui/` | Shared select, loading, empty, and error states / 通用状态组件 |
| `src/composables/` | Async state, metadata, and analytics behavior / 组合式逻辑 |
| `src/directives/` | Reduced-motion-aware reveal behavior / 入场动画指令 |
| `src/utils/` | Clone safety, retry, labels, image recovery, and SSE parsing / 通用工具 |
| `src/styles/` | Design tokens, responsive layouts, motion, and accessibility / 全局视觉系统 |

## `backend/`

| Path | Responsibility / 职责 |
| --- | --- |
| `requirements.txt`, `pyproject.toml` | Python dependencies and test/lint settings / Python 依赖与质量配置 |
| `alembic.ini`, `alembic/` | Ordered, non-destructive schema migrations / 数据库迁移 |
| `entrypoint.sh` | Standalone API preflight → migration → postflight → Uvicorn / 后端启动链 |
| `app/main.py` | FastAPI lifecycle, middleware, errors, health, sitemap, and routers / API 入口 |
| `app/startup.py` | Writable/integrity checks and revision-based SQLite backup / 启动检查与迁移备份 |
| `app/core/` | Python configuration loading, SQLite engine, UTC time, and logs / 基础设施 |
| `app/models/` | SQLAlchemy entities and relationships / 数据模型 |
| `app/schemas/` | Pydantic request/response contracts / API Schema |
| `app/repositories/` | Query and persistence operations / 数据访问 |
| `app/services/` | Auth, project, serializer, and AI business logic / 业务服务 |
| `app/api/routes/` | Public, auth, admin, analytics, and AI endpoints / HTTP 路由 |
| `app/api/dependencies.py` | Session, CSRF, and admin guards / 权限依赖 |
| `app/api/response.py`, `audit.py` | Unified envelopes, errors, and audit writes / 统一响应与审计 |
| `app/file_processing/` | Validation, thumbnails, metadata, safe Office/ZIP/text previews / 文件处理 |
| `app/analytics/` | Event recording, geolocation, aggregation, and scoring / 访问分析 |
| `app/security/` | Trusted-proxy/IP and SVG sanitization / 网络与 SVG 安全 |
| `app/classify_assets.py` | Optional operator utility for organizing existing assets / 资源整理工具 |
| `tests/` | Auth, CRUD, media, analytics, security, i18n, AI, and migration tests / 后端测试 |

## `deploy/`, `docs/`, data paths

| Path | Responsibility / 职责 |
| --- | --- |
| `deploy/config/config.example.py` | Source/external-runtime Python configuration template / Python 配置模板 |
| `deploy/config/config.container.py` | Environment-backed config embedded in the all-in-one image / 一体镜像配置 |
| `deploy/nginx/` | SPA, API proxy, MIME, caching, Range, and security headers / Nginx 配置 |
| `deploy/supervisor/` | Runs one API worker and Nginx / 进程管理 |
| `deploy/*entrypoint.sh` | Startup checks and automatic Alembic migration / 自动迁移入口 |
| `deploy/backup.ps1`, `restore.ps1` | Local backup and restore helpers / 备份恢复脚本 |
| `deploy/run.ps1`, `stop.ps1` | Windows Docker helpers / Windows 容器脚本 |
| `docs/API*.md` | API usage and conventions / API 文档 |
| `docs/ARCHITECTURE.md` | Runtime, data, security, and module boundaries / 架构说明 |
| `docs/DEPLOYMENT*.md` | English/Chinese installation, update, and rollback guides / 中英文部署指南 |
| `docs/images/` | Sanitized documentation screenshots only / 脱敏文档截图 |
| `data/` | Ignored SQLite database and migration backups / 被忽略的数据库目录 |
| `uploads/` | Ignored UUID media tree / 被忽略的上传目录 |
| `release/` | Ignored local release binaries generated without dates in names / 本地发布产物 |
| `scripts/` | Reproducible release packaging helpers / 发布脚本 |
| `.github/` | CI, Docker publishing, Issue/PR templates, and dependency updates / GitHub 自动化 |
