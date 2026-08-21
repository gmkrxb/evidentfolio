import { defineStore } from 'pinia'
import { ref } from 'vue'

export type ToastTone = 'success' | 'error' | 'info'

export const useToastStore = defineStore('toast', () => {
  const message = ref('')
  const tone = ref<ToastTone>('info')
  let timeout = 0

  function show(text: string, nextTone: ToastTone = 'info') {
    window.clearTimeout(timeout)
    message.value = text
    tone.value = nextTone
    timeout = window.setTimeout(() => (message.value = ''), 3800)
  }

  return { message, tone, show }
})

