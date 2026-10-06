/**
 * 把后台设置的品牌图标同步为浏览器标签页图标（favicon）与主屏图标；
 * 未上传图标时，用品牌文字生成一枚陶土色「印章」SVG。
 */
function linkFor(rel: string) {
  let link = document.head.querySelector<HTMLLinkElement>(`link[rel="${rel}"]`)
  if (!link) {
    link = document.createElement('link')
    link.rel = rel
    document.head.appendChild(link)
  }
  return link
}

function escapeXml(text: string) {
  return text.replace(/[<>&"']/g, (char) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;', "'": '&apos;' }[char]!))
}

export function sealIcon(mark: string) {
  const text = escapeXml(Array.from(mark.trim() || 'P').slice(0, 2).join(''))
  const size = Array.from(text).length > 1 ? 26 : 38
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="15" fill="#c96a48"/><text x="32" y="${size > 30 ? 45 : 41}" text-anchor="middle" font-family="Songti SC, STSong, Georgia, serif" font-size="${size}" fill="#fbf6ee">${text}</text></svg>`
  return `data:image/svg+xml,${encodeURIComponent(svg)}`
}

export function applySiteIcon(options: { iconUuid?: string | null; mark?: string | null }) {
  const href = options.iconUuid ? `/api/v1/public/assets/${options.iconUuid}/thumbnail` : sealIcon(options.mark || '')
  const type = options.iconUuid ? 'image/webp' : 'image/svg+xml'
  const icon = linkFor('icon')
  if (icon.href !== new URL(href, location.href).href) {
    icon.href = href
    icon.type = type
  }
  const touch = linkFor('apple-touch-icon')
  touch.href = options.iconUuid ? href : '/favicon.svg'
}

export function applyThemeColor() {
  let meta = document.head.querySelector<HTMLMetaElement>('meta[name="theme-color"]')
  if (!meta) {
    meta = document.createElement('meta')
    meta.name = 'theme-color'
    document.head.appendChild(meta)
  }
  meta.content = getComputedStyle(document.documentElement).getPropertyValue('--color-bg').trim() || '#f3efe7'
}
