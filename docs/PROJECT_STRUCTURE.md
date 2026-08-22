# 项目目录与文件职责说明

[English](PROJECT_STRUCTURE.en.md)

本页说明仓库内一方代码、顶层目录和主要文件的职责。PDF.js 的 CMap、字体和 WASM 属于上游运行资源，因此按资源组说明，不逐个列出数百个文件。

## 根目录

| 路径 | 职责 |
| --- | --- |
| `README.md` | 默认中文项目入口、能力概览、快速启动与文档导航 |
| `README.en.md` | 英文项目入口 |
| `LICENSE` | MIT 许可证 |
| `CHANGELOG.md` | 语义化版本与变更记录 |
| `CONTRIBUTING.md` | 默认中文贡献与 PR 规范 |
| `CONTRIBUTING.en.md` | 英文贡献与 PR 规范 |
| `CODE_OF_CONDUCT.md` | 社区行为准则 |
| `SECURITY.md` | 漏洞报告规则与部署者安全检查项 |
| `.gitignore` | 排除密钥、数据库、上传资源、构建结果、缓存和发行二进制文件 |
| `.dockerignore` | 防止本地数据和发行产物进入容器构建上下文 |
| `.editorconfig`, `.gitattributes` | 跨平台格式、编码与换行规则 |
| `Dockerfile.unified` | 前端 + API + Nginx 的官方一体镜像 |
| `Dockerfile.frontend` | 独立静态前端镜像 |
| `Dockerfile.backend` | 独立 FastAPI 后端镜像 |
| `Dockerfile.runtime` | 用于外置前后端代码的运行环境镜像 |
| `render.yaml` | 带持久磁盘的 Render Blueprint 配置 |

## `frontend/` 前端目录

| 路径 | 职责 |
| --- | --- |
| `package.json` | 前端依赖、开发、测试与构建脚本 |
| `vite.config.ts` | Vite 构建、开发代理与 Vitest 配置 |
| `tsconfig.json`, `src/env.d.ts` | TypeScript 与可选 API 构建变量类型 |
| `index.html` | 通用、非个人化应用入口页面 |
| `vercel.json` | Vercel 前端独立部署配置 |
| `public/favicon.svg` | EvidentFolio 通用图标 |
| `public/pdfjs/` | PDF.js CMap、字体、WASM 与上游许可证 |
| `src/main.ts`, `src/App.vue` | Vue 启动、全局过渡与消息容器 |
| `src/router/` | 公开端、管理端、`/en`、认证与首次初始化路由守卫 |
| `src/api/` | 公开端、后台、上传与 SSE 的类型化 HTTP 客户端 |
| `src/stores/` | Pinia 认证、站点、语言和消息状态 |
| `src/i18n/` | 固定中英文界面语言包 |
| `src/types/` | 前端共享领域类型定义 |
| `src/layouts/` | 公开端与后台独立布局 |
| `src/views/public/` | 首页、项目、简历、证书、联系与资源页面 |
| `src/views/admin/` | 仪表盘及内容、设置、分析等后台编辑页面 |
| `src/components/public/` | 公开端页头、页脚、项目卡片与交互组件 |
| `src/components/admin/` | 后台可复用资源选择器等管理组件 |
| `src/components/content/` | PDF 查看、Markdown 渲染与图片灯箱 |
| `src/components/icons/`, `src/icons/` | SVG/图片图标及可搜索图标注册表 |
| `src/components/ui/` | 选择器、加载、空状态和错误状态等通用组件 |
| `src/composables/` | 异步状态、页面元数据与分析逻辑 |
| `src/directives/` | 尊重减少动画偏好的入场指令 |
| `src/utils/` | 克隆安全、重试、标签、图片恢复与 SSE 解析等工具 |
| `src/styles/` | 设计变量、响应式布局、动画与可访问性样式 |

目录级说明见 `frontend/FRONTEND_APP_v1.0.0.md`。

## `backend/` 后端目录

| 路径 | 职责 |
| --- | --- |
| `requirements.txt`, `pyproject.toml` | Python 依赖与测试/质量配置 |
| `alembic.ini`, `alembic/` | 按顺序执行、非破坏式数据库迁移 |
| `entrypoint.sh` | 独立 API 的启动检查 → 迁移 → 后置检查 → Uvicorn 链路 |
| `app/main.py` | FastAPI 生命周期、中间件、错误处理、健康检查、站点地图与路由入口 |
| `app/startup.py` | 可写性/完整性检查及按迁移版本生成 SQLite 备份 |
| `app/core/` | Python 配置加载、SQLite 引擎、UTC 时间与日志 |
| `app/models/` | SQLAlchemy 实体与关系 |
| `app/schemas/` | Pydantic 请求/响应数据契约 |
| `app/repositories/` | 查询与持久化操作 |
| `app/services/` | 认证、项目、序列化和 AI 等业务逻辑 |
| `app/api/routes/` | 公开、认证、后台、分析和 AI HTTP 路由 |
| `app/api/dependencies.py` | Session、CSRF 与管理员权限依赖 |
| `app/api/response.py`, `audit.py` | 统一响应、错误与审计写入 |
| `app/file_processing/` | 文件校验、缩略图、元数据与安全预览 |
| `app/analytics/` | 事件记录、地理位置、聚合与评分 |
| `app/security/` | 可信代理、客户端 IP 与 SVG 安全规则 |
| `app/classify_assets.py` | 可选的既有资源整理工具 |
| `tests/` | 认证、CRUD、媒体、分析、安全、国际化、AI 与迁移测试 |

目录级说明见 `backend/BACKEND_SERVICE_v1.0.0.md`。

## `deploy/` 部署目录

| 路径 | 职责 |
| --- | --- |
| `config/config.example.py` | 源码或外置运行环境 Python 配置模板 |
| `config/config.container.py` | 一体镜像内部使用的环境变量配置 |
| `nginx/` | SPA、API 反代、MIME、缓存、Range 与安全响应头配置 |
| `supervisor/` | 单 API Worker 与 Nginx 进程管理 |
| `*entrypoint.sh` | 启动检查与自动 Alembic 迁移入口 |
| `backup.ps1`, `restore.ps1` | 本地数据备份与恢复辅助脚本 |
| `run.ps1`, `stop.ps1` | Windows Docker 启停辅助脚本 |

目录级说明见 `deploy/DEPLOY_TOOLKIT_v1.0.0.md`。

## `docs/` 文档目录

| 路径 | 职责 |
| --- | --- |
| `API.md` | 默认中文 API 使用说明 |
| `API.en.md` | 英文 API 使用说明 |
| `ARCHITECTURE.md` | 默认中文系统架构说明 |
| `ARCHITECTURE.en.md` | 英文系统架构说明 |
| `DEPLOYMENT.md` | 默认中文安装、升级、备份与回滚指南 |
| `DEPLOYMENT.en.md` | 英文部署指南 |
| `DEPLOYMENT.zh-CN.md` | 旧中文链接兼容入口 |
| `PROJECT_STRUCTURE.md` | 默认中文仓库目录与文件职责说明 |
| `PROJECT_STRUCTURE.en.md` | 英文目录与文件职责说明 |
| `images/` | 仅保存经过脱敏的项目文档截图 |

目录级说明见 `docs/DOCUMENTATION_INDEX_v1.0.0.md`。

## `data/` 数据目录

`data/` 用于运行时 SQLite 数据库和迁移备份。真实数据库与备份文件属于部署数据，不属于源码，仓库只保留必要的目录占位。目录级说明见 `data/DATA_RUNTIME_v1.0.0.md`。

## `scripts/` 发布脚本目录

`scripts/` 保存 Windows PowerShell 与 Unix Shell 的可重复发行打包脚本，发行产物写入被 Git 忽略的 `release/`。目录级说明见 `scripts/RELEASE_TOOLING_v1.0.0.md`。

## `.github/` GitHub 自动化与治理目录

`.github/` 保存 CI、Docker 发布工作流、Issue/PR 模板、Dependabot 和仓库治理说明。目录级说明及 `main` 分支保护建议见 `.github/REPOSITORY_GOVERNANCE_v1.0.0.md`。

## 默认文档语言约定

仓库默认文档语言为**简体中文**：

- 不带语言后缀的 Markdown 文档优先作为中文默认入口；
- 英文版本统一使用 `.en.md`；
- 已存在的 `.zh-CN.md` 可以作为兼容旧链接的跳转入口；
- 目录说明、文件职责说明和仓库治理说明均以中文描述为默认。
