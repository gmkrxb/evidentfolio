# EvidentFolio 前端应用说明

- **目录**：`frontend/`
- **组件**：Frontend Application
- **组件说明版本**：1.0.0
- **对应项目版本**：EvidentFolio 1.0.0

## 职责

该目录包含公开作品集站点与管理后台的 Vue 3 + TypeScript 前端，实现路由、状态管理、国际化、内容编辑、媒体展示、PDF 浏览、访问分析交互和多端响应式界面。

## 主要入口

- `src/main.ts`：Vue 应用启动入口。
- `src/router/`：公开端、管理端与鉴权路由。
- `src/views/public/`：公开作品集页面。
- `src/views/admin/`：后台管理页面。
- `src/api/`：类型化 API 客户端。
- `src/stores/`：Pinia 状态。
- `src/i18n/`：中英文固定界面文案。
- `public/pdfjs/`：PDF.js 运行资源。
- `vite.config.ts`：Vite、Vitest 与开发代理配置。

## 开发与检查

```bash
cnpm install
cnpm run type-check
cnpm run test
cnpm run build
```

默认开发代理将 `/api` 转发到 `127.0.0.1:8000`；前后端分离部署时使用构建变量配置 API 基地址，不应在源码内硬编码域名。

## 版本约定

本说明与 EvidentFolio 1.0.0 对应。发生公开路由、管理界面、前端 API 契约或构建流程变化时，应同步更新该说明与变更记录。
