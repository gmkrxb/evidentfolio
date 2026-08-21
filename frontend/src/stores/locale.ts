import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { messages, type MessageKey } from '@/i18n'

export type AppLocale = 'zh-CN' | 'en'

export const useLocaleStore = defineStore('locale', () => {
  const saved = localStorage.getItem('portfolio_locale') as AppLocale | null
  const language = ref<AppLocale>(saved || (navigator.language.toLowerCase().startsWith('zh') ? 'zh-CN' : 'en'))
  const isEnglish = computed(() => language.value === 'en')

  function setLanguage(next: AppLocale) {
    language.value = next
    localStorage.setItem('portfolio_locale', next)
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
  return { language, isEnglish, setLanguage, syncPath, publicPath, t }
})
