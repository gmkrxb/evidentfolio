export function readingProgress(scrollTop: number, contentTop: number, contentBottom: number, viewport: number, inset: number) {
  const start = Math.max(0, contentTop - inset)
  const end = Math.max(start + 1, contentBottom - viewport + 32)
  return Math.min(1, Math.max(0, (scrollTop - start) / (end - start)))
}
