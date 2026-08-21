import { api } from './client'
import type {
  Asset,
  AssetFolder,
  Certificate,
  Project,
  ProjectPayload,
  ResumeVersion,
  SiteSettings,
  TaxonomyItem,
} from '@/types'

interface Pagination {
  page: number
  page_size: number
  total: number
}

interface AdminUser {
  uuid: string
  username: string
  display_name: string
  role: string
}

export interface AssetDependencies {
  asset: { uuid: string; display_name: string }
  projects: Array<{ uuid: string; title: string; usage_count: number }>
  certificates: Array<{ uuid: string; name: string }>
  resumes: Array<{ uuid: string; name: string }>
  site_uses: string[]
  has_dependencies: boolean
}

export interface AssetFolderDependencies extends Omit<AssetDependencies, 'asset'> {
  folder: { uuid: string; name: string }
  asset_count: number
  folder_count: number
}

export const authApi = {
  setupStatus: () => api.get<{ required: boolean }>('/setup/status'),
  initialize: (payload: Record<string, string>) =>
    api.post<{ user: AdminUser }>('/setup/initialize', payload),
  login: (username: string, password: string) =>
    api.post<{ user: AdminUser }>('/admin/auth/login', { username, password }),
  me: () => api.get<{ user: AdminUser }>('/admin/auth/me'),
  logout: () => api.post<void>('/admin/auth/logout'),
}

export const adminApi = {
  dashboard: () => api.get<Record<string, unknown>>('/admin/dashboard'),
  projects: (params: Record<string, unknown> = {}) =>
    api.get<{ items: Project[]; pagination: Pagination }>('/admin/projects', params),
  project: (uuid: string) => api.get<Project>(`/admin/projects/${uuid}`),
  createProject: (payload: ProjectPayload) => api.post<Project>('/admin/projects', payload),
  updateProject: (uuid: string, payload: ProjectPayload) =>
    api.put<Project>(`/admin/projects/${uuid}`, payload),
  duplicateProject: (uuid: string) => api.post<Project>(`/admin/projects/${uuid}/duplicate`),
  deleteProject: (uuid: string) => api.delete<void>(`/admin/projects/${uuid}`),
  batchProjects: (uuids: string[], action: string) =>
    api.post<{ affected: number }>('/admin/projects/batch', { uuids, action }),

  categories: () => api.get<{ items: TaxonomyItem[] }>('/admin/categories'),
  createCategory: (payload: Record<string, unknown>) => api.post('/admin/categories', payload),
  updateCategory: (uuid: string, payload: Record<string, unknown>) =>
    api.put(`/admin/categories/${uuid}`, payload),
  deleteCategory: (uuid: string) => api.delete(`/admin/categories/${uuid}`),
  tags: () => api.get<{ items: TaxonomyItem[] }>('/admin/tags'),
  createTag: (payload: Record<string, unknown>) => api.post('/admin/tags', payload),
  updateTag: (uuid: string, payload: Record<string, unknown>) =>
    api.put(`/admin/tags/${uuid}`, payload),
  deleteTag: (uuid: string) => api.delete(`/admin/tags/${uuid}`),
  mergeTags: (sourceUuids: string[], targetUuid: string) =>
    api.post('/admin/tags/merge', { source_uuids: sourceUuids, target_uuid: targetUuid }),

  assets: (params: Record<string, unknown> = {}) =>
    api.get<{ items: Asset[]; pagination: Pagination }>('/admin/assets', params),
  assetFolders: () => api.get<{ items: AssetFolder[] }>('/admin/asset-folders'),
  createAssetFolder: (payload: Record<string, unknown>) =>
    api.post<AssetFolder>('/admin/asset-folders', payload),
  updateAssetFolder: (uuid: string, payload: Record<string, unknown>) =>
    api.put<AssetFolder>(`/admin/asset-folders/${uuid}`, payload),
  assetFolderDependencies: (uuid: string) =>
    api.get<AssetFolderDependencies>(`/admin/asset-folders/${uuid}/dependencies`),
  deleteAssetFolder: (uuid: string, deleteContents = false) =>
    api.delete(`/admin/asset-folders/${uuid}`, { delete_contents: deleteContents }),
  batchMoveAssets: (assetUuids: string[], folderUuid: string | null) =>
    api.post<{ moved: number }>('/admin/assets/batch-move', {
      asset_uuids: assetUuids,
      folder_uuid: folderUuid,
    }),
  updateAsset: (uuid: string, payload: Record<string, unknown>) =>
    api.put<Asset>(`/admin/assets/${uuid}`, payload),
  assetDependencies: (uuid: string) =>
    api.get<AssetDependencies>(`/admin/assets/${uuid}/dependencies`),
  deleteAsset: (uuid: string) => api.delete(`/admin/assets/${uuid}`),
  associateAsset: (assetUuid: string, projectUuid: string, payload: Record<string, unknown>) =>
    api.post(`/admin/assets/${assetUuid}/projects/${projectUuid}`, payload),
  uploadAsset: (file: File, isPublic = true, logicalGroup = '', folderUuid = '') => {
    const form = new FormData()
    form.append('file', file)
    form.append('is_public', String(isPublic))
    form.append('logical_group', logicalGroup)
    form.append('folder_uuid', folderUuid)
    return api.upload<Asset>('/admin/assets/upload', form)
  },

  resumes: () => api.get<{ items: ResumeVersion[] }>('/admin/resumes'),
  createResume: (payload: Record<string, unknown>) => api.post<ResumeVersion>('/admin/resumes', payload),
  updateResume: (uuid: string, payload: Record<string, unknown>) =>
    api.put<ResumeVersion>(`/admin/resumes/${uuid}`, payload),
  deleteResume: (uuid: string) => api.delete(`/admin/resumes/${uuid}`),

  certificates: () => api.get<{ items: Certificate[] }>('/admin/certificates'),
  createCertificate: (payload: Record<string, unknown>) =>
    api.post<Certificate>('/admin/certificates', payload),
  updateCertificate: (uuid: string, payload: Record<string, unknown>) =>
    api.put<Certificate>(`/admin/certificates/${uuid}`, payload),
  deleteCertificate: (uuid: string) => api.delete(`/admin/certificates/${uuid}`),

  settings: () => api.get<SiteSettings>('/admin/settings'),
  updateSettings: (payload: SiteSettings) => api.put<SiteSettings>('/admin/settings', payload),
  analyticsOverview: () => api.get<Record<string, unknown>>('/admin/analytics/overview'),
  visitors: () => api.get<{ items: Array<Record<string, unknown>> }>('/admin/analytics/visitors'),
  session: (uuid: string) => api.get<Record<string, unknown>>(`/admin/analytics/sessions/${uuid}`),
  cleanupAnalytics: (days: number) => api.delete<Record<string, number>>('/admin/analytics', { days }),
  auditLogs: () => api.get<{ items: Array<Record<string, unknown>> }>('/admin/audit-logs'),
  aiConfig: () => api.get<{ base_url: string; model: string; enabled: boolean; has_api_key: boolean }>('/admin/ai/config'),
  updateAiConfig: (payload: Record<string, unknown>) => api.put('/admin/ai/config', payload),
  aiModels: (payload: Record<string, unknown>) => api.post<{ items: Array<{ id: string; owned_by: string }> }>('/admin/ai/models', payload),
  aiStream: (path: 'translate' | 'resume/parse', payload: Record<string, unknown>) => api.stream(`/admin/ai/${path}/stream`, payload),
  applyAiResume: (result: Record<string, unknown>) => api.post<{ projects_created: number; certificates_created: number }>('/admin/ai/resume/apply', { result }),
}
