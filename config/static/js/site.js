;(function () {
  function qs(sel, root) {
    return (root || document).querySelector(sel)
  }
  function qsa(sel, root) {
    return Array.from((root || document).querySelectorAll(sel))
  }

  // Mobile nav toggle
  const mobileToggle = qs('[data-mobile-nav-toggle]')
  const mobileNav = qs('[data-mobile-nav]')

  if (mobileToggle && mobileNav) {
    mobileToggle.addEventListener('click', () => {
      const isOpen = !mobileNav.classList.contains('hidden')
      mobileNav.classList.toggle('hidden', isOpen)
      mobileToggle.setAttribute('aria-expanded', String(!isOpen))
    })
  }

  // Mobile subnav toggle
  const mobileSubToggle = qs('[data-mobile-subnav-toggle]')
  const mobileSubNav = qs('[data-mobile-subnav]')

  if (mobileSubToggle && mobileSubNav) {
    mobileSubToggle.addEventListener('click', () => {
      const isOpen = !mobileSubNav.classList.contains('hidden')
      mobileSubNav.classList.toggle('hidden', isOpen)
      mobileSubToggle.setAttribute('aria-expanded', String(!isOpen))
    })
  }

  // Desktop dropdown
  qsa('[data-dropdown]').forEach((wrap) => {
    const btn = qs('[data-dropdown-button]', wrap)
    const menu = qs('[data-dropdown-menu]', wrap)

    if (!btn || !menu) return

    function setOpen(open) {
      menu.dataset.open = open ? 'true' : 'false'
      btn.setAttribute('aria-expanded', String(open))
    }

    setOpen(false)

    btn.addEventListener('click', (e) => {
      e.stopPropagation()
      setOpen(menu.dataset.open !== 'true')
    })

    // Close when clicking outside
    document.addEventListener('click', () => setOpen(false))

    // Basic ESC close for keyboard users
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') setOpen(false)
    })
  })

  // Respect reduced motion preference: nothing to do here yet
  // (We’ll keep animations purely CSS-based and minimal.)
})()
