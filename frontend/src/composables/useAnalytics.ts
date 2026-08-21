import { onBeforeUnmount, onMounted } from 'vue'

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
  if (!queue.length) return
  const events = queue.splice(0, 50)
  const body = JSON.stringify({ events })
  if (useBeacon && navigator.sendBeacon) {
    navigator.sendBeacon('/api/v1/analytics/events', new Blob([body], { type: 'application/json' }))
    return
  }
  fetch('/api/v1/analytics/events', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body,
    keepalive: true,
  })
    .then((response) => {
      if (!response.ok) throw new Error(`analytics returned ${response.status}`)
    })
    .catch(() => {
      queue.unshift(...events)
      window.clearTimeout(flushTimer)
      flushTimer = window.setTimeout(() => flush(), 4000 + Math.floor(Math.random() * 1000))
    })
}

export function track(event: AnalyticsEvent, immediate = false) {
  queue.push({ ...context(), ...event })
  if (immediate || queue.length >= 10) flush()
  else {
    window.clearTimeout(flushTimer)
    flushTimer = window.setTimeout(() => flush(), 1800)
  }
}

export function usePageAnalytics(pageType: string, pageUuid?: string) {
  const started = performance.now()
  onMounted(() => track({ event_type: 'page_view', page_type: pageType, page_uuid: pageUuid }))
  const end = () =>
    track(
      {
        event_type: 'page_exit',
        page_type: pageType,
        page_uuid: pageUuid,
        event_data: { seconds: Math.round((performance.now() - started) / 1000) },
      },
      true,
    )
  onBeforeUnmount(end)
}

document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'hidden') flush(true)
})
