const isEnglish = () => typeof document !== 'undefined' && document.documentElement.lang === 'en'
const lookup = (labels: Record<string, [string, string]>, value: string | null | undefined, fallback?: string) =>
  value ? labels[value]?.[isEnglish() ? 1 : 0] || value : (fallback || (isEnglish() ? 'Unknown' : '未知'))

export const projectStatusLabel = (value: string | null | undefined) => lookup({
  draft: ['草稿', 'Draft'],
  published: ['已发布', 'Published'],
  hidden: ['已隐藏', 'Hidden'],
  archived: ['已归档', 'Archived'],
}, value)

export const projectStateLabel = (value: string | null | undefined) => lookup({
  active: ['进行中', 'Active'],
  completed: ['已完成', 'Completed'],
  research: ['研究中', 'Research'],
  maintained: ['持续维护', 'Maintained'],
}, value)

export const certificateTypeLabel = (value: string | null | undefined) => lookup({
  competition: ['竞赛获奖', 'Competition award'],
  scholarship: ['奖学金', 'Scholarship'],
  patent: ['专利', 'Patent'],
  course: ['资格与语言认证', 'Qualification'],
  other: ['其他荣誉', 'Other honor'],
}, value)

export const resumeTypeLabel = (value: string | null | undefined) => lookup({
  technical: ['技术简历', 'Technical résumé'],
  academic: ['学术简历', 'Academic résumé'],
  general: ['通用简历', 'General résumé'],
}, value)

export const languageLabel = (value: string | null | undefined) => lookup({
  'zh-CN': ['中文', 'Chinese'],
  zh: ['中文', 'Chinese'],
  en: ['英文', 'English'],
  'en-US': ['英文', 'English'],
}, value)

export const uploadStatusLabel = (value: string | null | undefined) => lookup({
  queued: ['等待上传', 'Queued'],
  uploading: ['上传中', 'Uploading'],
  success: ['上传成功', 'Uploaded'],
  error: ['上传失败', 'Failed'],
}, value)

export const deviceTypeLabel = (value: string | null | undefined) => lookup({
  desktop: ['桌面电脑', 'Desktop'],
  mobile: ['手机', 'Mobile'],
  tablet: ['平板电脑', 'Tablet'],
  bot: ['自动化访问', 'Bot'],
  unknown: ['未知设备', 'Unknown device'],
}, value)
