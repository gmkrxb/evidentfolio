import { computed, onBeforeUnmount, reactive } from 'vue'
import { adminApi } from '@/api/admin'
import { readSse, readableResult, readableStream, type StreamEvent } from '@/utils/sse'

export function useAiTask() {
  const state = reactive({ running: false, reasoning: '', content: '', error: '', result: null as Record<string, unknown> | null, visible: false, fields: [] as NonNullable<StreamEvent['fields']>, completed: 0, total: 0, context: null as { chars: number; limit: number; references: number } | null })
  let controller: AbortController | null = null
  const body = computed(() => state.result ? readableResult(state.result) : readableStream(state.content))
  function cancel() { controller?.abort() }
  function guard(read: () => unknown) {
    const snapshot = JSON.stringify(read())
    return () => snapshot === JSON.stringify(read())
  }
  async function run(path: 'translate' | 'resume/parse', payload: Record<string, unknown>, unchanged?: () => boolean) {
    if (state.running) throw new Error('请等待当前任务结束')
    controller = new AbortController()
    Object.assign(state, { running: true, reasoning: '', content: '', error: '', result: null, visible: true, fields: [], completed: 0, total: 0, context: null })
    let result: Record<string, unknown> | null = null
    try {
      await readSse(await adminApi.aiStream(path, payload, controller.signal), (event) => {
        if (event.type === 'context') state.context = { chars: event.chars || 0, limit: event.limit || 0, references: event.references || 0 }
        if (event.type === 'fields') { state.fields = event.fields || []; state.completed = event.completed || 0; state.total = event.total || 0 }
        if (event.type === 'reasoning') state.reasoning += event.content || ''
        if (event.type === 'content') state.content += event.content || ''
        if (event.type === 'result') result = event.data || null
      })
      if (!result) throw new Error('AI 未返回正文结果，请重试')
      if (controller.signal.aborted) throw new Error('已停止')
      if (unchanged && !unchanged()) throw new Error('翻译期间表单已修改，译文未覆盖你的编辑，请重试')
      state.result = result
      state.completed = state.total
      return result as Record<string, any>
    } catch (cause) {
      state.error = controller.signal.aborted ? '已停止，现有内容未修改' : cause instanceof Error ? cause.message : 'AI 处理失败'
      throw new Error(state.error)
    } finally { state.running = false; controller = null }
  }
  onBeforeUnmount(cancel)
  return { state, body, run, cancel, guard }
}
