import { useState, useEffect, useCallback } from 'react'
import { api } from '../utils/api'

export function useStats(pollInterval = 12000) {
  const [stats, setStats] = useState({
    total_detections: 0, total_alerts: 0, avg_crowd: 0, peak_crowd: 0,
    risk_distribution: { SAFE: 0, WARNING: 0, DANGER: 0 },
    recent_counts: [], recent_timestamps: []
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const refresh = useCallback(async () => {
    try {
      const data = await api.getStats()
      setStats(data)
      setError(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, pollInterval)
    return () => clearInterval(id)
  }, [refresh, pollInterval])

  return { stats, loading, error, refresh }
}
