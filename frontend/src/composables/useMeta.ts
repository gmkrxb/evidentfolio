import { onBeforeUnmount, watchEffect, type MaybeRefOrGetter, toValue } from 'vue'

function ensureMeta(selector: string, attributes: Record<string, string>) {
  let element = document.head.querySelector<HTMLMetaElement>(selector)
  if (!element) {
    element = document.createElement('meta')
    Object.entries(attributes).forEach(([key, value]) => element!.setAttribute(key, value))
    document.head.appendChild(element)
  }
  return element
}

export function useMeta(options: {
  title: MaybeRefOrGetter<string>
  description: MaybeRefOrGetter<string>
  image?: MaybeRefOrGetter<string | undefined>
}) {
  const canonical = document.createElement('link')
  canonical.rel = 'canonical'
  document.head.appendChild(canonical)
  const description = ensureMeta('meta[name="description"]', { name: 'description' })
  const ogTitle = ensureMeta('meta[property="og:title"]', { property: 'og:title' })
  const ogDescription = ensureMeta('meta[property="og:description"]', { property: 'og:description' })
  const ogUrl = ensureMeta('meta[property="og:url"]', { property: 'og:url' })
  const ogType = ensureMeta('meta[property="og:type"]', { property: 'og:type' })
  const twitterCard = ensureMeta('meta[name="twitter:card"]', { name: 'twitter:card' })
  watchEffect(() => {
    const title = toValue(options.title)
    const summary = toValue(options.description)
    document.title = title
    description.content = summary
    ogTitle.content = title
    ogDescription.content = summary
    ogUrl.content = window.location.href
    ogType.content = 'website'
    twitterCard.content = 'summary_large_image'
    canonical.href = window.location.href.split('?')[0]
  })
  onBeforeUnmount(() => canonical.remove())
}

