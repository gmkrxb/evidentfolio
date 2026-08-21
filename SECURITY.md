# Security Policy / 安全策略

## Supported versions / 支持版本

Security fixes are provided for the latest release. Please upgrade before reporting an issue already fixed on `main`.

安全修复面向最新版本。报告问题前请先确认 `main` 分支或最新镜像中是否已经修复。

## Private reporting / 私下报告

Do not open a public issue for authentication bypass, private asset access, upload execution, path traversal, secret exposure, CSRF, or visitor-data leakage. Use GitHub's **Report a vulnerability** feature in the Security tab. Include affected version, reproduction steps, impact, and a minimal proof of concept without real personal data.

认证绕过、私有资源越权、上传执行、路径穿越、密钥泄漏、CSRF 或访客数据泄漏请勿提交公开 Issue。请通过 GitHub Security 页面中的 **Report a vulnerability** 私下报告，并提供受影响版本、复现步骤、影响范围和不包含真实个人数据的最小示例。

Please allow reasonable time for triage and a coordinated release. Do not access data you do not own.

请为确认和协调发布预留合理时间，不要访问不属于你的数据。

## Operator responsibilities / 部署者责任

- Generate a unique secret of at least 32 random characters.
- Use HTTPS and secure cookies in production.
- Restrict trusted hosts, proxy IPs, CORS origins, upload types, and upload size.
- Back up both the SQLite database and uploads.
- Keep Nginx, Python dependencies, ffmpeg, and the container base image updated.
- Disclose analytics and IP geolocation as required by the laws applicable to your deployment.

- 使用至少 32 位随机字符生成唯一密钥；
- 生产环境启用 HTTPS 和安全 Cookie；
- 收紧可信域名、代理 IP、CORS、上传类型和大小；
- 同时备份 SQLite 数据库与上传目录；
- 更新 Nginx、Python 依赖、ffmpeg 和容器基础镜像；
- 根据部署所在地适用法律披露访问分析与 IP 地理位置处理。
