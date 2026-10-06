const fallback = new Map<string, string>()

export function readPreference(key: string): string | null {
  try { return localStorage.getItem(key) ?? fallback.get(key) ?? null }
  catch { return fallback.get(key) ?? null }
}

export function writePreference(key: string, value: string) {
  fallback.set(key, value)
  try { localStorage.setItem(key, value) } catch { /* 禁用存储时保留当前会话偏好。 */ }
}
