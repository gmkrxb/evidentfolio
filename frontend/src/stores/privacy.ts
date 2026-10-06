import { reactive } from 'vue'
import { api } from '@/api/client'

export const privacy = reactive({ ready: false, decided: false, analytics: false, raw_ip: false, open: false })
let loading: Promise<void> | null = null
export function loadPrivacy() {
  if (!loading) loading = api.get<{ decided: boolean; analytics: boolean; raw_ip: boolean }>('/privacy/consent').then((value) => {
    Object.assign(privacy, value, { ready: true, open: !value.decided })
  }).catch(() => { privacy.ready = true; privacy.open = true }).finally(() => { loading = null })
  return loading
}
export async function savePrivacy(analytics: boolean, rawIp: boolean) {
  const value = await api.put<{ decided: boolean; analytics: boolean; raw_ip: boolean }>('/privacy/consent', { analytics, raw_ip: analytics && rawIp })
  Object.assign(privacy, value, { ready: true, open: false })
  window.dispatchEvent(new Event('portfolio-consent-changed'))
  try { localStorage.setItem('portfolio-consent-change', String(Date.now())) } catch { /* 存储禁用不影响选择 */ }
}
window.addEventListener('storage', (event) => {
  if (event.key === 'portfolio-consent-change') {
    privacy.ready = false
    void loadPrivacy().then(() => window.dispatchEvent(new Event('portfolio-consent-changed')))
  }
})
