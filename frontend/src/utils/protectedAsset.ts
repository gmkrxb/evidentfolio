/**
 * 受保护资源的取用：
 * - 仅可查看（asset.protected）：申请一次性查看票据 → 获取 AES-CTR 密文 → 在内存中用 WebCrypto 解密 → Blob URL；
 * - 下载：申请带签名、短时有效的下载票据后再跳转，原始下载地址不再直接暴露给访客。
 */
import { api, API_BASE_URL } from '@/api/client'
import type { Asset } from '@/types'

type AssetLike = Pick<Asset, 'uuid' | 'sha256' | 'mime_type' | 'content_url'> & { protected?: boolean; version?: number }

interface ViewTicket {
  url: string
  expires_at: number
  encrypted: boolean
  key?: string
  counter?: string
  mime_type: string
}

const resolveUrl = (url: string) => API_BASE_URL + url.replace(/^\/api\/v1/, '')
const bytes = (base64: string) => Uint8Array.from(atob(base64), (char) => char.charCodeAt(0))
const cache = new Map<string, Promise<Blob>>()
const urls = new Map<string, string>()

export const isProtected = (asset: { protected?: boolean } | null | undefined) => Boolean(asset?.protected)

async function fetchBlob(asset: AssetLike): Promise<Blob> {
  const canDecrypt = typeof crypto !== 'undefined' && Boolean(crypto.subtle)
  const ticket = await api.post<ViewTicket>(`/public/assets/${asset.uuid}/ticket`, { purpose: 'view', encrypted: canDecrypt })
  const response = await fetch(resolveUrl(ticket.url), { credentials: 'include', cache: 'no-store' })
  if (!response.ok) throw new Error(response.status === 429 ? '请求过于频繁，请稍后再试' : '资源加载失败')
  const payload = await response.arrayBuffer()
  if (!ticket.encrypted || !ticket.key || !ticket.counter) return new Blob([payload], { type: ticket.mime_type || asset.mime_type })
  const key = await crypto.subtle.importKey('raw', bytes(ticket.key), 'AES-CTR', false, ['decrypt'])
  const plain = await crypto.subtle.decrypt({ name: 'AES-CTR', counter: bytes(ticket.counter), length: 64 }, key, payload)
  return new Blob([plain], { type: ticket.mime_type || asset.mime_type })
}

/** 解密后的内容（同一页面会话内共享，避免重复申请票据）。signal 只中止等待，不中止共享的下载。 */
export function protectedBlob(asset: AssetLike, signal?: AbortSignal): Promise<Blob> {
  const id = `${asset.uuid}:${asset.sha256 || asset.version || ''}`
  let pending = cache.get(id)
  if (!pending) {
    pending = fetchBlob(asset)
    cache.set(id, pending)
    pending.catch(() => cache.delete(id))
    if (cache.size > 40) {
      const [oldest] = cache.keys()
      if (oldest) { cache.delete(oldest); const url = urls.get(oldest); if (url) URL.revokeObjectURL(url); urls.delete(oldest) }
    }
  }
  if (!signal) return pending
  return new Promise<Blob>((resolve, reject) => {
    if (signal.aborted) return reject(new DOMException('Aborted', 'AbortError'))
    signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true })
    pending!.then(resolve, reject)
  })
}

export async function protectedObjectUrl(asset: AssetLike, signal?: AbortSignal) {
  const id = `${asset.uuid}:${asset.sha256 || asset.version || ''}`
  const blob = await protectedBlob(asset, signal)
  let url = urls.get(id)
  if (!url) { url = URL.createObjectURL(blob); urls.set(id, url) }
  return url
}

export async function protectedText(asset: AssetLike, signal?: AbortSignal) {
  return (await protectedBlob(asset, signal)).text()
}

export async function protectedBytes(asset: AssetLike, signal?: AbortSignal) {
  return new Uint8Array(await (await protectedBlob(asset, signal)).arrayBuffer())
}

/** 可直接用于 src 的地址：受保护资源返回解密后的 Blob URL，其余返回原地址。 */
export async function assetSource(asset: AssetLike, signal?: AbortSignal) {
  return asset.protected ? protectedObjectUrl(asset, signal) : asset.content_url
}

/** 通过签名票据下载；仅可查看的资源会被服务端拒绝。 */
export async function downloadAsset(asset: Pick<Asset, 'uuid'>) {
  const ticket = await api.post<{ url: string }>(`/public/assets/${asset.uuid}/ticket`, { purpose: 'download' })
  const link = document.createElement('a')
  link.href = resolveUrl(ticket.url)
  link.rel = 'noopener'
  document.body.appendChild(link)
  link.click()
  link.remove()
}
