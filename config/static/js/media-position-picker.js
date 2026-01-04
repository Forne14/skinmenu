;(function () {
  function clamp(n, min, max) {
    return Math.max(min, Math.min(max, n))
  }

  function findInput(root, nameEndsWith) {
    return root.querySelector(`input[name$="${nameEndsWith}"]`)
  }

  function setTargetFromInputs(stage, target, xInput, yInput) {
    const x = clamp(parseInt(xInput.value || '50', 10), 0, 100)
    const y = clamp(parseInt(yInput.value || '50', 10), 0, 100)
    target.style.left = x + '%'
    target.style.top = y + '%'
    stage.style.setProperty('--focus-x', x + '%')
    stage.style.setProperty('--focus-y', y + '%')
  }

  function setInputsFromPointer(stage, target, xInput, yInput, clientX, clientY) {
    const rect = stage.getBoundingClientRect()
    const x = clamp(((clientX - rect.left) / rect.width) * 100, 0, 100)
    const y = clamp(((clientY - rect.top) / rect.height) * 100, 0, 100)

    const xi = Math.round(x)
    const yi = Math.round(y)

    xInput.value = String(xi)
    yInput.value = String(yi)

    target.style.left = xi + '%'
    target.style.top = yi + '%'
    stage.style.setProperty('--focus-x', xi + '%')
    stage.style.setProperty('--focus-y', yi + '%')

    // trigger show/hide + Wagtail change detection
    xInput.dispatchEvent(new Event('input', { bubbles: true }))
    yInput.dispatchEvent(new Event('input', { bubbles: true }))
  }

  function setPreview(stage, blockRoot) {
    // Try to find a selected document (video) or image chooser preview.
    // Wagtail’s chooser markup can vary by version; we’ll do a resilient approach:
    // - If a document is chosen, there is usually an <a> with href to the file or a data attribute.
    // - If an image is chosen, there is often an <img> preview in the chooser.
    //
    // We’ll just mirror any existing preview media we can find into the stage.

    // Clear previous media
    const existing = stage.querySelector('[data-media-picker-media]')
    if (existing) existing.remove()

    // Prefer: image preview inside chooser
    const img = blockRoot.querySelector(
      '.image-chooser img, .wagtail-image-chooser img, img.chooser__image'
    )
    if (img && img.src) {
      const clone = document.createElement('img')
      clone.src = img.src
      clone.alt = 'Preview'
      clone.setAttribute('data-media-picker-media', 'true')
      clone.className = 'media-picker-media'
      stage.prepend(clone)
      return
    }

    // Next: document link (video file)
    const docLink = blockRoot.querySelector(
      '.document-chooser a[href], .wagtail-document-chooser a[href], a.chooser__title[href]'
    )
    if (docLink && docLink.href) {
      const v = document.createElement('video')
      v.src = docLink.href
      v.muted = true
      v.playsInline = true
      v.loop = true
      v.autoplay = true
      v.setAttribute('data-media-picker-media', 'true')
      v.className = 'media-picker-media'
      stage.prepend(v)

      const p = v.play && v.play()
      if (p && typeof p.catch === 'function') p.catch(() => {})
    }
  }

  function initBlock(blockRoot) {
    const stage = blockRoot.querySelector('[data-media-picker-stage]')
    const target = blockRoot.querySelector('[data-media-picker-target]')
    if (!stage || !target) return

    const xInput = findInput(blockRoot, '-pos_x')
    const yInput = findInput(blockRoot, '-pos_y')
    if (!xInput || !yInput) return

    setPreview(stage, blockRoot)
    setTargetFromInputs(stage, target, xInput, yInput)

    // Update target if someone edits number inputs
    xInput.addEventListener('input', () => setTargetFromInputs(stage, target, xInput, yInput))
    yInput.addEventListener('input', () => setTargetFromInputs(stage, target, xInput, yInput))

    // Drag handling
    let down = false

    function onDown(e) {
      down = true
      stage.setPointerCapture?.(e.pointerId)
      setInputsFromPointer(stage, target, xInput, yInput, e.clientX, e.clientY)
    }
    function onMove(e) {
      if (!down) return
      setInputsFromPointer(stage, target, xInput, yInput, e.clientX, e.clientY)
    }
    function onUp() {
      down = false
    }

    stage.addEventListener('pointerdown', onDown)
    stage.addEventListener('pointermove', onMove)
    stage.addEventListener('pointerup', onUp)
    stage.addEventListener('pointercancel', onUp)

    // When chooser changes, refresh preview (listen broadly)
    blockRoot.addEventListener('change', () => {
      setTimeout(() => {
        setPreview(stage, blockRoot)
        setTargetFromInputs(stage, target, xInput, yInput)
      }, 0)
    })
  }

  function boot() {
    document.querySelectorAll('[data-media-picker-block]').forEach(initBlock)

    // StreamField blocks can be added dynamically. Observe and init new ones.
    const obs = new MutationObserver((mutations) => {
      for (const m of mutations) {
        m.addedNodes.forEach((n) => {
          if (!(n instanceof HTMLElement)) return
          if (n.matches && n.matches('[data-media-picker-block]')) initBlock(n)
          n.querySelectorAll?.('[data-media-picker-block]').forEach(initBlock)
        })
      }
    })
    obs.observe(document.body, { childList: true, subtree: true })
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot)
  else boot()
})()
