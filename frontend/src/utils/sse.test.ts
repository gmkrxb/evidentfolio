import { describe, expect, it } from 'vitest'
import { readSse, readableResult, readableStream } from './sse'

// 模拟网络在任意字节边界切分，包括中文与 CRLF。
function response(text: string) {
  const bytes = new TextEncoder().encode(text)
  return { body: new ReadableStream({ start(controller) { for (const byte of bytes) controller.enqueue(new Uint8Array([byte])); controller.close() } }) } as Response
}
describe('AI 流式响应', () => {
  it('保留分片中文，支持 CRLF 和无末尾换行', async () => {
    const events: string[] = []
    await readSse(response('data: {"type":"content","content":"正文"}\r\n\r\ndata: {"type":"done"}'), (event) => events.push(event.content || event.type))
    expect(events).toEqual(['正文', 'done'])
  })
  it('连接截断时拒绝应用结果', async () => {
    await expect(readSse(response('data: {"type":"result","data":{"title":"结果"}}\n\n'), () => {})).rejects.toThrow('连接提前结束')
  })
  it('错误事件显示实际错误', async () => {
    await expect(readSse(response('data: {"type":"error","message":"模型不可用"}\n\n'), () => {})).rejects.toThrow('模型不可用')
  })
  it('正文展示不含原始 JSON 结构', () => {
    expect(readableStream('{"title":"Hello","body":"世界')).toBe('Hello\n\n世界')
    expect(readableResult({ title: 'Hello', sections: [{ client_key: 'secret-id', body: '世界' }] })).toBe('Hello\n\n世界')
  })
})
