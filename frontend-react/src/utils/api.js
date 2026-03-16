const BASE = ''

export const api = {
  analyzeImage: async (file) => {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${BASE}/analyze/image`, { method: 'POST', body: form })
    return res.json()
  },

  analyzeVideo: async (file) => {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${BASE}/analyze/video`, { method: 'POST', body: form })
    return res.json()
  },

  getStats: async () => {
    const res = await fetch(`${BASE}/stats`)
    return res.json()
  },

  getHistory: async () => {
    const res = await fetch(`${BASE}/history`)
    return res.json()
  },

  generateReport: async () => {
    const res = await fetch(`${BASE}/reports/generate`, { method: 'POST' })
    return res.json()
  },

  getReports: async () => {
    const res = await fetch(`${BASE}/reports`)
    return res.json()
  }
}