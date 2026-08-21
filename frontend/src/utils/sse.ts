export interface StreamEvent {
  type: 'started' | 'reasoning' | 'content' | 'result' | 'done' | 'error'
  content?: string
  message?: string
  data?: Record<string, unknown>
}

export async function readSse(response: Response, onEvent: (event: StreamEvent) => void) {
  const reader = response.body?.getReader()
  if (!reader) throw new Error('当前浏览器不支持流式响应')
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const blocks = buffer.split('\n\n')
    buffer = blocks.pop() || ''
    for (const block of blocks) {
      const line = block.split('\n').find((item) => item.startsWith('data:'))
      if (!line) continue
      const event = JSON.parse(line.slice(5).trim()) as StreamEvent
      if (event.type === 'error') throw new Error(event.message || 'AI 处理失败')
      onEvent(event)
    }
  }
}
