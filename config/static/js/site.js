;(function () {
  function qs(sel, root) {
    return (root || document).querySelector(sel)
  }
  function qsa(sel, root) {
    return Array.from((root || document).querySelectorAll(sel))
  }

  // =========================
  // Mobile nav toggle
  // =========================
  const mobileToggle = qs('[data-mobile-nav-toggle]')
  const mobileNav = qs('[data-mobile-nav]')

  if (mobileToggle && mobileNav) {
    mobileToggle.addEventListener('click', () => {
      const isOpen = !mobileNav.classList.contains('hidden')
      mobileNav.classList.toggle('hidden', isOpen)
      mobileToggle.setAttribute('aria-expanded', String(!isOpen))
    })
  }

  // Mobile subnav toggle (supports single submenu for now)
  const mobileSubToggle = qs('[data-mobile-subnav-toggle]')
  const mobileSubNav = qs('[data-mobile-subnav]')
  if (mobileSubToggle && mobileSubNav) {
    mobileSubToggle.addEventListener('click', () => {
      const isOpen = !mobileSubNav.classList.contains('hidden')
      mobileSubNav.classList.toggle('hidden', isOpen)
      mobileSubToggle.setAttribute('aria-expanded', String(!isOpen))
    })
  }

  // =========================
  // Desktop dropdowns
  // =========================
  const dropdowns = qsa('[data-dropdown]')
  function closeAllDropdowns() {
    dropdowns.forEach((wrap) => {
      const btn = qs('[data-dropdown-button]', wrap)
      const menu = qs('[data-dropdown-menu]', wrap)
      if (!btn || !menu) return
      menu.dataset.open = 'false'
      btn.setAttribute('aria-expanded', 'false')
    })
  }
  function toggleDropdown(wrap) {
    const btn = qs('[data-dropdown-button]', wrap)
    const menu = qs('[data-dropdown-menu]', wrap)
    if (!btn || !menu) return
    const open = menu.dataset.open === 'true'
    closeAllDropdowns()
    menu.dataset.open = open ? 'false' : 'true'
    btn.setAttribute('aria-expanded', open ? 'false' : 'true')
  }

  dropdowns.forEach((wrap) => {
    const btn = qs('[data-dropdown-button]', wrap)
    const menu = qs('[data-dropdown-menu]', wrap)
    if (!btn || !menu) return
    menu.dataset.open = 'false'
    btn.setAttribute('aria-expanded', 'false')

    btn.addEventListener('click', (e) => {
      e.preventDefault()
      e.stopPropagation()
      toggleDropdown(wrap)
    })
  })

  document.addEventListener('click', (e) => {
    // close if click is outside any dropdown
    const insideDropdown = e.target.closest('[data-dropdown]')
    if (!insideDropdown) closeAllDropdowns()
  })

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeAllDropdowns()
  })
})()
