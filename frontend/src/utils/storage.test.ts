import { afterEach, expect, test, vi } from 'vitest'
import { readPreference, writePreference } from './storage'

afterEach(() => vi.restoreAllMocks())
test('浏览器禁用存储时仍能切换会话内偏好', () => {
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new DOMException('Blocked', 'SecurityError') })
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new DOMException('Blocked', 'SecurityError') })
  expect(readPreference('test-private-mode')).toBe(null)
  writePreference('test-private-mode', 'en')
  expect(readPreference('test-private-mode')).toBe('en')
})
