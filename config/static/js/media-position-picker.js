// /config/static/js/media-position-picker.js
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
        `input[type="checkbox"][name$="${s}"], input[type="checkbox"][id$="${s}"]`,
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

  // ---------------------------
  // NEW: lightweight status overlay (doesn't affect existing flows)
  // ---------------------------
  function ensureStatusEl(stage) {
    let el = stage.querySelector('[data-media-picker-status]')
    if (el) return el

    el = document.createElement('div')
    el.setAttribute('data-media-picker-status', 'true')
    // Inline styles so we don't require CSS changes (production-safe)
    el.style.position = 'absolute'
    el.style.left = '10px'
    el.style.bottom = '10px'
    el.style.padding = '6px 8px'
    el.style.borderRadius = '8px'
    el.style.fontSize = '12px'
    el.style.color = 'rgba(255,255,255,0.92)'
    el.style.background = 'rgba(0,0,0,0.45)'
    el.style.zIndex = '5'
    el.style.pointerEvents = 'none'
    el.style.display = 'none'

    stage.appendChild(el)
    return el
  }

  function setStatus(stage, text) {
    const el = ensureStatusEl(stage)
    if (!text) {
      el.textContent = ''
      el.style.display = 'none'
      return
    }
    el.textContent = String(text)
    el.style.display = 'block'
  }

  // ---------------------------
  // NEW: Derivatives status fetch + best source selection
  // ---------------------------
  function fetchDerivativesStatus(docId) {
    // Global-ish throttle per docId (prevents bursts from rerenders + polling)
    const key = `mediaPickerLastStatusFetch_${docId}`
    const now = Date.now()
    const last = parseInt(sessionStorage.getItem(key) || '0', 10)

    // allow at most ~1 request per 2s per doc
    if (now - last < 2000) {
      // Return a promise that resolves to null; callers should handle it
      return Promise.resolve(null)
    }
    sessionStorage.setItem(key, String(now))

    const url = `/admin/media-derivatives/${docId}/status/`
    return fetch(url, { credentials: 'same-origin' }).then((r) => {
      if (!r.ok) throw new Error('Failed to fetch derivatives status: ' + r.status)
      return r.json()
    })
  }

  function pickBestVideoUrlFromStatus(data) {
    const list = (data && data.derivatives) || []
    const mp4 = list.find((d) => d && d.kind === 'mp4')
    const webm = list.find((d) => d && d.kind === 'webm')

    if (DEBUG) {
      log(
        'status:',
        list.map((d) => ({
          kind: d.kind,
          status: d.status,
          progress: d.progress,
          hasFile: !!d.file_url,
          hasPoster: !!d.poster_url,
          updated_at: d.updated_at,
        })),
      )
    }

    if (mp4 && mp4.status === 'ready' && mp4.file_url) {
      return {
        url: String(mp4.file_url),
        poster: mp4.poster_url ? String(mp4.poster_url) : '',
        status: mp4.status,
        progress: mp4.progress || 0,
        error: mp4.error || '',
      }
    }

    if (webm && webm.status === 'ready' && webm.file_url) {
      return {
        url: String(webm.file_url),
        poster: webm.poster_url ? String(webm.poster_url) : '',
        status: webm.status,
        progress: webm.progress || 0,
        error: webm.error || '',
      }
    }

    const processing =
      mp4 && mp4.status === 'processing' ? mp4 : webm && webm.status === 'processing' ? webm : null
    if (processing) {
      return {
        url: '',
        poster: processing.poster_url ? String(processing.poster_url) : '',
        status: processing.status,
        progress: processing.progress || 0,
        error: processing.error || '',
      }
    }

    const failed =
      mp4 && mp4.status === 'failed' ? mp4 : webm && webm.status === 'failed' ? webm : null
    if (failed) {
      return {
        url: '',
        poster: failed.poster_url ? String(failed.poster_url) : '',
        status: failed.status,
        progress: failed.progress || 0,
        error: failed.error || '',
      }
    }

    return { url: '', poster: '', status: '', progress: 0, error: '' }
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
      setStatus(stage, '') // clear any prior status overlay
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

      // NEW: Poll derivatives status first, then fall back to original doc url.
      // This keeps existing behavior working even if derivatives endpoint fails.
      const pollKey = `mediaPickerPoll_${docId}`
      const existingPoll = stage.dataset[pollKey]
      if (existingPoll) {
        // Avoid stacking intervals on repeated re-renders
        try {
          clearTimeout(parseInt(existingPoll, 10))
        } catch (e) {}
        delete stage.dataset[pollKey]
      }

      function renderVideoUrl(url, posterUrl) {
        if (stage.dataset.mediaPickerRequestId !== requestId) return
        if (!url) return false

        setCachedDocument(blockRoot, docId, url)

        const v = buildVideoEl(url, loopEnabled)
        if (posterUrl) v.poster = posterUrl

        v.addEventListener('error', () => warn('video error', url, v.error), { once: true })

        removeExistingPreview(stage)
        stage.prepend(v)

        applyPlaybackRateToVideo(v, blockRoot)
        const p = v.play && v.play()
        if (p && typeof p.catch === 'function') p.catch(() => {})
        log('preview: inserted video', url)
        return true
      }

      function renderPosterFallback(posterUrl) {
        if (stage.dataset.mediaPickerRequestId !== requestId) return
        if (!posterUrl) return false
        removeExistingPreview(stage)
        stage.prepend(makeImgPreview(posterUrl))
        return true
      }

      function fetchOriginalDocUrlFallback() {
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

            setStatus(stage, '') // clear status
            setCachedDocument(blockRoot, docId, url)

            const v = buildVideoEl(url, loopEnabled)
            v.addEventListener('error', () => warn('video error', url, v.error), { once: true })

            removeExistingPreview(stage)
            stage.prepend(v)

            applyPlaybackRateToVideo(v, blockRoot)
            const p = v.play && v.play()
            if (p && typeof p.catch === 'function') p.catch(() => {})
            log('preview: inserted video (fallback)', url)
          })
          .catch((err) => {
            warn('preview: doc url fetch failed', err)

            // fallback poster
            const posterSrc = getPosterPreviewSrc(blockRoot)
            if (posterSrc) {
              setStatus(stage, '')
              removeExistingPreview(stage)
              stage.prepend(makeImgPreview(posterSrc))
              log('preview: fallback poster')
            }
          })
      }

      // First attempt: derivatives status
      // First attempt: derivatives status (single setTimeout loop, not setInterval)
      let pollTimer = null
      let pollInFlight = false

      function stopPoll() {
        if (pollTimer) window.clearTimeout(pollTimer)
        pollTimer = null
        pollInFlight = false
      }

      function schedulePoll(delayMs) {
        stopPoll()
        pollTimer = window.setTimeout(pollTick, delayMs)
        // store so a rerender can cancel it
        stage.dataset[pollKey] = String(pollTimer)
      }

      function pollTick() {
        if (stage.dataset.mediaPickerRequestId !== requestId) return
        if (pollInFlight) {
          // try again shortly; don't stack calls
          schedulePoll(250)
          return
        }
        pollInFlight = true

        fetchDerivativesStatus(docId)
          .then((data) => {
            pollInFlight = false
            if (stage.dataset.mediaPickerRequestId !== requestId) return

            // throttled fetch may return null
            if (!data) {
              schedulePoll(2000)
              return
            }

            const best = pickBestVideoUrlFromStatus(data)

            if (best.status === 'ready' && best.url) {
              setStatus(stage, '')
              renderVideoUrl(best.url, best.poster)
              stopPoll()
              delete stage.dataset[pollKey]
              return
            }

            if (best.status === 'failed') {
              setStatus(stage, 'Encoding failed (using original)')
              if (best.poster) renderPosterFallback(best.poster)
              stopPoll()
              delete stage.dataset[pollKey]
              fetchOriginalDocUrlFallback()
              return
            }

            if (best.status === 'processing') {
              const pct =
                typeof best.progress === 'number'
                  ? best.progress
                  : parseInt(best.progress || '0', 10)

              // If progress is 0 and no poster yet, we're probably still extracting poster / probing
              if ((!best.poster || !best.poster.length) && (pct === 0 || Number.isNaN(pct))) {
                setStatus(stage, 'Preparing…')
              } else if (pct >= 0) {
                setStatus(stage, `Encoding… ${pct}%`)
              } else {
                setStatus(stage, 'Encoding…')
              }

              if (best.poster) renderPosterFallback(best.poster)
              schedulePoll(2500)
              return
            }

            // no useful derivative info -> fallback to original and stop polling
            setStatus(stage, '')
            stopPoll()
            delete stage.dataset[pollKey]
            fetchOriginalDocUrlFallback()
          })
          .catch((err) => {
            pollInFlight = false
            warn('preview: derivatives poll failed', err)

            // On repeated failures, don't hammer; fall back.
            setStatus(stage, '')
            stopPoll()
            delete stage.dataset[pollKey]
            fetchOriginalDocUrlFallback()
          })
      }

      // One-shot initial fetch; if processing, start timeout loop.
      fetchDerivativesStatus(docId)
        .then((data) => {
          if (stage.dataset.mediaPickerRequestId !== requestId) return

          if (!data) {
            // throttled; try again once shortly
            schedulePoll(2000)
            return
          }

          const best = pickBestVideoUrlFromStatus(data)

          if (best.status === 'ready' && best.url) {
            setStatus(stage, '')
            renderVideoUrl(best.url, best.poster)
            stopPoll()
            delete stage.dataset[pollKey]
            return
          }

          if (best.status === 'failed') {
            setStatus(stage, 'Encoding failed (using original)')
            if (best.poster) renderPosterFallback(best.poster)
            stopPoll()
            delete stage.dataset[pollKey]
            fetchOriginalDocUrlFallback()
            return
          }

          if (best.status === 'processing') {
            const pct =
              typeof best.progress === 'number' ? best.progress : parseInt(best.progress || '0', 10)

            // If progress is 0 and no poster yet, we're probably still extracting poster / probing
            if ((!best.poster || !best.poster.length) && (pct === 0 || Number.isNaN(pct))) {
              setStatus(stage, 'Preparing…')
            } else if (pct >= 0) {
              setStatus(stage, `Encoding… ${pct}%`)
            } else {
              setStatus(stage, 'Encoding…')
            }

            if (best.poster) renderPosterFallback(best.poster)
            schedulePoll(2500)
            return
          }

          // No derivative info => fallback
          setStatus(stage, '')
          stopPoll()
          delete stage.dataset[pollKey]
          fetchOriginalDocUrlFallback()
        })
        .catch((err) => {
          warn('preview: derivatives status fetch failed', err)
          setStatus(stage, '')
          stopPoll()
          delete stage.dataset[pollKey]
          fetchOriginalDocUrlFallback()
        })

      return
    }

    // No video -> poster fallback
    const posterSrc = getPosterPreviewSrc(blockRoot)
    if (posterSrc) {
      setStatus(stage, '')
      stage.prepend(makeImgPreview(posterSrc))
      log('preview: poster (no video)')
      return
    }

    setStatus(stage, '')
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
      // Keep caching behavior — but note: derivative preview may overwrite it later.
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
    let isRendering = false

    const schedule = () => {
      if (isRendering) return
      if (raf) return
      raf = requestAnimationFrame(() => {
        raf = null
        isRendering = true
        try {
          setPreview(stage, blockRoot)
        } finally {
          isRendering = false
        }
      })
    }

    const obs = new MutationObserver((mutations) => {
      // Ignore mutations inside the stage, because setPreview mutates there.
      for (const m of mutations) {
        if (m.target && stage.contains(m.target)) return
      }
      schedule()
    })

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
