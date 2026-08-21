# EvidentFolio

<p align="center">
  <strong>以证据为核心的个人作品集与案例研究 CMS。</strong><br />
  展示问题、决策、个人贡献和可验证成果，而不只是另一组项目卡片。
</p>

<p align="center">
  <a href="README.md">English</a> ·
  在线演示 ·
  <a href="docs/DEPLOYMENT.zh-CN.md">部署指南</a> ·
  <a href="CONTRIBUTING.zh-CN.md">参与贡献</a>
</p>

<p align="center">
  <a href="https://github.com/gmkrxb/evidentfolio/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/gmkrxb/evidentfolio/actions/workflows/ci.yml/badge.svg" /></a>
  <a href="https://github.com/gmkrxb/evidentfolio/stargazers"><img alt="GitHub Stars" src="https://img.shields.io/github/stars/gmkrxb/evidentfolio?style=flat-square" /></a>
  <a href="https://hub.docker.com/r/gmkrxb/evidentfolio"><img alt="Docker Pulls" src="https://img.shields.io/docker/pulls/gmkrxb/evidentfolio?style=flat-square" /></a>
  <a href="LICENSE"><img alt="MIT License" src="https://img.shields.io/github/license/gmkrxb/evidentfolio?style=flat-square" /></a>
</p>

![EvidentFolio 首页](docs/images/home-desktop.png)

## 为什么做 EvidentFolio？

招聘负责人真正关心的通常不是“你会多少技术名词”，而是：你解决了什么问题、你具体负责什么、你为什么这样设计，以及结果是否有证据支撑。

EvidentFolio 围绕这条阅读路径构建，将高质量公开展示、真实可用的内容与资源后台、可解释的访问关注分析、双语内容和可选 AI 助手组合成一个完全自托管的系统。数据库、简历、证书和上传资源始终由你控制。

## 核心能力

- 案例研究式项目详情：自定义区块、标题层级、图文混排、相册、轮播、附件、证书、链接、成果和统一目录拖拽排序。
- 资源库：多级文件夹、全局搜索、SHA-256 去重、安全预览、删除依赖预检、稳定 UUID 地址、缩略图、视频信息与 Range 请求。
- 多版本简历：PDF.js 逐页渲染、加载进度、缩放、全屏、页码跳转、下载统计及完整中文字体资源。
- 证书与荣誉：图片/PDF 原位展示、灯箱放大，并与项目双向关联。
- 匿名关注分析：访问路径、停留时长、设备、来源、UTM、下载、媒体进度及规则可解释的高关注评分。
- 中英文路由与数据库翻译字段；固定界面文案集中在可扩展语言包中。
- OpenAI 兼容 AI：模型列表拉取、流式双向翻译、简历结构化解析并确认导入草稿。
- HttpOnly Cookie、CSRF、Argon2、登录限流、审计日志、可信代理和安全文件校验。
- SQLite WAL、Alembic 自动迁移、启动完整性检查、迁移前备份、Docker 健康检查、Nginx 缓存和 SPA fallback。
- 隐私安全的空白初次部署：不会写入维护者的简历、项目、证书或个人身份。

## 页面预览

| 公开案例研究 | 项目内容管理 |
| --- | --- |
| ![项目案例](docs/images/project-detail.png) | ![项目编辑器](docs/images/admin-editor.png) |

开源版本首次启动为空白系统；下列网站仅作为维护者自己的成品演示：**demo**。

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 公开端与后台 | Vue 3、TypeScript、Vite、Vue Router、Pinia、CSS Tokens、Lucide / Element Plus Icons |
| API | Python 3.12、FastAPI、Pydantic、SQLAlchemy 2、Uvicorn |
| 数据 | SQLite WAL、Alembic、公开 UUID 标识 |
| 媒体 | Pillow、PyMuPDF、PDF.js、ffmpeg/ffprobe、Nginx Range |
| 安全 | Argon2、HttpOnly Cookie、CSRF、限流、审计、MIME 与路径校验 |
| 部署 | Nginx、Docker、Render Blueprint、可选 Vercel 前端 |

## Docker 快速启动

官方镜像已经包含前端、后端、Nginx、ffmpeg 和运行环境，只需持久化数据库和上传目录：

```bash
mkdir -p evidentfolio/data evidentfolio/uploads
docker run -d --name evidentfolio --restart unless-stopped -p 8080:80 \
  -e EVIDENTFOLIO_SECRET_KEY="$(openssl rand -hex 32)" \
  -e EVIDENTFOLIO_TRUSTED_HOSTS="localhost,127.0.0.1,你的域名" \
  -e EVIDENTFOLIO_SECURE_COOKIES=false \
  -v "$PWD/evidentfolio/data:/app/data" \
  -v "$PWD/evidentfolio/uploads:/app/uploads" \
  gmkrxb/evidentfolio:latest
```

打开 `http://localhost:8080`。空白部署会自动进入 `/admin/login` 初始化页，创建第一个管理员和网站基础身份；管理员存在后，初始化接口立即关闭。

生产 HTTPS 环境请设置 `EVIDENTFOLIO_SECURE_COOKIES=true`，并将真实域名加入 `EVIDENTFOLIO_TRUSTED_HOSTS`。

## 旧数据库自动升级

升级镜像时继续挂载原来的 `data/` 和 `uploads/`。容器每次启动、对外提供服务之前会自动执行：

1. 检查数据库目录和上传目录是否可写；
2. 执行 SQLite `PRAGMA quick_check`；
3. 按当前迁移版本在 `data/migration-backups/` 创建一次性备份；
4. 执行 `alembic upgrade head`；
5. 检查外键和迁移后的数据库版本；
6. 全部通过后才启动单 Worker Uvicorn 与 Nginx。

```bash
docker pull gmkrxb/evidentfolio:latest
docker rm -f evidentfolio
# 使用原来的目录挂载再次执行 docker run
docker logs -f --tail 160 evidentfolio
```

已有项目和设置不会被示例数据覆盖；检查或迁移失败时容器会停止，而不是用半迁移数据库继续运行。备份、回滚、域名、反向代理和分离部署见[完整部署指南](docs/DEPLOYMENT.zh-CN.md)。

## 源码开发

要求 Python 3.12、ffmpeg、Node.js 22+ 和 `cnpm`。

```powershell
# 后端：直接使用当前 Python，不强制创建项目虚拟环境
python -m pip install -r backend/requirements.txt
Copy-Item deploy/config/config.example.py deploy/config/config.py
Set-Location backend
python -m app.startup preflight
python -m alembic -c alembic.ini upgrade head
python -m app.startup postflight
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1

# 另开终端启动前端
Set-Location frontend
cnpm install
cnpm run dev
```

开发服务器自动将 `/api` 代理到 `127.0.0.1:8000`，前端没有硬编码域名。前后端分开托管时，可在构建阶段设置 `VITE_API_BASE_URL`。

## 部署方式

| 方式 | 适合场景 | 持久化方式 |
| --- | --- | --- |
| 官方一体镜像 | 最简单的自托管 | 映射 `/app/data`、`/app/uploads` |
| 自行构建 `Dockerfile.unified` | 需要审计构建过程 | 同上 |
| 前端、后端、运行环境分离包 | 独立更新代码和环境 | 外置前端、后端、数据、上传和 Python 配置 |
| Render Blueprint | 托管式全栈部署 | 必须启用持久磁盘 |
| Vercel 前端 | 为已有 API 部署公开只读前端 | 数据仍位于 API 主机 |
| 直接源码 | 开发或自定义基础设施 | 由 `config.py` 指定路径 |

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/gmkrxb/evidentfolio)
[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/gmkrxb/evidentfolio&root-directory=frontend&env=VITE_API_BASE_URL)

Vercel 不适合直接承载 SQLite 与上传目录，因此这里只提供前端部署；需要同域后台 Cookie 时，请使用一体镜像或自行反代 `/api`。Render 配置使用项目内的持久磁盘 Blueprint。

## 配置方式

项目不依赖 `.env` 文件：

- 官方 Docker 镜像读取 `EVIDENTFOLIO_` 前缀的环境变量，必须设置 `EVIDENTFOLIO_SECRET_KEY`；
- 源码或外置运行环境复制 `deploy/config/config.example.py` 为被 Git 忽略的 `config.py`，再通过 `PORTFOLIO_CONFIG` 指定。

不要提交 `config.py`、AI Key、数据库、上传目录和迁移备份。AI 服务密钥会使用系统 `SECRET_KEY` 加密后再写入数据库。

## 目录、测试与贡献

- [项目目录与文件职责](docs/PROJECT_STRUCTURE.md)
- [系统架构](docs/ARCHITECTURE.md)
- [完整部署指南](docs/DEPLOYMENT.zh-CN.md)
- [API 文档](docs/API.md)
- [贡献规范](CONTRIBUTING.zh-CN.md)
- [安全策略](SECURITY.md)
- [版本记录](CHANGELOG.md)

```bash
cd frontend && cnpm run type-check && cnpm run test && cnpm run build
cd ../backend && pytest
cd .. && docker build --platform linux/amd64 -f Dockerfile.unified -t evidentfolio:local .
```

PR 必须聚焦、可测试、有文档，并且不能包含个人数据库、简历、上传资源或密钥。安全问题请遵循 `SECURITY.md` 私下报告。

## Star 趋势

[![Star History Chart](https://api.star-history.com/svg?repos=gmkrxb/evidentfolio&type=Date)](https://star-history.com/#gmkrxb/evidentfolio&Date)

## 许可证

[MIT](LICENSE) © 2026 Mingke Gu 与 EvidentFolio 贡献者。
