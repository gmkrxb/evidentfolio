# EvidentFolio 发布脚本说明

- **目录**：`scripts/`
- **组件**：发布工具
- **组件说明版本**：1.0.0
- **对应项目版本**：EvidentFolio 1.0.0

## 目录职责

该目录保存可重复执行的发布打包辅助脚本，用于生成本地发行产物，并保持 Windows PowerShell 与 Unix Shell 的基本发布流程一致。

## 主要脚本

- `build-release.ps1`：Windows / PowerShell 发布打包入口。
- `build-release.sh`：Linux / macOS Shell 发布打包入口。

## 使用原则

- 发布产物应写入被 Git 忽略的 `release/`，不直接提交二进制包。
- 发行包名称应使用语义化版本，而不是构建日期作为版本标识。
- 正式发布前应先通过前端、后端和容器 CI 检查。
- 打包脚本发生行为变化时，应核对 Docker、文档和 `CHANGELOG.md` 是否需要同步修改。

## 版本约定

本说明对应 EvidentFolio 1.0.0。发布脚本的变更不应自行制造独立产品版本；正式发行版本仍以 Git Tag 与根目录变更记录为准。
