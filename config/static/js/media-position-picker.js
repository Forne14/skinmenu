;(function () {
  const DEBUG = typeof window !== 'undefined' && window.MEDIA_PICKER_DEBUG === true

  function log(...args) {
    if (!DEBUG) return
    console.log('[media-picker]', ...args)
  }
  function warn(...args) {
    console.warn('[media-picker]', ...args)
  }

  function clamp(n, min, max) {
    return Math.max(min, Math.min(max, n))
  }

  // Try multiple suffixes (Wagtail names usually end with "pos_x", not "-pos_x")
  function findInput(root, ...suffixes) {
    for (const s of suffixes) {
      const el = root.querySelector(`input[name$="${s}"], input[id$="${s}"]`)
      if (el) return el
    }
    return null
  }

  function findSelect(root, ...suffixes) {
    for (const s of suffixes) {
      const el = root.querySelector(`select[name$="${s}"], select[id$="${s}"]`)
      if (el) return el
    }
    return null
  }

  function findCheckbox(root, ...suffixes) {
    for (const s of suffixes) {
      const el = root.querySelector(
        `input[type="checkbox"][name$="${s}"], input[type="checkbox"][id$="${s}"]`
      )
      if (el) return el
    }
    return null
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

    xInput.dispatchEvent(new Event('input', { bubbles: true }))
    yInput.dispatchEvent(new Event('input', { bubbles: true }))
  }

  function removeExistingPreview(stage) {
    stage.querySelectorAll('[data-media-picker-media]').forEach((n) => n.remove())
  }

  function makeImgPreview(src) {
    const el = document.createElement('img')
    el.src = src
    el.alt = 'Preview'
    el.setAttribute('data-media-picker-media', 'true')
    el.className = 'media-picker-media'
    return el
  }

  function applyPlaybackRateToVideo(videoEl, blockRoot) {
    const rateSelect = findSelect(blockRoot, 'playback_rate', '-playback_rate')
    const apply = () => {
      const raw = (rateSelect && rateSelect.value) || '1.0'
      const rate = parseFloat(raw)
      if (!rate || Number.isNaN(rate)) return
      try {
        videoEl.playbackRate = rate
      } catch (e) {}
    }

    if (videoEl.readyState >= 1) apply()
    else videoEl.addEventListener('loadedmetadata', apply, { once: true })

    if (rateSelect) rateSelect.addEventListener('change', apply)
  }

  // Be strict: only accept a real chosen image preview (avoid matching random admin images/icons)
  function getPosterPreviewSrc(blockRoot) {
    const imageField = blockRoot.querySelector('[data-media-picker-image-field]')
    if (!imageField) return null

    // In Wagtail, the chosen image preview is typically img.chooser__image
    const img = imageField.querySelector('img.chooser__image')
    const src = img ? img.getAttribute('src') : null
    if (!src) return null
    const s = String(src).trim()
    if (!s) return null

    // guard against empty src resolving to current page
    try {
      const u = new URL(s, window.location.href)
      if (u.href === window.location.href) return null
    } catch (e) {}

    return s
  }

  function getDocumentIdFromChooserDOM(blockRoot) {
    const videoField = blockRoot.querySelector('[data-media-picker-video-field]')
    if (!videoField) return null

    // Hidden input usually exists and has the doc id
    const hidden = videoField.querySelector('input[type="hidden"]')
    const raw = hidden && hidden.value ? String(hidden.value).trim() : ''
    if (raw && /^\d+$/.test(raw)) return parseInt(raw, 10)

    return null
  }

  function setCachedDocument(blockRoot, id, url) {
    if (id != null) blockRoot.dataset.mediaPickerDocumentId = String(id)
    if (url) blockRoot.dataset.mediaPickerDocumentUrl = String(url)
  }

  function clearCachedDocument(blockRoot) {
    delete blockRoot.dataset.mediaPickerDocumentId
    delete blockRoot.dataset.mediaPickerDocumentUrl
  }

  function buildVideoEl(url, loopEnabled) {
    const v = document.createElement('video')
    v.setAttribute('data-media-picker-media', 'true')
    v.className = 'media-picker-media'
    v.muted = true
    v.playsInline = true
    v.autoplay = true
    v.preload = 'metadata'
    v.src = url
    v.loop = !!loopEnabled
    return v
  }

  function setPreview(stage, blockRoot) {
    const DOC_URL_ENDPOINT_BASE = '/admin/media-picker/document-url/'

    removeExistingPreview(stage)

    const loopBox = findCheckbox(blockRoot, 'loop', '-loop')
    const loopEnabled = loopBox ? !!loopBox.checked : true

    // VIDEO-FIRST

    const cachedUrl = blockRoot.dataset.mediaPickerDocumentUrl
    if (cachedUrl) {
      log('preview: cached video url', cachedUrl)
      const v = buildVideoEl(cachedUrl, loopEnabled)
      v.addEventListener('error', () => warn('video error', cachedUrl, v.error), { once: true })
      stage.prepend(v)
      applyPlaybackRateToVideo(v, blockRoot)
      const p = v.play && v.play()
      if (p && typeof p.catch === 'function') p.catch(() => {})
      return
    }

    const docId = getDocumentIdFromChooserDOM(blockRoot)
    if (docId) {
      const requestId = String(Date.now()) + ':' + String(Math.random()).slice(2)
      stage.dataset.mediaPickerRequestId = requestId

      log('preview: fetching doc url', docId)

      fetch(DOC_URL_ENDPOINT_BASE + docId + '/', { credentials: 'same-origin' })
        .then((r) => {
          if (!r.ok) throw new Error('Failed to fetch document URL: ' + r.status)
          return r.json()
        })
        .then((data) => {
          if (stage.dataset.mediaPickerRequestId !== requestId) return
          const url = data && data.url ? String(data.url) : ''
          if (!url) return

          setCachedDocument(blockRoot, docId, url)

          const v = buildVideoEl(url, loopEnabled)
          v.addEventListener('error', () => warn('video error', url, v.error), { once: true })

          removeExistingPreview(stage)
          stage.prepend(v)

          applyPlaybackRateToVideo(v, blockRoot)
          const p = v.play && v.play()
          if (p && typeof p.catch === 'function') p.catch(() => {})
          log('preview: inserted video', url)
        })
        .catch((err) => {
          warn('preview: doc url fetch failed', err)

          // fallback poster
          const posterSrc = getPosterPreviewSrc(blockRoot)
          if (posterSrc) {
            removeExistingPreview(stage)
            stage.prepend(makeImgPreview(posterSrc))
            log('preview: fallback poster')
          }
        })

      return
    }

    // No video -> poster fallback
    const posterSrc = getPosterPreviewSrc(blockRoot)
    if (posterSrc) {
      stage.prepend(makeImgPreview(posterSrc))
      log('preview: poster (no video)')
      return
    }

    log('preview: empty')
  }

  function initBlock(blockRoot) {
    const stage = blockRoot.querySelector('[data-media-picker-stage]')
    const target = blockRoot.querySelector('[data-media-picker-target]')

    if (!stage || !target) {
      log('initBlock: missing stage/target')
      return
    }

    // IMPORTANT: correct suffixes (no leading dash required)
    const xInput = findInput(blockRoot, 'pos_x', '-pos_x')
    const yInput = findInput(blockRoot, 'pos_y', '-pos_y')

    if (!xInput || !yInput) {
      log('initBlock: missing pos_x/pos_y inputs', { xInput: !!xInput, yInput: !!yInput })
      return
    }

    // Initial sync
    setPreview(stage, blockRoot)
    setTargetFromInputs(stage, target, xInput, yInput)

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

    // Chooser events
    blockRoot.addEventListener('document:chosen', (e) => {
      const doc = e && e.detail ? e.detail : null
      if (!doc || !doc.id || !doc.url) return
      log('document:chosen', doc.id, doc.url)
      setCachedDocument(blockRoot, doc.id, doc.url)
      setTimeout(() => setPreview(stage, blockRoot), 0)
    })

    blockRoot.addEventListener('document:removed', () => {
      log('document:removed')
      clearCachedDocument(blockRoot)
      setTimeout(() => setPreview(stage, blockRoot), 0)
    })

    // Re-render preview on input/change
    blockRoot.addEventListener('input', () => setTimeout(() => setPreview(stage, blockRoot), 0))
    blockRoot.addEventListener('change', () => setTimeout(() => setPreview(stage, blockRoot), 0))

    // Observe DOM changes
    let raf = null
    const schedule = () => {
      if (raf) return
      raf = requestAnimationFrame(() => {
        raf = null
        setPreview(stage, blockRoot)
      })
    }
    const obs = new MutationObserver(schedule)
    obs.observe(blockRoot, { childList: true, subtree: true })
  }

  function boot() {
    const blocks = document.querySelectorAll('[data-media-picker-block]')
    log('boot: found blocks', blocks.length)
    blocks.forEach(initBlock)

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
