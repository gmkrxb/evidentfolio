# EvidentFolio API

[English](API.en.md)

所有业务接口使用 `/api/v1` 前缀，成功响应均为：

```json
{
  "success": true,
  "data": {},
  "message": null,
  "request_id": "request-uuid"
}
```

错误响应包含稳定错误码、可读消息、字段错误（如适用）和请求 ID，不返回堆栈或服务器文件路径。运行后可在 `/api/docs` 查看 OpenAPI UI，在 `/api/openapi.json` 获取机器可读文档。

## 公开接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/public/site` | 网站设置、分类和标签 |
| GET | `/public/projects` | 已发布项目，支持 `q/category/tags/featured/sort/page/page_size` |
| GET | `/public/projects/{uuid}` | 已发布项目案例研究 |
| GET | `/public/assets/{uuid}` | 公开资源元信息 |
| GET | `/public/assets/{uuid}/preview` | DOCX/XLSX/PPTX 安全文本结构或 ZIP 文件目录 |
| GET | `/public/assets/{uuid}/content` | 资源内容，支持 HTTP Range |
| GET | `/public/assets/{uuid}/download` | 下载资源 |
| GET | `/public/assets/{uuid}/thumbnail` | 缩略图 |
| GET | `/public/resumes` | 公开简历版本 |
| GET | `/public/resumes/{uuid}` | 简历详情 |
| GET | `/public/certificates` | 公开证书、奖学金与竞赛荣誉 |
| GET | `/public/certificates/{uuid}` | 公开证书详情 |
| POST | `/analytics/events` | 批量上报匿名访问事件（最多 50 条） |
| GET | `/setup/status` | 是否需要首次初始化 |
| POST | `/setup/initialize` | 只在没有管理员时开放 |

## 管理接口

管理接口使用 HttpOnly `portfolio_session` Cookie。所有修改操作还要求 `portfolio_csrf` Cookie 的值通过 `X-CSRF-Token` 请求头回传。

- `/admin/auth/login`、`/logout`、`/me`
- `/admin/dashboard`
- `/admin/projects` 与项目复制、批量状态接口
- `/admin/categories`、`/admin/tags`、标签合并
- `/admin/assets`、上传、批量上传、项目关联
- `/admin/resumes`
- `/admin/certificates`（证书文件、图标与项目关联）
- `/admin/settings`
- `/admin/analytics/overview`、访客会话与数据清理
- `/admin/audit-logs`

## UUID 与资源权限

连续整数 ID 不会出现在外部 URL 或 API。公开资源按稳定 UUID 访问；私有资源即使知道 UUID 也会返回 404。数据库路径和物理 `storage_name` 不向前端暴露。UUID 只用于降低枚举概率，权限仍由服务端会话与资源公开状态决定。

项目详情响应中的 `albums` 保存项目相册，`sections` 可使用 `text/single/gallery/carousel/album/video/audio/attachments/mixed` 展示模式。未设置固定 `cover_asset` 时，`auto_cover_assets` 会在每次请求中根据当前项目图片实时计算，媒体关联变化后不需要手工重新生成封面。

资源支持图片、MP4/WebM、MP3/WAV/OGG/M4A、PDF、安全文本、DOCX/XLSX/PPTX 与 ZIP。Office 和 ZIP 预览不会执行宏、脚本或解压附件；无法安全解释的格式只提供元信息和下载。

## 分析语义

系统记录的是匿名/假名化访问行为并生成可解释关注分数。分数规则显示在会话详情中，不能用于识别真实身份，也不等同于录用意向。
