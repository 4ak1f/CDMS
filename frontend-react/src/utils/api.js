const BASE = ''

async function request(path, options = {}) {
  const token = localStorage.getItem('cdms_token')
  try {
    const res = await fetch(BASE + path, {
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers || {}),
      },
      ...options,
    })
    if (res.status === 401) {
      localStorage.removeItem('cdms_token')
      window.location.href = '/login'
      throw new Error('Session expired')
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return res.json()
  } catch(e) {
    console.error(`API error ${path}:`, e.message)
    throw e
  }
}

export const api = {
  getStats:       () => request('/stats'),
  getSystemStats: () => request('/system/stats'),
  getHistory:     () => request('/history'),
  getIncidents:   () => request('/incidents'),
  getAlerts:      () => request('/alerts'),
  getCalibration: () => request('/calibration'),
  getFeedback:    () => request('/feedback'),
  getThresholds:  () => request('/thresholds'),
  getZones:       () => request('/zones/config'),
  updateThresholds: (body) => request('/thresholds', { method: 'POST', body: JSON.stringify(body) }),
  submitFeedback:   (body) => request('/feedback',   { method: 'POST', body: JSON.stringify(body) }),
  clearLogs:        ()     => request('/logs/clear', { method: 'POST' }),
  archiveLogs:      ()     => request('/logs/archive',{ method: 'POST' }),
  analyzeImage: (file, mode = 'auto') => {
    const token = localStorage.getItem('cdms_token')
    const form = new FormData()
    form.append('file', file)
    return fetch(`${BASE}/analyze/image?mode=${mode}`, {
      method: 'POST', body: form,
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    }).then(r => r.json())
  },
  analyzeVideo: (file, mode = 'auto') => {
    const token = localStorage.getItem('cdms_token')
    const form = new FormData()
    form.append('file', file)
    return fetch(`${BASE}/analyze/video?mode=${mode}`, {
      method: 'POST', body: form,
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    }).then(r => r.json())
  },
  setupAnomalies:    () => request('/anomaly/setup',   { method: 'POST' }),
  getAnomalies:      (limit = 10) => request(`/anomaly/recent?limit=${limit}`),
  getAnomalyHistory: () => request('/anomaly/history'),
}

export default api
