import { watch } from 'vue'
import { useRoute } from 'vue-router'

// 同一页面切换语言时复用组件和媒体，仅刷新文案数据。
export function useLocaleReload(load: () => unknown) {
  const route = useRoute()
  watch(() => route.path === '/en' || route.path.startsWith('/en/'), load)
}
