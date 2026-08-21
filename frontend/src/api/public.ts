import { api } from './client'
import type { Asset, Certificate, Project, ResumeVersion, SiteData } from '@/types'

export interface Paginated<T> {
  items: T[]
  pagination: { page: number; page_size: number; total: number; pages?: number }
}

export const publicApi = {
  site: (signal?: AbortSignal) => api.get<SiteData>('/public/site', { locale: currentLocale() }, signal),
  projects: (params: Record<string, unknown>, signal?: AbortSignal) =>
    api.get<Paginated<Project>>('/public/projects', { ...params, locale: currentLocale() }, signal),
  project: (uuid: string, signal?: AbortSignal) =>
    api.get<Project>(`/public/projects/${uuid}`, { locale: currentLocale() }, signal),
  resumes: (signal?: AbortSignal) =>
    api.get<{ items: ResumeVersion[] }>('/public/resumes', undefined, signal),
  resume: (uuid: string, signal?: AbortSignal) =>
    api.get<ResumeVersion>(`/public/resumes/${uuid}`, undefined, signal),
  certificates: (signal?: AbortSignal) =>
    api.get<{ items: Certificate[] }>('/public/certificates', { locale: currentLocale() }, signal),
  certificate: (uuid: string, signal?: AbortSignal) =>
    api.get<Certificate>(`/public/certificates/${uuid}`, { locale: currentLocale() }, signal),
  asset: (uuid: string, signal?: AbortSignal) =>
    api.get<Asset>(`/public/assets/${uuid}`, undefined, signal),
  assetPreview: (uuid: string, signal?: AbortSignal) =>
    api.get<{
      kind: 'office' | 'archive'
      sections?: Array<{ title: string; lines: string[] }>
      entries?: Array<{ name: string; size: number; compressed_size: number; is_directory: boolean }>
      entry_count?: number
      truncated?: boolean
    }>(`/public/assets/${uuid}/preview`, undefined, signal),
}

function currentLocale() {
  return location.pathname === '/en' || location.pathname.startsWith('/en/') ? 'en' : 'zh-CN'
}
