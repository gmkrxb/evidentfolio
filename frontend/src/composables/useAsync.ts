import { onBeforeUnmount, ref } from 'vue'
import { trackPageLoad } from '@/utils/pageNavigation'

export function useAsyncState<T>(options: { keepPreviousData?: boolean } = {}) {
  const data = ref<T | null>(null)
  const loading = ref(false)
  const error = ref('')
  let controller: AbortController | null = null
  let disposed = false

  async function run(loader: (signal: AbortSignal) => Promise<T>) {
    if (disposed) return null
    controller?.abort()
    const current = new AbortController()
    controller = current
    loading.value = !options.keepPreviousData || data.value === null
    error.value = ''
    return trackPageLoad((async () => { try {
      const result = await loader(current.signal)
      if (controller !== current || current.signal.aborted) return null
      data.value = result
      return data.value
    } catch (cause) {
      if (controller !== current || current.signal.aborted) return null
      if (cause instanceof DOMException && cause.name === 'AbortError') return null
      error.value = cause instanceof Error ? cause.message : '加载失败'
      return null
    } finally {
      if (controller === current) loading.value = false
    } })())
  }

  onBeforeUnmount(() => { disposed = true; controller?.abort() })
  return { data, loading, error, run }
}
