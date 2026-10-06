import { onBeforeUnmount, onMounted, watch } from 'vue'

import { privacy } from '@/stores/privacy'
import { API_BASE_URL } from '@/api/client'

interface AnalyticsEvent {
  event_type: string
  page_type?: string
  page_uuid?: string
  project_uuid?: string
  asset_uuid?: string
  event_data?: Record<string, unknown>
  referer?: string
  utm_source?: string
  utm_medium?: string
  utm_campaign?: string
  language?: string
  timezone?: string
  screen_size?: string
}

const queue: AnalyticsEvent[] = []
let flushTimer = 0
const requests = new Set<AbortController>()
let consentGeneration = 0
window.addEventListener('portfolio-consent-changed', () => {
  consentGeneration += 1
  queue.length = 0
  window.clearTimeout(flushTimer)
  requests.forEach((controller) => controller.abort())
  requests.clear()
})

function context(): Partial<AnalyticsEvent> {
  const query = new URLSearchParams(location.search)
  return {
    referer: document.referrer,
    utm_source: query.get('utm_source') || '',
    utm_medium: query.get('utm_medium') || '',
    utm_campaign: query.get('utm_campaign') || '',
    language: navigator.language,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    screen_size: `${window.screen.width}x${window.screen.height}`,
  }
}

function flush(useBeacon = false) {
  window.clearTimeout(flushTimer)
  if (!privacy.ready || !privacy.analytics) { queue.length = 0; return }
  if (!queue.length) return
  const generation = consentGeneration
  const controller = new AbortController()
  requests.add(controller)
  const events = queue.splice(0, 50)
  const body = JSON.stringify({ events })
  if (useBeacon && navigator.sendBeacon) {
    const sent = navigator.sendBeacon(`${API_BASE_URL}/analytics/events`, new Blob([body], { type: 'application/json' }))
    if (sent) { requests.delete(controller); return }
  }
  fetch(`${API_BASE_URL}/analytics/events`, {
    method: 'POST',
    signal: controller.signal,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body,
    keepalive: true,
  })
    .then((response) => {
      if (!response.ok) throw new Error(`analytics returned ${response.status}`)
    })
    .catch(() => {
      if (controller.signal.aborted || generation !== consentGeneration || !privacy.analytics) return
      queue.unshift(...events)
      queue.splice(100)
      window.clearTimeout(flushTimer)
      flushTimer = window.setTimeout(() => flush(), 4000 + Math.floor(Math.random() * 1000))
    }).finally(() => requests.delete(controller))
}

export function track(event: AnalyticsEvent, immediate = false) {
  if (!privacy.ready || !privacy.analytics) return
  queue.push({ ...context(), ...event })
  if (immediate || queue.length >= 10) flush()
  else {
    window.clearTimeout(flushTimer)
    flushTimer = window.setTimeout(() => flush(), 1800)
  }
}

export function usePageAnalytics(pageType: string, pageUuid?: string) {
  let started = performance.now()
  let recorded = false
  function begin() {
    if (!privacy.ready || !privacy.analytics || recorded) return
    recorded = true; started = performance.now()
    track({ event_type: 'page_view', page_type: pageType, page_uuid: pageUuid })
  }
  onMounted(begin)
  watch(() => privacy.ready && privacy.analytics, (allowed) => { if (allowed) begin(); else recorded = false })
  const end = () => {
    if (!recorded) return
    track(
      {
        event_type: 'page_exit',
        page_type: pageType,
        page_uuid: pageUuid,
        event_data: { seconds: Math.round((performance.now() - started) / 1000) },
      },
      true,
    )
  }
  onBeforeUnmount(end)
}

document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'hidden') flush(true)
})
