# 系统架构

[English](ARCHITECTURE.en.md)

## 运行链路

```text
浏览器
  └─ Nginx :80
      ├─ Vue SPA 与不可变静态资源
      ├─ /api、/sitemap.xml、/robots.txt → FastAPI :8000
      └─ 受保护缩略图 → 内部 X-Accel 重定向

FastAPI（单 Uvicorn Worker）
  ├─ 路由 → 服务 → 仓储 → SQLAlchemy → SQLite WAL
  ├─ 上传校验 → UUID 存储 → 缩略图 / 元数据
  ├─ HttpOnly Session + CSRF + 审计日志
  └─ 匿名访问分析 → 事件 → 可解释聚合指标
```

发布镜像内同时运行 Nginx 与单个 Uvicorn Worker。单写入实例是明确的设计选择，用于保持 SQLite 的简单性与可移植性，而不是把 SQLite 当作水平扩展数据库使用。

## 模块边界

- `frontend/src/`：公开端与管理端页面、可复用组件、状态管理、组合式逻辑、路由和类型化 API 客户端。
- `backend/app/api`：仅处理 HTTP 层职责，业务行为放在服务层与仓储层。
- `backend/app/models`：定义持久化模型；`schemas`：定义 API 输入输出契约。
- `file_processing`：负责文件校验、缩略图和元数据派生，不向外暴露物理存储路径。
- `analytics`：记录去标识化访问事件，并计算基于规则、可解释的关注指标。
- `security`：集中处理可信代理、客户端 IP、SVG 等安全规则。

## 数据所有权

所有持久数据均位于容器外：

```text
data/portfolio.db       SQLite 数据库
data/migration-backups  按源迁移版本保存的一次性备份
uploads/                UUID 命名的原始文件、缩略图与临时文件
```

删除或替换容器不会删除宿主机绑定目录。首次空白启动只创建空 Schema；之后的启动仅原地迁移已有数据库，不注入演示内容。

## 启动状态机

```text
挂载目录
  → 可写性检查
  → SQLite quick_check
  → 按迁移版本创建备份（仅已有数据库）
  → alembic upgrade head
  → foreign_key_check + ffmpeg 检查
  → Supervisor 启动 API 与 Nginx
  → 健康检查转为 healthy
```

任意步骤失败都会停止启动。旧数据库备份保留在 `data/migration-backups/`，由部署者决定是否回滚。

## 公开标识与文件

数据库内部关系可以使用整数主键，但所有对外可见实体均使用 UUID。资源 URL 通过 UUID 查询后仍需执行权限检查；物理存储路径与原始文件路径不会直接暴露。修改展示名称不会改变公开 URL。

## 国际化

- 固定界面文案：`frontend/src/i18n/messages/zh-CN.ts` 与 `en.ts`。
- 用户内容：数据库中的 JSON 翻译对象。
- 英文公开路由：`/en/...`；用户选择的语言缓存在浏览器中。
- API 错误：根据 `Accept-Language` 本地化，同时避免泄露堆栈信息。

增加新的界面语言需要新增语言包与路由支持；增加新的用户内容语言还需要同步扩展翻译编辑器与序列化器的语言选择逻辑。

## AI 边界

AI 功能可选，并兼容 OpenAI API。服务地址、加密后的密钥和模型由管理后台配置。解析与翻译使用流式输出及结构化 JSON 校验；AI 生成的项目在管理员确认前保持草稿状态。核心作品集能力不依赖任何 AI 服务商。

## 安全假设

- 仅配置过的可信代理可以提供转发后的客户端 IP 请求头。
- 上传的 HTML 或 JavaScript 不会被执行。
- 私有 UUID 资源仍必须经过权限校验，UUID 的不可猜测性不能替代访问控制。
- Docker 绑定目录与备份文件的保护依赖部署主机自身的文件权限。
