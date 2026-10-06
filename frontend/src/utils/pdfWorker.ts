// PDF Worker 入口：先补齐运行环境，再加载 pdf.js 的解析线程。
import './pdfPolyfills'
import 'pdfjs-dist/build/pdf.worker.min.mjs'
