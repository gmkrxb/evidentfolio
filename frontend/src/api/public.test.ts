import { beforeEach, expect, test, vi } from 'vitest'
import { api } from './client'
import { prepareLocalePage, publicApi } from './public'

vi.mock('./client', () => ({ api: { get: vi.fn() } }))
beforeEach(() => { vi.clearAllMocks(); history.replaceState({}, '', '/') })

test('目标语言先预载，动画内消费一次，后续访问仍读取新数据', async () => {
  const site = { settings: { featured_project_count: 3 }, categories: [], tags: [] }
  const projects = { items: [{ uuid: 'same', title: 'English' }], pagination: {} }
  vi.mocked(api.get).mockResolvedValueOnce(site).mockResolvedValueOnce(projects).mockResolvedValueOnce({ items: [] })
  await prepareLocalePage('/', {}, 'en')
  expect(api.get).toHaveBeenCalledTimes(2)
  history.replaceState({}, '', '/en')
  expect(await publicApi.site()).toEqual(site)
  expect(await publicApi.projects({ page_size: 3, featured: true })).toEqual(projects)
  expect(api.get).toHaveBeenCalledTimes(2)
  await publicApi.projects({ featured: true, page_size: 3 })
  expect(api.get).toHaveBeenCalledTimes(3)
})

test('项目列表切换保留过滤条件，预载不改变当前语言', async () => {
  vi.mocked(api.get).mockResolvedValue({ settings: {} })
  await prepareLocalePage('/projects', { q: 'RAG', tags: ['one', 'two'] }, 'en')
  expect(location.pathname).toBe('/')
  expect(api.get).toHaveBeenLastCalledWith('/public/projects', { q: 'RAG', category: undefined, tags: ['one', 'two'], sort: 'featured', page_size: 50, locale: 'en' })
})
