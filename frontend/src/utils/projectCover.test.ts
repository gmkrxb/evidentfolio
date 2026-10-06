import { expect, test } from 'vitest'
import type { Asset } from '@/types'
import { coverLayout, projectCoverAssets } from './projectCover'

test('一至四图铺满容器，图块不重叠，也不越界', () => {
  const images = [{ width: 1800, height: 600 }, { width: 600, height: 1400 }, { width: 900, height: 900 }, { width: null, height: null }]
  for (const aspect of [.7, 1, 1.9, 3]) {
    for (let count = 1; count <= 4; count++) {
      const tiles = coverLayout(images.slice(0, count), aspect)
      expect(tiles).toHaveLength(count)
      expect(tiles.reduce((area, tile) => area + tile.width * tile.height, 0)).toBeCloseTo(1)
      for (const tile of tiles) {
        expect(tile.x).toBeGreaterThanOrEqual(0)
        expect(tile.y).toBeGreaterThanOrEqual(0)
        expect(tile.x + tile.width).toBeLessThanOrEqual(1.00001)
        expect(tile.y + tile.height).toBeLessThanOrEqual(1.00001)
        expect(tile.width * tile.height).toBeGreaterThan(.09)
        for (const other of tiles.filter(other => other.index > tile.index)) {
          const width = Math.max(0, Math.min(tile.x + tile.width, other.x + other.width) - Math.max(tile.x, other.x))
          const height = Math.max(0, Math.min(tile.y + tile.height, other.y + other.height) - Math.max(tile.y, other.y))
          expect(width * height).toBeCloseTo(0)
        }
      }
    }
  }
})

test('横图上下排、竖图左右排，避免等分网格的大幅裁切', () => {
  const wide = coverLayout([{ width: 200, height: 100 }, { width: 200, height: 100 }], 1)
  expect(wide.every(tile => tile.width === 1 && tile.height === .5)).toBe(true)
  const tall = coverLayout([{ width: 100, height: 200 }, { width: 100, height: 200 }], 1)
  expect(tall.every(tile => tile.height === 1 && tile.width === .5)).toBe(true)
})

test('封面优先，合并自动组图，排除同文件和非公开图片', () => {
  const asset = (uuid: string, sha256 = uuid, is_public = true) => ({ uuid, sha256, is_public, mime_type: 'image/png' } as Asset)
  const cover = asset('cover')
  expect(projectCoverAssets({ cover_asset: cover, auto_cover_assets: [asset('copy', 'cover'), asset('private', 'private', false), asset('two'), asset('three'), asset('four'), asset('five')] }).map(item => item.uuid)).toEqual(['cover', 'two', 'three', 'four'])
})
