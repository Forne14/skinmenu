;(function () {
  const STORAGE_KEY = 'skinmenu_consent_v1'

  function readConsent() {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY)
      if (!raw) return { analytics: false, marketing: false }
      const parsed = JSON.parse(raw) || {}
      return {
        analytics: !!parsed.analytics,
        marketing: !!parsed.marketing,
      }
    } catch (_e) {
      return { analytics: false, marketing: false }
    }
  }

  function track(name, properties) {
    if (!name) return
    const consent = readConsent()

    if (consent.analytics && typeof window.gtag === 'function') {
      window.gtag('event', name, properties || {})
    }

    if (consent.marketing && typeof window.fbq === 'function') {
      window.fbq('trackCustom', name, properties || {})
    }
  }

  function syncConsentFields() {
    const consent = readConsent()
    document.querySelectorAll('[data-consent-analytics-field]').forEach((input) => {
      input.value = consent.analytics ? '1' : '0'
    })
  }

  window.skinmenuTrack = track
  document.addEventListener('DOMContentLoaded', syncConsentFields)
  window.addEventListener('skinmenu:consent-updated', syncConsentFields)
})()
