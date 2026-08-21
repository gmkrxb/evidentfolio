import { onBeforeUnmount, ref } from 'vue'

export function useAsyncState<T>() {
  const data = ref<T | null>(null)
  const loading = ref(false)
  const error = ref('')
  let controller: AbortController | null = null

  async function run(loader: (signal: AbortSignal) => Promise<T>) {
    controller?.abort()
    controller = new AbortController()
    loading.value = true
    error.value = ''
    try {
      data.value = await loader(controller.signal)
      return data.value
    } catch (cause) {
      if (cause instanceof DOMException && cause.name === 'AbortError') return null
      error.value = cause instanceof Error ? cause.message : '加载失败'
      return null
    } finally {
      loading.value = false
    }
  }

  onBeforeUnmount(() => controller?.abort())
  return { data, loading, error, run }
}

