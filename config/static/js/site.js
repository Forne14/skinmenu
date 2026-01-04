/* SKINMENU site interactions:
   - Header dropdown
   - Mobile drawer + subnav
   - Lightweight carousels (hero + reviews)
   - Scroll-snap rails (treatments)
   - Generic prev/next scrollers (team/offering carousels)
   - Optional single-open accordions for <details data-accordion>
*/

;(function () {
  // ---------------------------
  // Dropdown (desktop)
  // ---------------------------
  function initDropdowns() {
    const dropdowns = document.querySelectorAll('[data-dropdown]')
    if (!dropdowns.length) return

    function closeAll() {
      dropdowns.forEach((d) => {
        d.dataset.open = 'false'
        const btn = d.querySelector('[data-dropdown-button]')
        if (btn) btn.setAttribute('aria-expanded', 'false')
        const menu = d.querySelector('[data-dropdown-menu]')
        if (menu) menu.dataset.open = 'false'
      })
    }

    dropdowns.forEach((d) => {
      const btn = d.querySelector('[data-dropdown-button]')
      const menu = d.querySelector('[data-dropdown-menu]')
      if (!btn || !menu) return

      d.dataset.open = 'false'
      menu.dataset.open = 'false'

      btn.addEventListener('click', (e) => {
        e.stopPropagation()
        const open = d.dataset.open === 'true'
        closeAll()
        d.dataset.open = open ? 'false' : 'true'
        menu.dataset.open = open ? 'false' : 'true'
        btn.setAttribute('aria-expanded', open ? 'false' : 'true')
      })
    })

    document.addEventListener('click', () => closeAll())
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeAll()
    })
  }

  // ---------------------------
  // Mobile nav
  // ---------------------------
  function initMobileNav() {
    const toggle = document.querySelector('[data-mobile-nav-toggle]')
    const panel = document.querySelector('[data-mobile-nav]')
    if (!toggle || !panel) return

    toggle.addEventListener('click', () => {
      const isOpen = panel.classList.contains('hidden') === false
      panel.classList.toggle('hidden')
      toggle.setAttribute('aria-expanded', isOpen ? 'false' : 'true')
    })

    const subToggle = document.querySelector('[data-mobile-subnav-toggle]')
    const subnav = document.querySelector('[data-mobile-subnav]')
    if (subToggle && subnav) {
      subToggle.addEventListener('click', () => {
        const isOpen = subnav.classList.contains('hidden') === false
        subnav.classList.toggle('hidden')
        subToggle.setAttribute('aria-expanded', isOpen ? 'false' : 'true')
      })
    }
  }

  // ---------------------------
  // Carousels (hero + reviews)
  // ---------------------------
  function initCarousels() {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const carousels = document.querySelectorAll('[data-carousel]')
    if (!carousels.length) return

    carousels.forEach((root) => {
      const track = root.querySelector('[data-carousel-track]')
      const slides = Array.from(root.querySelectorAll('[data-carousel-slide]'))
      const dotsWrap = root.querySelector('[data-carousel-dots]')
      const dots = dotsWrap ? Array.from(dotsWrap.querySelectorAll('[data-carousel-dot]')) : []

      if (!track || slides.length <= 1) {
        // Still ensure first slide is visible if we're using fade layers (hero)
        slides.forEach((s, i) => {
          if (s.style && root.dataset.carousel === 'hero') {
            if (i === 0) {
              s.style.opacity = '1'
              s.dataset.active = 'true'
            } else {
              s.style.opacity = '0'
              s.dataset.active = 'false'
            }
          }
        })
        return
      }

      const mode = root.dataset.carousel === 'hero' ? 'hero' : 'track'
      let index = 0
      let timer = null

      function apply(indexNext) {
        index = Math.max(0, Math.min(slides.length - 1, indexNext))

        if (mode === 'hero') {
          slides.forEach((s, i) => {
            const active = i === index
            s.dataset.active = active ? 'true' : 'false'
            s.style.opacity = active ? '1' : '0'
          })
        } else {
          const slide = slides[index]
          const left = slide.offsetLeft
          track.style.transform = `translateX(${-left}px)`
          slides.forEach((s, i) => (s.dataset.active = i === index ? 'true' : 'false'))
        }

        dots.forEach((d, i) => {
          if (i === index) d.setAttribute('aria-current', 'true')
          else d.removeAttribute('aria-current')
        })
      }

      function next() {
        apply((index + 1) % slides.length)
      }

      function startAutoplay() {
        if (prefersReducedMotion) return
        if (root.dataset.autoplay !== 'true') return
        const interval = parseInt(root.dataset.interval || '8000', 10)
        stopAutoplay()
        timer = window.setInterval(next, interval)
      }

      function stopAutoplay() {
        if (timer) window.clearInterval(timer)
        timer = null
      }

      // Dots
      dots.forEach((btn) => {
        btn.addEventListener('click', () => {
          const i = parseInt(btn.getAttribute('data-carousel-dot'), 10)
          apply(i)
          startAutoplay()
        })
      })

      // Swipe/drag
      let pointerDown = false
      let startX = 0
      let lastX = 0
      let moved = false

      function onDown(clientX) {
        pointerDown = true
        moved = false
        startX = clientX
        lastX = clientX
        stopAutoplay()
      }

      function onMove(clientX) {
        if (!pointerDown) return
        const dx = clientX - startX
        if (Math.abs(dx) > 8) moved = true
        lastX = clientX
      }

      function onUp() {
        if (!pointerDown) return
        pointerDown = false

        const dx = lastX - startX
        if (moved && Math.abs(dx) > 40) {
          if (dx < 0) apply(index + 1)
          else apply(index - 1)
        }

        startAutoplay()
      }

      root.addEventListener('pointerdown', (e) => onDown(e.clientX), { passive: true })
      root.addEventListener('pointermove', (e) => onMove(e.clientX), { passive: true })
      root.addEventListener('pointerup', onUp, { passive: true })
      root.addEventListener('pointercancel', onUp, { passive: true })

      // Pause on hover/focus (desktop polish)
      root.addEventListener('mouseenter', stopAutoplay)
      root.addEventListener('mouseleave', startAutoplay)
      root.addEventListener('focusin', stopAutoplay)
      root.addEventListener('focusout', startAutoplay)

      apply(0)
      startAutoplay()
    })
  }

  // ---------------------------
  // Scroll-snap rails (treatments grid)
  // ---------------------------
  function initHscrollDots() {
    const rails = document.querySelectorAll('[data-hscroll]')
    if (!rails.length) return

    rails.forEach((root) => {
      const track = root.querySelector('[data-hscroll-track]')
      const slides = Array.from(root.querySelectorAll('[data-hscroll-slide]'))
      const dotsWrap = root.querySelector('[data-hscroll-dots]')
      const dots = dotsWrap ? Array.from(dotsWrap.querySelectorAll('[data-hscroll-dot]')) : []

      if (!track || slides.length <= 1 || !dots.length) return

      function setActive(i) {
        dots.forEach((d, idx) => {
          if (idx === i) d.setAttribute('aria-current', 'true')
          else d.removeAttribute('aria-current')
        })
      }

      function scrollToIndex(i) {
        const slide = slides[i]
        if (!slide) return
        track.scrollTo({ left: slide.offsetLeft - track.offsetLeft, behavior: 'smooth' })
        setActive(i)
      }

      dots.forEach((btn) => {
        btn.addEventListener('click', () => {
          const i = parseInt(btn.getAttribute('data-hscroll-dot') || '0', 10)
          scrollToIndex(i)
        })
      })

      let raf = null
      function onScroll() {
        if (raf) return
        raf = window.requestAnimationFrame(() => {
          raf = null
          const x = track.scrollLeft + track.clientWidth * 0.33
          let active = 0
          for (let i = 0; i < slides.length; i++) {
            if (slides[i].offsetLeft <= x) active = i
          }
          setActive(active)
        })
      }

      track.addEventListener('scroll', onScroll, { passive: true })
      onScroll()
    })
  }

  // ---------------------------
  // Generic prev/next scrollers
  // Used by templates with:
  //   data-carousel-track="team"
  //   data-carousel-prev="team"
  //   data-carousel-next="team"
  // ---------------------------
  function initNamedCarousels() {
    function scrollTrack(key, dir) {
      if (!key) return
      const track = document.querySelector(
        `[data-carousel-track="${CSS && CSS.escape ? CSS.escape(key) : key}"]`
      )
      if (!track) return

      // Determine step size: prefer first child width + gap
      const child = track.querySelector(':scope > *')
      const gap = 16
      const step = child ? child.getBoundingClientRect().width + gap : track.clientWidth * 0.8

      track.scrollBy({ left: dir * step, behavior: 'smooth' })
    }

    document.addEventListener('click', (e) => {
      const prev = e.target.closest('[data-carousel-prev]')
      const next = e.target.closest('[data-carousel-next]')
      if (prev) scrollTrack(prev.getAttribute('data-carousel-prev'), -1)
      if (next) scrollTrack(next.getAttribute('data-carousel-next'), 1)
    })
  }

  // ---------------------------
  // Accessible <details> accordion:
  // If you add data-accordion to <details>, opening one closes siblings
  // Optionally scope by wrapping in an element with data-accordion-scope
  // ---------------------------
  function initAccordions() {
    document.addEventListener(
      'toggle',
      (e) => {
        const el = e.target
        if (!(el instanceof HTMLDetailsElement)) return
        if (!el.hasAttribute('data-accordion')) return
        if (!el.open) return

        const scope = el.closest('[data-accordion-scope]') || document
        const all = scope.querySelectorAll('details[data-accordion]')
        all.forEach((d) => {
          if (d !== el) d.open = false
        })
      },
      true
    )
  }

  // ---------------------------
  // Boot
  // ---------------------------
  document.addEventListener('DOMContentLoaded', () => {
    initDropdowns()
    initMobileNav()
    initCarousels()
    initHscrollDots()

    // New behavior (does not touch existing ones unless you add the attributes)
    initNamedCarousels()
    initAccordions()
  })
})()
