const MAX_IMAGE_RETRIES = 4
const RETRY_DELAYS = [450, 1400, 3400, 7000]

export function installImageRecovery(): () => void {
  const onError = (event: Event) => {
    const image = event.target
    if (!(image instanceof HTMLImageElement) || !image.src) return

    const retries = Number(image.dataset.retryCount || 0)
    if (retries >= MAX_IMAGE_RETRIES) {
      image.classList.remove('is-retrying')
      image.classList.add('has-load-error')
      return
    }

    const original = image.dataset.originalSrc || image.currentSrc || image.src
    image.dataset.originalSrc = original
    image.dataset.retryCount = String(retries + 1)
    image.classList.add('is-retrying')

    const jitter = Math.floor(Math.random() * 350)
    window.setTimeout(() => {
      const retryUrl = new URL(original, window.location.href)
      retryUrl.searchParams.set('_retry', `${Date.now()}-${retries + 1}`)
      image.src = retryUrl.toString()
    }, RETRY_DELAYS[retries] + jitter)
  }

  const onLoad = (event: Event) => {
    const image = event.target
    if (!(image instanceof HTMLImageElement)) return
    image.classList.remove('is-retrying', 'has-load-error')
  }

  document.addEventListener('error', onError, true)
  document.addEventListener('load', onLoad, true)
  return () => {
    document.removeEventListener('error', onError, true)
    document.removeEventListener('load', onLoad, true)
  }
}
