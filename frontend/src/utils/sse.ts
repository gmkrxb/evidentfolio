export interface StreamEvent {
  type: 'started' | 'reasoning' | 'content' | 'result' | 'done' | 'error' | 'fields' | 'plan' | 'task_started' | 'task_done' | 'task_error' | 'context'
  fields?: Array<{ path: string; label: string; text: string; done: boolean }>
  chars?: number
  limit?: number
  references?: number
  completed?: number
  total?: number
  id?: string
  module?: string
  title?: string
  items?: Array<{ id: string; module: string; title: string; total: number }>
  content?: string
  message?: string
  data?: Record<string, unknown>
}

export async function readSse(response: Response, onEvent: (event: StreamEvent) => void) {
  const reader = response.body?.getReader()
  if (!reader) throw new Error('当前浏览器不支持流式响应')
  const decoder = new TextDecoder()
  let buffer = ''
  let completed = false
  function dispatch(block: string) {
    const data = block.split(/\r?\n/).filter((line) => line.startsWith('data:')).map((line) => line.slice(5).trimStart()).join('\n')
    if (!data) return
    const event = JSON.parse(data) as StreamEvent
    if (event.type === 'error') throw new Error(event.message || 'AI 处理失败')
    if (event.type === 'done') completed = true
    onEvent(event)
  }
  try {
    while (true) {
      const { done, value } = await reader.read()
      buffer += decoder.decode(value, { stream: !done })
      const blocks = buffer.split(/\r?\n\r?\n/)
      buffer = blocks.pop() || ''
      blocks.forEach(dispatch)
      if (done) break
    }
    if (buffer.trim()) dispatch(buffer)
    if (!completed) throw new Error('连接提前结束，未应用不完整结果，请重试')
  } finally {
    await reader.cancel().catch(() => undefined)
    reader.releaseLock()
  }
}

// 仅展示 JSON 字符串值，隐藏键名、括号和协议封装。
export function readableStream(value: string): string {
  const parts: string[] = []
  const pattern = /"((?:\\.|[^"\\])*)("|$)/g
  for (const match of value.matchAll(pattern)) {
    const after = value.slice((match.index || 0) + match[0].length)
    if (match[2] && /^\s*:/.test(after)) continue
    if (match[2] && !after.trim()) continue
    let text = match[1]
    try { text = JSON.parse(`"${text}"`) as string } catch { text = text.replace(/\\n/g, '\n').replace(/\\"/g, '"') }
    if (text.trim()) parts.push(text)
  }
  return parts.join('\n\n')
}

export function readableResult(value: unknown): string {
  if (typeof value === 'string') return value
  if (Array.isArray(value)) return value.map(readableResult).filter(Boolean).join('\n\n')
  if (value && typeof value === 'object') return Object.entries(value).filter(([key]) => !['uuid', 'client_key', 'icon_svg', 'icon_asset_uuid', 'url', 'to', 'type', 'kind'].includes(key)).map(([, item]) => readableResult(item)).filter(Boolean).join('\n\n')
  return ''
}
