# PDF.js runtime data

`cmaps/`、`standard_fonts/` 和 `wasm/` 从项目依赖 `pdfjs-dist@6.2.108`
复制，用于离线部署时的中文 CMap、标准字体回退和 PDF 解码。它们随前端静态资源
一起部署，不依赖 CDN。PDF.js 按 Apache License 2.0 发布，完整许可随
`pdfjs-dist` 依赖包提供。
