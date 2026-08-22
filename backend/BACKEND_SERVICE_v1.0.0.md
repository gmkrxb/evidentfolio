# EvidentFolio 后端服务说明

- **目录**：`backend/`
- **组件**：Backend Service
- **组件说明版本**：1.0.0
- **对应项目版本**：EvidentFolio 1.0.0

## 职责

该目录承载 EvidentFolio 的 FastAPI 后端、数据库模型、业务服务、鉴权、安全校验、分析逻辑、文件处理与 Alembic 数据库迁移。

## 主要入口

- `app/main.py`：FastAPI 应用入口、生命周期、中间件与路由注册。
- `app/startup.py`：启动前后完整性检查、SQLite 检查与迁移备份。
- `app/api/`：公开端、管理端、认证、分析与 AI HTTP API。
- `app/models/`：SQLAlchemy 数据模型。
- `app/services/`：业务逻辑。
- `alembic/`：数据库迁移。
- `tests/`：后端自动化测试。

## 开发与检查

```bash
python -m pip install -r requirements.txt
pytest
```

生产启动前应依次执行 preflight、Alembic migration 与 postflight，避免在数据库状态不完整时提供服务。

## 版本约定

本说明文件的版本与当前公开发行版保持一致。后端发生不兼容 API、Schema 或迁移行为变化时，应同步更新本文件与根目录 `CHANGELOG.md`。
