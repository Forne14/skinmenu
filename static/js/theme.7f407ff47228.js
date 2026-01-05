;(function () {
  const STORAGE_KEY = 'skinmenu_theme'

  function getPreferredTheme() {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === 'light' || stored === 'dark') return stored
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light'
  }

  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme
    const btns = document.querySelectorAll('[data-theme-toggle]')
    btns.forEach((btn) => {
      btn.setAttribute('aria-pressed', theme === 'dark' ? 'true' : 'false')
      btn.setAttribute('data-theme', theme)
    })
  }

  function toggleTheme() {
    const current = document.documentElement.dataset.theme || 'light'
    const next = current === 'dark' ? 'light' : 'dark'
    localStorage.setItem(STORAGE_KEY, next)
    applyTheme(next)
  }

  // Initialize ASAP
  const initial = getPreferredTheme()
  applyTheme(initial)

  // Wire toggle
  document.addEventListener('click', (e) => {
    const t = e.target.closest('[data-theme-toggle]')
    if (!t) return
    e.preventDefault()
    toggleTheme()
  })
})()
