import type { Asset, Project } from '@/types'

export type CoverTile = { index: number; x: number; y: number; width: number; height: number }
type Layout = { cost: number; tiles: CoverTile[] }

export function projectCoverAssets(project: Pick<Project, 'cover_asset' | 'auto_cover_assets'>): Asset[] {
  const seen = new Set<string>()
  return [project.cover_asset, ...(project.auto_cover_assets || [])].filter((asset): asset is Asset => {
    if (!asset || !asset.mime_type.startsWith('image/') || !asset.is_public) return false
    // 仅可查看且没有缩略图的图片不能作为封面直接引用
    if (asset.protected && !asset.thumbnail_url) return false
    const identity = asset.sha256 || asset.uuid
    if (seen.has(identity)) return false
    seen.add(identity)
    return true
  }).slice(0, 4)
}

export function coverImageUrl(asset: Asset) {
  return asset.thumbnail_url || `${asset.content_url}?v=${asset.sha256?.slice(0, 16) || asset.version}`
}

export function coverLayout(images: Array<Pick<Asset, 'width' | 'height'>>, aspect: number): CoverTile[] {
  if (!images.length) return []
  const frame = Number.isFinite(aspect) && aspect > 0 ? aspect : 1.6
  const ratios = images.slice(0, 4).map(image => image.width && image.height && image.width > 0 && image.height > 0 ? image.width / image.height : 1.5)
  // 搜索横排、竖排和主次拼图，优先减少裁切并避免过小的图块。
  function fit(indices: number[], x: number, y: number, width: number, height: number): Layout {
    if (indices.length === 1) {
      const index = indices[0]!, ratio = ratios[index]!, target = frame * width / height
      const area = width * height, retained = Math.min(ratio / target, target / ratio)
      const cost = area * (1 - retained) + Math.max(0, .14 - area) * 2 + Math.max(0, .22 - Math.min(width, height))
      return { cost, tiles: [{ index, x, y, width, height }] }
    }
    let best: Layout = { cost: Infinity, tiles: [] }
    for (let split = 1; split < indices.length; split++) {
      const first = indices.slice(0, split), second = indices.slice(split)
      for (const horizontal of [true, false]) {
        const weight = (items: number[]) => items.reduce((sum, index) => sum + (horizontal ? ratios[index]! : 1 / ratios[index]!), 0)
        const natural = Math.max(.28, Math.min(.72, weight(first) / weight(indices)))
        for (const portion of new Set([1 / 3, .5, 2 / 3, natural])) {
          const a = horizontal ? fit(first, x, y, width * portion, height) : fit(first, x, y, width, height * portion)
          const b = horizontal ? fit(second, x + width * portion, y, width * (1 - portion), height) : fit(second, x, y + height * portion, width, height * (1 - portion))
          const cost = a.cost + b.cost
          if (cost < best.cost) best = { cost, tiles: [...a.tiles, ...b.tiles] }
        }
      }
    }
    return best
  }
  return fit(ratios.map((_, index) => index), 0, 0, 1, 1).tiles.sort((a, b) => a.index - b.index)
}
