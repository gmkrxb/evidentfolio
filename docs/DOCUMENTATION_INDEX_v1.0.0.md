# EvidentFolio 文档目录说明

- **目录**：`docs/`
- **组件**：Documentation
- **组件说明版本**：1.0.0
- **对应项目版本**：EvidentFolio 1.0.0

## 职责

该目录集中保存架构、API、部署、项目结构以及文档截图等长期维护资料。根目录 `README.md` 负责快速入口，`docs/` 负责完整技术说明。

## 文档索引

- `ARCHITECTURE.md`：系统架构、运行边界、数据与安全设计。
- `API.md` / `API.en.md`：中英文 API 使用说明。
- `DEPLOYMENT.zh-CN.md` / `DEPLOYMENT.md`：中英文部署、升级与回滚说明。
- `PROJECT_STRUCTURE.md`：仓库目录与文件职责映射。
- `images/`：经过脱敏的项目文档截图。

## 维护原则

代码行为变化但文档未同步会产生更大的维护成本。涉及 API、配置项、启动流程、目录职责、迁移策略或部署方式的变更，应在同一 PR 中更新对应文档。

## 版本约定

该文档索引对应 EvidentFolio 1.0.0。单个文档可持续更新，但涉及发行版可见行为变化时应同时更新 `CHANGELOG.md`。
