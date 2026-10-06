import { beforeEach, expect, test, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { publicApi } from '@/api/public'
import { useSiteStore } from './site'

vi.mock('@/api/public', () => ({ publicApi: { site: vi.fn() } }))
beforeEach(() => { setActivePinia(createPinia()); vi.clearAllMocks(); history.replaceState({}, '', '/') })

test('切换语言时等待最新响应，旧响应不能覆盖新内容', async () => {
  let resolveChinese!: (value: any) => void
  let resolveEnglish!: (value: any) => void
  vi.mocked(publicApi.site).mockImplementationOnce(() => new Promise((resolve) => { resolveChinese = resolve }))
    .mockImplementationOnce(() => new Promise((resolve) => { resolveEnglish = resolve }))
  const site = useSiteStore()
  const first = site.load()
  const same = site.load()
  expect(publicApi.site).toHaveBeenCalledTimes(1)
  history.replaceState({}, '', '/en')
  const second = site.load()
  resolveChinese({ settings: { site_name: '中文' }, categories: [], tags: [] })
  resolveEnglish({ settings: { site_name: 'English' }, categories: [], tags: [] })
  await Promise.all([first, same, second])
  expect(site.settings.site_name).toBe('English')
  expect(site.loading).toBe(false)
  expect(publicApi.site).toHaveBeenCalledTimes(2)
})
