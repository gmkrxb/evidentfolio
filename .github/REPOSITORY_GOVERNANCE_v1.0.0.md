# EvidentFolio 仓库治理与分支保护说明

- **目录**：`.github/`
- **组件**：Repository Governance
- **组件说明版本**：1.0.0
- **对应项目版本**：EvidentFolio 1.0.0

## 职责

该目录保存 GitHub Actions、Issue 模板、Pull Request 模板、Dependabot 配置，以及仓库协作和主分支治理规则。

## 当前 CI

`.github/workflows/ci.yml` 对 Pull Request 和 `main` 推送运行以下三个检查：

- `frontend`：TypeScript 类型检查、Vitest 与 Vite 构建。
- `backend`：Python 依赖安装与 Pytest。
- `image`：构建 `Dockerfile.unified` 的 linux/amd64 镜像。

## 建议的 main 分支保护

在 GitHub 仓库 **Settings → Rules → Rulesets** 中为 `main` 创建规则，建议至少启用：

1. Require a pull request before merging。
2. Require status checks to pass before merging。
3. 将 `frontend`、`backend`、`image` 设为必需检查。
4. Block force pushes。
5. Restrict deletions / Block deletions。
6. Require conversation resolution before merging。
7. 对管理员是否允许 bypass 按维护需求决定；个人仓库建议尽量减少 bypass。

启用后，仓库首页的 “Your main branch isn't protected” 提示应消失。

## 版本约定

CI job 名称、PR 流程、Dependabot 或分支治理规则发生变化时，应同步更新本说明，避免保护规则引用已经不存在的检查名称。
