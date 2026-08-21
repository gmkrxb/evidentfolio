import axios, { AxiosError, type AxiosProgressEvent, type AxiosRequestConfig } from 'axios'
import type { ApiEnvelope } from '@/types'

export class ApiClientError extends Error {
  code: string
  status: number
  fields?: Array<Record<string, unknown>>

  constructor(message: string, code = 'UNKNOWN_ERROR', status = 0, fields?: Array<Record<string, unknown>>) {
    super(message)
    this.name = 'ApiClientError'
    this.code = code
    this.status = status
    this.fields = fields
  }
}

function cookieValue(name: string): string {
  const match = document.cookie
    .split('; ')
    .find((part) => part.startsWith(`${name}=`))
  return match ? decodeURIComponent(match.split('=').slice(1).join('=')) : ''
}

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')

const client = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  timeout: 20_000,
  // FastAPI parses repeated list parameters as `tags=a&tags=b`.
  // Axios' bracket form (`tags[]=a`) is treated as an unrelated parameter.
  paramsSerializer: { indexes: null },
  headers: { Accept: 'application/json' },
})

client.interceptors.request.use((config) => {
  config.headers.set('Accept-Language', localStorage.getItem('portfolio_locale') || navigator.language || 'zh-CN')
  const method = config.method?.toLowerCase()
  if (method && ['post', 'put', 'patch', 'delete'].includes(method)) {
    const csrf = cookieValue('portfolio_csrf')
    if (csrf) config.headers.set('X-CSRF-Token', csrf)
  }
  return config
})

client.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiEnvelope<unknown>>) => {
    const payload = error.response?.data
    throw new ApiClientError(
      payload?.message || error.message || '请求失败',
      payload?.error?.code,
      error.response?.status,
      payload?.error?.fields as Array<Record<string, unknown>> | undefined,
    )
  },
)

async function request<T>(config: AxiosRequestConfig): Promise<T> {
  const retryable = (config.method || 'GET').toUpperCase() === 'GET'
  for (let attempt = 0; ; attempt += 1) {
    try {
      const response = await client.request<ApiEnvelope<T>>(config)
      return response.data.data
    } catch (error) {
      const status = error instanceof ApiClientError ? error.status : 0
      if (!retryable || attempt >= 3 || ![0, 502, 503, 504].includes(status)) throw error
      const delays = [350, 1100, 3000]
      await new Promise((resolve) =>
        window.setTimeout(resolve, delays[attempt] + Math.floor(Math.random() * 250)),
      )
    }
  }
}

export const api = {
  get<T>(url: string, params?: Record<string, unknown>, signal?: AbortSignal) {
    return request<T>({ method: 'GET', url, params, signal })
  },
  post<T>(url: string, data?: unknown, config?: AxiosRequestConfig) {
    return request<T>({ method: 'POST', url, data, ...config })
  },
  put<T>(url: string, data?: unknown, config?: AxiosRequestConfig) {
    return request<T>({ method: 'PUT', url, data, ...config })
  },
  delete<T>(url: string, params?: Record<string, unknown>) {
    return request<T>({ method: 'DELETE', url, params })
  },
  upload<T>(
    url: string,
    formData: FormData,
    onProgress?: (event: AxiosProgressEvent) => void,
  ) {
    return request<T>({
      method: 'POST',
      url,
      data: formData,
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 0,
      onUploadProgress: onProgress,
    })
  },
  async stream(url: string, data: unknown): Promise<Response> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      'Accept-Language': localStorage.getItem('portfolio_locale') || navigator.language || 'zh-CN',
    }
    const csrf = cookieValue('portfolio_csrf')
    if (csrf) headers['X-CSRF-Token'] = csrf
    const response = await fetch(`${API_BASE_URL}${url}`, {
      method: 'POST', credentials: 'include', headers, body: JSON.stringify(data),
    })
    if (!response.ok) {
      const payload = await response.json().catch(() => null) as ApiEnvelope<unknown> | null
      throw new ApiClientError(payload?.message || `HTTP ${response.status}`, payload?.error?.code, response.status)
    }
    return response
  },
}
