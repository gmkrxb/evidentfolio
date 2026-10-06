import { describe, expect, it } from 'vitest'
import { headingSlug } from './headingSlug'

describe('headingSlug', () => {
  it('matches common Markdown table-of-contents anchors', () => {
    expect(headingSlug('5. 接口设计')).toBe('5-接口设计')
    expect(headingSlug('10. 扩展性设计')).toBe('10-扩展性设计')
    expect(headingSlug('API Gateway & Auth')).toBe('api-gateway--auth')
    expect(headingSlug('  Hello, World!  ')).toBe('hello-world')
  })
})
