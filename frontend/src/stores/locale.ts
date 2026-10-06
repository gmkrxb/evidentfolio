import { readPreference, writePreference } from '@/utils/storage'
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { messages, type MessageKey } from '@/i18n'

export type AppLocale = 'zh-CN' | 'en'

export const useLocaleStore = defineStore('locale', () => {
  const preference = readPreference('portfolio_locale')
  const saved = preference === 'en' || preference === 'zh-CN' ? preference : null
  const language = ref<AppLocale>(saved || (navigator.language.toLowerCase().startsWith('zh') ? 'zh-CN' : 'en'))
  const isEnglish = computed(() => language.value === 'en')
  const switching = ref(false)

  function setLanguage(next: AppLocale) {
    language.value = next
    writePreference('portfolio_locale', next)
    document.documentElement.lang = next
  }
  function t(key: MessageKey) {
    return messages[language.value][key]
  }
  function publicPath(path: string) {
    const normalized = path.startsWith('/') ? path : `/${path}`
    return isEnglish.value ? `/en${normalized === '/' ? '' : normalized}` : normalized
  }
  function syncPath(path: string) {
    setLanguage(path === '/en' || path.startsWith('/en/') ? 'en' : 'zh-CN')
  }

  document.documentElement.lang = language.value
  return { language, isEnglish, switching, setLanguage, syncPath, publicPath, t }
})
