# EvidentFolio 仓库治理与主分支保护说明

- **目录**：`.github/`
- **组件**：仓库治理与自动化
- **组件说明版本**：1.0.0
- **对应项目版本**：EvidentFolio 1.0.0
- **默认文档语言**：简体中文

## 目录职责

该目录保存 GitHub Actions、Issue 模板、Pull Request 模板、Dependabot 配置，以及仓库协作和主分支治理规则。

## 当前 CI

`.github/workflows/ci.yml` 对 Pull Request 和 `main` 推送运行以下三个检查：

- `frontend`：TypeScript 类型检查、Vitest 测试与 Vite 构建。
- `backend`：Python 依赖安装与 Pytest 测试。
- `image`：构建 `Dockerfile.unified` 的 `linux/amd64` 一体镜像。

## `main` 分支 Ruleset 推荐配置

在 GitHub 仓库 **Settings → Rules → Rulesets → New branch ruleset** 中按下表设置。

| 设置项 | 推荐值 | 说明 |
| --- | --- | --- |
| Ruleset Name | `main 分支保护` | 清楚说明规则用途 |
| Enforcement status | `Active` | 创建后立即生效 |
| Bypass list | 留空 | 默认不允许绕过；个人仓库更容易保持规则一致 |
| Target branches | `Include default branch` | 不硬编码分支名，即使以后默认分支改名仍会受保护 |

### 建议开启的规则

- **Restrict deletions**：开启。禁止普通权限直接删除 `main`。
- **Require a pull request before merging**：开启。所有正常修改先进入非目标分支，再通过 PR 合并。
  - 个人仓库的 **Required approvals** 建议设为 `0`，否则只有一个维护者时可能无法满足他人审批要求。
  - 若界面提供 **Require conversation resolution before merging**，建议开启。
- **Require status checks to pass**：开启。
  - 必需检查：`frontend`
  - 必需检查：`backend`
  - 必需检查：`image`
  - 建议开启 **Require branches to be up to date before merging**，确保 PR 基于最新 `main` 重新通过检查。
- **Block force pushes**：开启。禁止强制改写 `main` 历史。

### 建议暂时不要开启的规则

- **Restrict creations**：关闭。没有必要限制目标分支创建，删除本身已经被限制。
- **Restrict updates**：关闭。该规则会把目标分支更新限制给 bypass 用户，不适合作为常规 PR 合并保护。
- **Require deployments to succeed**：关闭。当前仓库没有作为合并门禁的 GitHub Environment 部署流程。
- **Require signed commits**：暂时关闭。只有确认维护者、自动化和机器人提交均使用可验证签名后再启用。
- **Require code scanning results**：暂时关闭。先配置 CodeQL 或其他代码扫描工具再启用。
- **Require code quality results**：暂时关闭。先确认仓库已经启用对应 GitHub Code Quality 分析。
- **Restrict code coverage**：暂时关闭。当前 CI 未上传可用于 Ruleset 判断的覆盖率结果。
- **Automatically request Copilot code review**：可选，默认关闭；它不是主分支保护的必要条件。

### 可选：线性历史

**Require linear history** 可以开启，但开启后 `main` 不能接收 merge commit，只能使用 squash merge 或 rebase merge。若希望保持一条线性的提交历史，建议同时在仓库合并设置中以 **Squash merge** 为主要方式；如果仍需要普通 merge commit，则不要开启该规则。

## 文档语言约定

仓库默认文档语言为简体中文：

- 不带语言后缀的 Markdown 文档默认使用中文。
- 英文补充文档统一使用 `.en.md`。
- 目录说明、文件职责说明、Issue/PR 说明和仓库治理说明优先使用中文。
- 原有 `.zh-CN.md` 文件可作为旧链接兼容入口保留。

## 版本约定

CI job 名称、PR 流程、Dependabot 或分支治理规则发生变化时，应同步更新本说明，避免保护规则引用已经不存在的检查名称。
