;(function () {
  const STORAGE_KEY = 'skinmenu_consent_v1'

  function readConsent() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) return null
      const parsed = JSON.parse(raw)
      if (!parsed || typeof parsed !== 'object') return null
      return {
        necessary: true,
        analytics: !!parsed.analytics,
        marketing: !!parsed.marketing,
      }
    } catch {
      return null
    }
  }

  function writeConsent(consent) {
    const payload = {
      analytics: !!consent.analytics,
      marketing: !!consent.marketing,
      ts: Date.now(),
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
    window.SKINMENU_CONSENT = {
      has(category) {
        const c = readConsent()
        if (!c) return category === 'necessary'
        return !!c[category]
      },
    }
  }

  function ensureGlobal() {
    window.SKINMENU_CONSENT = {
      has(category) {
        const c = readConsent()
        if (!c) return category === 'necessary'
        return !!c[category]
      },
    }
  }

  function showBanner() {
    const el = document.querySelector('[data-cookie-banner]')
    if (!el) return
    el.hidden = false
  }

  function hideBanner() {
    const el = document.querySelector('[data-cookie-banner]')
    if (!el) return
    el.hidden = true
  }

  function init() {
    ensureGlobal()

    const existing = readConsent()
    if (!existing) showBanner()

    const banner = document.querySelector('[data-cookie-banner]')
    if (!banner) return

    const panel = banner.querySelector('[data-cookie-panel]')
    const btnAccept = banner.querySelector('[data-cookie-accept]')
    const btnReject = banner.querySelector('[data-cookie-reject]')
    const btnCustomise = banner.querySelector('[data-cookie-customise]')
    const btnSave = banner.querySelector('[data-cookie-save]')

    const cbAnalytics = banner.querySelector('[data-cookie-analytics]')
    const cbMarketing = banner.querySelector('[data-cookie-marketing]')

    if (existing) {
      if (cbAnalytics) cbAnalytics.checked = !!existing.analytics
      if (cbMarketing) cbMarketing.checked = !!existing.marketing
    }

    btnAccept?.addEventListener('click', () => {
      writeConsent({ analytics: true, marketing: true })
      hideBanner()
      window.dispatchEvent(new CustomEvent('skinmenu:consent-updated'))
    })

    btnReject?.addEventListener('click', () => {
      writeConsent({ analytics: false, marketing: false })
      hideBanner()
      window.dispatchEvent(new CustomEvent('skinmenu:consent-updated'))
    })

    btnCustomise?.addEventListener('click', () => {
      panel?.classList.toggle('hidden')
    })

    btnSave?.addEventListener('click', () => {
      writeConsent({
        analytics: !!cbAnalytics?.checked,
        marketing: !!cbMarketing?.checked,
      })
      hideBanner()
      window.dispatchEvent(new CustomEvent('skinmenu:consent-updated'))
    })
  }

  document.addEventListener('DOMContentLoaded', init)
})()
