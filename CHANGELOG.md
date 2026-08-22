# 更新记录

本项目的重要变更遵循 [Keep a Changelog](https://keepachangelog.com/) 的组织方式，并使用语义化版本管理。

## [未发布]

### 文档

- 将仓库默认 `README.md` 调整为中文，并将完整英文说明迁移到 `README.en.md`。
- 保留 `README.zh-CN.md` 作为旧链接兼容入口。
- 将 `CONTRIBUTING.md`、`SECURITY.md`、`CODE_OF_CONDUCT.md`、`docs/ARCHITECTURE.md`、`docs/DEPLOYMENT.md`、`docs/PROJECT_STRUCTURE.md` 统一为中文默认文档。
- 为对应英文文档增加 `.en.md` 文件，并修正英文 README 的内部链接。
- 为 `.github/`、`backend/`、`data/`、`deploy/`、`docs/`、`frontend/`、`scripts/` 增加独立命名、带版本号的中文目录职责说明。
- 明确仓库约定：不带语言后缀的 Markdown 默认使用简体中文，英文版本使用 `.en.md`。
- 增加 `main` 分支 Ruleset 推荐配置，并将 `frontend`、`backend`、`image` 列为必需 CI 检查。

## [1.0.0] - 2026-08-21

### 新增

- 以证据为核心的公开作品集与案例研究展示。
- 项目、分类、资源、文件夹、相册、简历、证书、设置、分析和审计管理。
- 中英文路由、界面语言包以及数据库驱动的内容翻译。
- OpenAI 兼容模型配置、流式翻译与简历解析。
- 一体 Docker、外置运行环境、Render、Vercel 前端和源码部署路径。
- SQLite 启动完整性检查、自动 Alembic 升级与迁移前备份。

### 调整

- 开源安装首次启动保持完全空白，并进入一次性初始化流程。
- 软件包和镜像名称不再使用构建日期作为版本，正式版本由语义化版本号与 Git Tag 标识。

### 安全

- 源码和镜像不包含维护者简历、项目数据库、上传媒体、API Key 或访客记录。
