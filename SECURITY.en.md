# Security Policy

[简体中文](SECURITY.md)

## Supported versions

Security fixes are provided for the latest release. Please upgrade before reporting an issue already fixed on `main`.

## Private reporting

Do not open a public issue for authentication bypass, private asset access, upload execution, path traversal, secret exposure, CSRF, or visitor-data leakage. Use GitHub's **Report a vulnerability** feature in the Security tab. Include the affected version, reproduction steps, impact, and a minimal proof of concept without real personal data.

Please allow reasonable time for triage and a coordinated release. Do not access data you do not own.

## Operator responsibilities

- Generate a unique secret of at least 32 random characters.
- Use HTTPS and secure cookies in production.
- Restrict trusted hosts, proxy IPs, CORS origins, upload types, and upload size.
- Back up both the SQLite database and uploads.
- Keep Nginx, Python dependencies, ffmpeg, and the container base image updated.
- Disclose analytics and IP geolocation as required by the laws applicable to your deployment.
