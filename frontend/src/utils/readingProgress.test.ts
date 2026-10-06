import { expect, test } from 'vitest'
import { readingProgress } from './readingProgress'

test('进度从正文开始计算，正文读完即完成，不计页头页尾', () => {
  expect(readingProgress(0, 600, 2800, 800, 160)).toBe(0)
  expect(readingProgress(440, 600, 2800, 800, 160)).toBe(0)
  expect(readingProgress(1236, 600, 2800, 800, 160)).toBe(.5)
  expect(readingProgress(2032, 600, 2800, 800, 160)).toBe(1)
  expect(readingProgress(4000, 600, 2800, 800, 160)).toBe(1)
})

test('短文章与浏览器过度滚动不会产生无效或超范围的进度', () => {
  expect(readingProgress(-80, 200, 500, 800, 160)).toBe(0)
  expect(readingProgress(41, 200, 500, 800, 160)).toBe(1)
})
