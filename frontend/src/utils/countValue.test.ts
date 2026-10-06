import { describe, expect, it } from 'vitest'
import { parseCountValue } from './countValue'

describe('parseCountValue', () => {
  it('keeps thousands separators instead of turning them into decimals', () => {
    const value = parseCountValue('4,703')!
    expect(value.number).toBe(4703)
    expect(value.format(4703)).toBe('4,703')
    expect(value.format(1200)).toBe('1,200')
  })
  it('keeps decimals, prefixes and suffixes', () => {
    expect(parseCountValue('90.67%')!.format(90.67)).toBe('90.67%')
    expect(parseCountValue('20Hz+')!.format(20)).toBe('20Hz+')
    expect(parseCountValue('72K')!.number).toBe(72)
    expect(parseCountValue('Top 32')!.format(32)).toBe('Top 32')
  })
  it('leaves non-numeric or multi-number text alone', () => {
    expect(parseCountValue('Full Stack')).toBeNull()
    expect(parseCountValue('2024–2026')).toBeNull()
  })
})
