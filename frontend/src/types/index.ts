export interface ApiEnvelope<T> {
  success: boolean
  data: T
  message: string | null
  request_id: string
  error?: {
    code: string
    message: string
    fields?: Array<{ field?: string; message?: string }>
  }
}

export interface Asset {
  uuid: string
  original_name: string
  display_name: string
  mime_type: string
  extension: string
  size: number
  sha256: string
  category: string
  width: number | null
  height: number | null
  duration: number | null
  is_public: boolean
  description: string
  logical_group: string
  folder: { uuid: string; name: string } | null
  view_count: number
  download_count: number
  created_at: string
  updated_at: string
  content_url: string
  download_url: string
  thumbnail_url: string | null
  translations?: Record<string, Record<string, unknown>>
}

export interface AssetFolder {
  uuid: string
  name: string
  description: string
  sort_order: number
  asset_count: number
  child_count: number
  parent_uuid: string | null
  path: Array<{ uuid: string; name: string }>
  created_at?: string
  updated_at?: string
}

export interface TaxonomyItem {
  uuid: string
  name: string
  slug: string
  color?: string
  description?: string
  sort_order?: number
  project_count?: number
  translations?: Record<string, Record<string, unknown>>
}

export interface ProjectLink {
  uuid?: string
  label: string
  url: string
  link_type: string
  sort_order: number
}

export interface ProjectSection {
  uuid?: string
  client_key: string
  title: string
  body: string
  section_type: string
  display_mode:
    | 'text'
    | 'single'
    | 'gallery'
    | 'carousel'
    | 'album'
    | 'video'
    | 'audio'
    | 'attachments'
    | 'mixed'
  asset_uuids: string[]
  album_uuid: string | null
  heading_level: 2 | 3 | 4
  is_visible: boolean
  media_assets?: Asset[]
  album?: ProjectAlbum | null
  sort_order: number
  translations?: Record<string, Record<string, unknown>>
}

export interface ProjectContentLayoutItem {
  key: string
  kind: 'builtin' | 'custom'
  visible: boolean
  sort_order: number
}

export interface ProjectAlbumAsset {
  uuid: string
  caption: string
  sort_order: number
  asset: Asset
}

export interface ProjectAlbum {
  uuid?: string
  title: string
  description: string
  display_mode: 'grid' | 'carousel'
  asset_uuids?: string[]
  assets?: ProjectAlbumAsset[]
  sort_order: number
  translations?: Record<string, Record<string, unknown>>
}

export interface ProjectAsset {
  uuid: string
  usage: string
  caption: string
  sort_order: number
  asset: Asset
}

export interface Project {
  uuid: string
  title: string
  subtitle: string
  summary: string
  content: string
  background: string
  problem: string
  solution: string
  architecture: string
  contributions: string[]
  technologies: string[]
  outcomes: string[]
  start_date: string
  end_date: string
  role: string
  team_size: number | null
  status: 'draft' | 'published' | 'hidden' | 'archived'
  project_state: string
  is_featured: boolean
  is_open_source: boolean
  sort_order: number
  content_layout: ProjectContentLayoutItem[]
  category: TaxonomyItem | null
  tags: TaxonomyItem[]
  certificates: Certificate[]
  cover_asset: Asset | null
  auto_cover_assets: Asset[]
  links: ProjectLink[]
  sections: ProjectSection[]
  albums: ProjectAlbum[]
  assets: ProjectAsset[]
  seo_title: string
  seo_description: string
  published_at: string | null
  created_at: string
  updated_at: string
  translations: Record<string, Record<string, unknown>>
  content_language_mode: 'bilingual' | 'single_zh' | 'single_en'
}

export interface ProjectPayload {
  title: string
  subtitle: string
  summary: string
  content: string
  background: string
  problem: string
  solution: string
  architecture: string
  contributions: string[]
  technologies: string[]
  outcomes: string[]
  start_date: string
  end_date: string
  role: string
  team_size: number | null
  status: Project['status']
  project_state: string
  is_featured: boolean
  is_open_source: boolean
  sort_order: number
  category_uuid: string | null
  tag_uuids: string[]
  certificate_uuids: string[]
  cover_asset_uuid: string | null
  seo_title: string
  seo_description: string
  links: ProjectLink[]
  sections: ProjectSection[]
  albums: ProjectAlbum[]
  content_layout: ProjectContentLayoutItem[]
  translations: Record<string, Record<string, unknown>>
  content_language_mode: 'bilingual' | 'single_zh' | 'single_en'
}

export interface ResumeVersion {
  uuid: string
  name: string
  language: string
  resume_type: string
  is_default: boolean
  is_public: boolean
  version: string
  view_count: number
  download_count: number
  created_at: string
  updated_at: string
  asset: Asset
}

export interface Certificate {
  uuid: string
  name: string
  issuer: string
  certificate_type: 'scholarship' | 'competition' | 'patent' | 'course' | 'other'
  issued_at: string
  description: string
  credential_no: string
  credential_url: string
  is_public: boolean
  sort_order: number
  project_count: number
  projects?: Array<{
    uuid: string
    title: string
    subtitle: string
    summary: string
    start_date: string
    end_date: string
    role: string
    status: Project['status']
  }>
  asset: Asset | null
  icon_asset: Asset | null
  icon_name: string
  icon_svg: string
  created_at: string
  updated_at: string
  translations?: Record<string, Record<string, unknown>>
  content_language_mode?: 'bilingual' | 'single_zh' | 'single_en'
}

export interface SiteSettings {
  site_name?: string
  person_name?: string
  headline?: string
  bio?: string
  current_identity?: string
  research_directions?: string[]
  email?: string
  github_url?: string
  gitee_url?: string
  location?: string
  avatar_asset_uuid?: string
  footer_text?: string
  footer_eyebrow?: string
  footer_heading?: string
  hero_eyebrow?: string
  hero_focus_label?: string
  hero_focus_value?: string
  brand_mark_text?: string
  brand_icon_asset_uuid?: string
  navigation_items?: Array<{ label: string; to: string; kind: 'route' | 'external' }>
  home_stats?: Array<{ value: string; label: string }>
  home_copy?: Record<string, string>
  home_capabilities?: Array<{ title: string; description: string }>
  contact_methods?: Array<{
    type: string
    label: string
    value: string
    url: string
    description: string
    icon_asset_uuid: string
    icon_name: string
    icon_svg: string
  }>
  page_content?: Record<string, { eyebrow: string; title: string; description: string }>
  analytics_enabled?: boolean
  analytics_retention_days?: number
  analytics_notice_enabled?: boolean
  featured_project_count?: number
  default_seo_title?: string
  default_seo_description?: string
  primary_language?: 'zh-CN' | 'en'
  translations?: Record<string, SiteSettings>
  [key: string]: unknown
}

export interface SiteData {
  settings: SiteSettings
  categories: TaxonomyItem[]
  tags: TaxonomyItem[]
  base_url: string
}
