import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { publicApi } from '@/api/public'
import type { SiteData } from '@/types'

export const useSiteStore = defineStore('site', () => {
  const data = ref<SiteData | null>(null)
  const loading = ref(false)
  const error = ref('')

  const settings = computed(() => data.value?.settings || {})
  const categories = computed(() => data.value?.categories || [])
  const tags = computed(() => data.value?.tags || [])

  let loadedLocale = ''
  let generation = 0
  let pending: { locale: string; promise: Promise<SiteData | null> } | null = null
  function load(force = false): Promise<SiteData | null> {
    const locale = location.pathname.startsWith('/en') ? 'en' : 'zh-CN'
    if (!force && pending?.locale === locale) return pending.promise
    if (data.value && !force && loadedLocale === locale) return Promise.resolve(data.value)
    const current = ++generation
    loading.value = true
    error.value = ''
    const promise = (async (): Promise<SiteData | null> => { try {
      const result = await publicApi.site()
      if (current !== generation) return pending?.promise || data.value
      data.value = result
      loadedLocale = locale
      return data.value
    } catch (cause) {
      if (current !== generation) return pending?.promise || data.value
      error.value = cause instanceof Error ? cause.message : (location.pathname.startsWith('/en') ? 'Failed to load site information' : '网站信息加载失败')
      throw cause
    } finally {
      if (current === generation) { loading.value = false; pending = null }
    } })()
    pending = { locale, promise }
    return promise
  }

  return { data, settings, categories, tags, loading, error, load }
})
