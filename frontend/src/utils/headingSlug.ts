/** 与 GitHub、Typora、VS Code 的 Markdown 目录一致的标题锚点：小写、去标点、空格变连字符。 */
export function headingSlug(text: string) {
  return text
    .trim()
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\p{M}\s_-]/gu, '')
    .replace(/\s/g, '-')
}
