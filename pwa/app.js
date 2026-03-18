// ── State ──────────────────────────────────────────────
const state = {
  currentPage: 'home',
  risk: 'SAFE',
  count: 0,
  message: 'System ready',
  zones: [],
  stats: {},
  history: [],
  cameraActive: false,
  ws: null,
  stream: null,
  frameInterval: null,
  analysisInterval: null
}

// ── API Base URL ────────────────────────────────────────
// Change this to your Hugging Face URL for production
const API_BASE = window.location.origin.includes('localhost')
  ? 'http://localhost:8000'
  : 'https://4ak1f-cdms.hf.space'

// ── Splash Screen ───────────────────────────────────────
window.addEventListener('load', () => {
  setTimeout(() => {
    document.getElementById('splash').classList.add('hidden')
    setTimeout(() => {
      document.getElementById('splash').style.display = 'none'
    }, 500)
  }, 2500)

  loadStats()
  loadHistory()
  setInterval(loadStats, 10000)
  registerSW()
})

// ── Service Worker ──────────────────────────────────────
function registerSW() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/mobile/sw.js')
      .then(() => console.log('SW registered'))
      .catch(e => console.log('SW failed:', e))
  }
}

// ── Navigation ──────────────────────────────────────────
function navigate(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'))
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'))
  document.getElementById(`page-${page}`).classList.add('active')
  document.getElementById(`nav-${page}`).classList.add('active')
  state.currentPage = page

  if (page !== 'camera' && state.cameraActive) stopCamera()
}

// ── Risk Config ─────────────────────────────────────────
const RISK = {
  SAFE:    { color: '#00ff88', pct: 0.25, label: 'ALL CLEAR' },
  WARNING: { color: '#ff9500', pct: 0.65, label: 'WARNING'   },
  DANGER:  { color: '#ff3b5c', pct: 1.0,  label: 'DANGER'    },
}

// ── Update Risk Display ─────────────────────────────────
function updateRisk(count, risk, message, zones) {
  state.risk    = risk
  state.count   = count
  state.message = message
  state.zones   = zones || []

  const cfg    = RISK[risk] || RISK.SAFE
  const radius = 68
  const circ   = 2 * Math.PI * radius
  const offset = circ * (1 - cfg.pct)

  // Update SVG ring
  const circle = document.getElementById('riskCircle')
  if (circle) {
    circle.style.stroke           = cfg.color
    circle.style.strokeDashoffset = offset
    circle.style.filter           = `drop-shadow(0 0 12px ${cfg.color})`
  }

  // Update text
  const els = {
    'riskNumber':  count,
    'riskLabel':   cfg.label,
    'riskMessage': message,
  }
  Object.entries(els).forEach(([id, val]) => {
    const el = document.getElementById(id)
    if (el) el.textContent = val
  })

  const labelEl = document.getElementById('riskLabel')
  if (labelEl) labelEl.style.color = cfg.color

  // Update zones
  updateZones(zones)

  // Show alert if danger
  if (risk === 'DANGER') showAlert(message)
}

// ── Zone Grid ───────────────────────────────────────────
function updateZones(zones) {
  const grid = document.getElementById('zoneGrid')
  if (!grid) return

  const display = zones?.length ? zones : Array.from({ length: 9 }, (_, i) => ({
    zone: `Zone ${i + 1}`, risk: 'SAFE', count: 0
  }))

  grid.innerHTML = display.map(z => `
    <div class="zone-cell zone-${z.risk.toLowerCase()}">
      <div class="zone-name">${z.zone}</div>
      <div class="zone-risk">${z.risk}</div>
      <div class="zone-count">~${z.count}</div>
    </div>
  `).join('')
}

// ── Alert Banner ────────────────────────────────────────
function showAlert(message) {
  const banner = document.getElementById('alertBanner')
  document.getElementById('alertMsg').textContent = message
  banner.style.display = 'block'
  setTimeout(() => { banner.style.display = 'none' }, 6000)

  // Vibrate if supported
  if (navigator.vibrate) navigator.vibrate([200, 100, 200])
}

// ── Stats ───────────────────────────────────────────────
async function loadStats() {
  try {
    const res  = await fetch(`${API_BASE}/stats`)
    const data = await res.json()
    state.stats = data

    const ids = {
      'statTotal':  data.total_detections || 0,
      'statAlerts': data.total_alerts     || 0,
      'statAvg':    data.avg_crowd        || 0,
      'statPeak':   data.peak_crowd       || 0,
    }
    Object.entries(ids).forEach(([id, val]) => {
      const el = document.getElementById(id)
      if (el) el.textContent = val
    })
  } catch (e) { console.log('Stats failed') }
}

// ── History ─────────────────────────────────────────────
async function loadHistory() {
  try {
    const res  = await fetch(`${API_BASE}/history`)
    const data = await res.json()
    state.history = data

    const container = document.getElementById('historyList')
    if (!container) return

    if (!data.length) {
      container.innerHTML = '<p style="color:#64748b;text-align:center;padding:20px;">No detections yet</p>'
      return
    }

    const badgeClass = { SAFE: 'badge-safe', WARNING: 'badge-warning', DANGER: 'badge-danger' }

    container.innerHTML = data.slice(0, 20).map(d => `
      <div class="history-item">
        <div>
          <div class="history-time">${d.timestamp}</div>
          <div class="history-count">${d.person_count} people</div>
        </div>
        <span class="history-badge ${badgeClass[d.risk_level]}">${d.risk_level}</span>
      </div>
    `).join('')
  } catch (e) { console.log('History failed') }
}

// ── Camera ──────────────────────────────────────────────
async function startCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment', width: 640, height: 480 }
    })
    state.stream = stream

    const video = document.getElementById('cameraFeed')
    video.srcObject = stream
    await video.play()

    state.cameraActive = true
    document.getElementById('startCamBtn').style.display = 'none'
    document.getElementById('stopCamBtn').style.display  = 'flex'
    document.querySelector('.rec-indicator').style.display = 'flex'
    document.getElementById('cameraOverlay').style.display = 'block'

    // Connect WebSocket
    const wsUrl = API_BASE.replace('http', 'ws') + '/ws/webcam'
    state.ws = new WebSocket(wsUrl)

    state.ws.onopen = () => {
      const canvas = document.createElement('canvas')
      canvas.width  = 640
      canvas.height = 480
      const ctx = canvas.getContext('2d')

      state.frameInterval = setInterval(() => {
        if (!state.cameraActive) return
        ctx.drawImage(video, 0, 0, 640, 480)
        const frame = canvas.toDataURL('image/jpeg', 0.6).split(',')[1]
        if (state.ws?.readyState === WebSocket.OPEN) {
          state.ws.send(JSON.stringify({ frame }))
        }
      }, 800)
    }

    state.ws.onmessage = (e) => {
      const data = JSON.parse(e.data)

      // Draw result on canvas
      const resultCanvas = document.getElementById('resultCanvas')
      const ctx = resultCanvas.getContext('2d')
      const img = new Image()
      img.onload = () => {
        resultCanvas.width  = resultCanvas.offsetWidth
        resultCanvas.height = resultCanvas.offsetHeight
        ctx.drawImage(img, 0, 0, resultCanvas.width, resultCanvas.height)
      }
      img.src = 'data:image/jpeg;base64,' + data.frame

      // Update overlay
      document.getElementById('overlayCount').textContent = `👥 ${data.person_count}`
      const riskColors = { SAFE: '#00ff88', WARNING: '#ff9500', DANGER: '#ff3b5c' }
      document.getElementById('overlayRisk').style.color   = riskColors[data.risk_level]
      document.getElementById('overlayRisk').textContent   = data.risk_level

      // Update main risk display
      updateRisk(data.person_count, data.risk_level, data.message, data.zones)
      loadStats()
    }

    state.ws.onerror = () => stopCamera()

  } catch (e) {
    alert('Camera permission denied. Please allow camera access and try again.')
  }
}

function stopCamera() {
  state.cameraActive = false
  if (state.frameInterval) clearInterval(state.frameInterval)
  if (state.ws) state.ws.close()
  if (state.stream) state.stream.getTracks().forEach(t => t.stop())

  document.getElementById('startCamBtn').style.display = 'flex'
  document.getElementById('stopCamBtn').style.display  = 'none'
  document.querySelector('.rec-indicator').style.display = 'none'
  document.getElementById('cameraOverlay').style.display = 'none'

  const ctx = document.getElementById('resultCanvas').getContext('2d')
  ctx.clearRect(0, 0, 9999, 9999)
}

// ── Image Analysis ──────────────────────────────────────
function triggerImageUpload() {
  document.getElementById('imageInput').click()
}

async function analyzeImage(input) {
  const file = input.files[0]
  if (!file) return

  document.getElementById('imageResult').style.display = 'none'
  document.getElementById('imageUploadBtn').disabled   = true
  document.getElementById('imageUploadBtn').innerHTML  = '<div class="spinner"></div> Analyzing...'

  const form = new FormData()
  form.append('file', file)

  try {
    const res  = await fetch(`${API_BASE}/analyze/image`, { method: 'POST', body: form })
    const data = await res.json()

    const risk    = data.risk_level
    const resultEl = document.getElementById('imageResult')
    resultEl.className = `result-box result-${risk.toLowerCase()}`
    resultEl.style.display = 'block'

    document.getElementById('imageRisk').textContent    = risk
    document.getElementById('imageMsg').textContent     = data.message
    document.getElementById('imageCount').textContent   = data.person_count
    document.getElementById('imageDensity').textContent = data.density_score

    if (data.annotated_image) {
      const img = document.getElementById('annotatedImg')
      img.src = 'data:image/jpeg;base64,' + data.annotated_image
      img.style.display = 'block'
    }

    updateRisk(data.person_count, risk, data.message, data.zones)
    loadStats()
    loadHistory()
  } catch (e) {
    alert('Analysis failed. Make sure you are connected.')
  }

  document.getElementById('imageUploadBtn').disabled  = false
  document.getElementById('imageUploadBtn').innerHTML = '🔍 Analyze Image'
}

// ── Video Analysis ──────────────────────────────────────
function triggerVideoUpload() {
  document.getElementById('videoInput').click()
}

async function analyzeVideo(input) {
  const file = input.files[0]
  if (!file) return

  document.getElementById('videoResult').style.display  = 'none'
  document.getElementById('videoUploadBtn').disabled    = true
  document.getElementById('videoProgressWrap').style.display = 'block'

  let progress = 0
  const interval = setInterval(() => {
    progress = Math.min(progress + 1.5, 90)
    document.getElementById('videoProgress').style.width     = progress + '%'
    document.getElementById('videoProgressPct').textContent  = Math.round(progress) + '%'
  }, 400)

  const form = new FormData()
  form.append('file', file)

  try {
    const res  = await fetch(`${API_BASE}/analyze/video`, { method: 'POST', body: form })
    const data = await res.json()

    clearInterval(interval)
    document.getElementById('videoProgress').style.width    = '100%'
    document.getElementById('videoProgressPct').textContent = '100%'

    const risk    = data.overall_risk
    const resultEl = document.getElementById('videoResult')
    resultEl.className    = `result-box result-${risk.toLowerCase()}`
    resultEl.style.display = 'block'

    document.getElementById('videoRisk').textContent    = `Overall: ${risk}`
    document.getElementById('videoFrames').textContent  = data.frames_analyzed
    document.getElementById('videoAvg').textContent     = data.avg_person_count
    document.getElementById('videoPeak').textContent    = data.max_person_count
    document.getElementById('videoDanger').textContent  = data.danger_frames

    updateRisk(data.max_person_count, risk, `Video: ${data.frames_analyzed} frames analyzed`, [])
    loadStats()
    loadHistory()
  } catch (e) {
    clearInterval(interval)
    alert('Video analysis failed.')
  }

  document.getElementById('videoUploadBtn').disabled         = false
  document.getElementById('videoUploadBtn').innerHTML        = '🎬 Analyze Video'
  document.getElementById('videoProgressWrap').style.display = 'none'
}

// ── Generate Report ─────────────────────────────────────
async function generateReport() {
  const btn = document.getElementById('reportBtn')
  btn.disabled   = true
  btn.textContent = '⏳ Generating...'

  try {
    const res  = await fetch(`${API_BASE}/reports/generate`, { method: 'POST' })
    const data = await res.json()
    alert(`✅ Report generated: ${data.filename}`)
  } catch (e) {
    alert('Report generation failed.')
  }

  btn.disabled    = false
  btn.textContent = '📄 Generate Report'
}
