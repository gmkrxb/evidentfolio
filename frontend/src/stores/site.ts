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

  async function load(force = false) {
    if (data.value && !force) return data.value
    loading.value = true
    error.value = ''
    try {
      data.value = await publicApi.site()
      return data.value
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : (location.pathname.startsWith('/en') ? 'Failed to load site information' : '网站信息加载失败')
      throw cause
    } finally {
      loading.value = false
    }
  }

  return { data, settings, categories, tags, loading, error, load }
})
