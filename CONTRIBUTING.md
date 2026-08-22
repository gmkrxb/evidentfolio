# 参与 EvidentFolio 开发

[English](CONTRIBUTING.en.md)

感谢你帮助 EvidentFolio 成为一个重视证据、表达、隐私和长期维护的作品集系统。

## 开始编码之前

- 先搜索已有 Issue 和 Pull Request；
- 大功能、数据结构调整、新依赖或破坏性 API 变更需要先开 Issue 讨论；
- 安全问题按照 [SECURITY.md](SECURITY.md) 私下报告；
- 禁止用真实简历、生产数据库、API Key、访客日志和个人上传文件作为测试数据。

## 分支与提交规范

- 分支：`feat/简短名称`、`fix/简短名称`、`docs/简短名称`、`refactor/简短名称`；
- 提交遵循 Conventional Commits，例如 `feat(assets): add dependency preflight`；
- 每个提交应当可以独立审阅，不要把纯格式化和功能修改混在一起。

## 开发规则

- Python 使用 3.12 和类型标注，路由、服务、仓储、模型与 Schema 保持分层；
- Vue 使用 TypeScript、Composition API、独立 API 层和可复用组件；
- 固定界面文案必须同步维护 `zh-CN.ts` 与 `en.ts`；用户编辑的翻译写入数据库 `translations` 字段；
- 公开 URL 和 API 只使用 UUID，不能泄露数据库整数 ID；
- 数据库修改必须提供 Alembic 迁移，并证明旧数据升级后仍然存在；
- 上传功能必须测试扩展名、MIME、大小、路径穿越和资源权限；
- 动画尊重 `prefers-reduced-motion`，所有操作保留键盘可访问性；
- 未经讨论不要加入第三方 CMS、远程字体或第三方跟踪器。

## 必须通过的检查

```bash
cd frontend
cnpm run type-check
cnpm run test
cnpm run build

cd ../backend
pytest

cd ..
docker build --platform linux/amd64 -f Dockerfile.unified -t evidentfolio:pr .
```

界面修改应附桌面和移动端截图；数据库迁移必须新增“从上一版本升级并验证内容保留”的测试。

## PR 内容要求

1. 问题及用户影响；
2. 修改内容，以及刻意没有修改的边界；
3. 实际执行的验证命令和结果；
4. 相关截图或 API 示例；
5. 数据迁移、安全、可访问性和回滚说明。

包含密钥或个人数据、绕过迁移、削弱文件安全、把登录凭证写入 LocalStorage，或包含无法解释的大量生成代码的 PR 将被拒绝。维护者可以要求先缩小改动范围。

提交贡献即表示你同意使用本项目 MIT 许可证，并遵守[行为准则](CODE_OF_CONDUCT.md)。
