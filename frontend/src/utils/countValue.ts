export interface CountValue {
  number: number
  format: (value: number) => string
}

/**
 * 解析「90.67%」「4,703」「72K」「20Hz+」「1.2 万」这类展示数值。
 * 逗号后正好三位数字视为千分位；只有一个数字段的文本才参与计数动画。
 */
export function parseCountValue(text: string): CountValue | null {
  const match = text.match(/^(\D*?)(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(\D*)$/)
  if (!match) return null
  const [, prefix = '', raw = '', suffix = ''] = match
  const grouped = raw.includes(',')
  const number = Number(raw.replace(/,/g, ''))
  if (!Number.isFinite(number)) return null
  const decimals = (raw.split('.')[1] || '').length
  const formatter = new Intl.NumberFormat('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals, useGrouping: grouped })
  return { number, format: (value: number) => `${prefix}${formatter.format(value)}${suffix}` }
}
