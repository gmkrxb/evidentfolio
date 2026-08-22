# EvidentFolio 部署工具说明

- **目录**：`deploy/`
- **组件**：Deployment Toolkit
- **组件说明版本**：1.0.0
- **对应项目版本**：EvidentFolio 1.0.0

## 职责

该目录保存容器与源码部署所需的运行配置、Nginx 配置、Supervisor 配置、启动脚本，以及 Windows 环境下的运行、停止、备份和恢复辅助脚本。

## 主要内容

- `config/config.example.py`：源码或外置运行环境的配置模板。
- `config/config.container.py`：一体化容器使用的环境变量配置。
- `nginx/`：静态资源、SPA fallback、API 反代、缓存、Range 与安全响应头。
- `supervisor/`：API 与 Nginx 进程编排。
- `unified-entrypoint.sh`：一体镜像启动入口。
- `runtime-entrypoint.sh`：外置代码运行环境入口。
- `run.ps1` / `stop.ps1`：Windows Docker 启停辅助。
- `backup.ps1` / `restore.ps1`：本地数据备份与恢复辅助。

## 部署原则

生产环境应持久化 `data/` 与 `uploads/`，固定并妥善保存 `EVIDENTFOLIO_SECRET_KEY`，正确配置可信 Host、HTTPS Cookie 与代理网络。

## 版本约定

部署脚本、容器布局、挂载路径或启动检查流程变化时，应同步更新该文件、根 README 和 `docs/DEPLOYMENT*.md`。
