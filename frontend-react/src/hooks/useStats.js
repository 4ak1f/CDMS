import { useState, useEffect, useCallback } from 'react'
import { api } from '../utils/api'

export function useStats() {
  const [stats, setStats] = useState({
    total_detections: 0,
    total_alerts: 0,
    avg_crowd: 0,
    peak_crowd: 0,
    risk_distribution: { SAFE: 0, WARNING: 0, DANGER: 0 },
    recent_counts: [],
    recent_timestamps: []
  })

  const refresh = useCallback(async () => {
    try {
      const data = await api.getStats()
      setStats(data)
    } catch (e) {
      console.log('Stats fetch failed')
    }
  }, [])

  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, 8000)
    return () => clearInterval(interval)
  }, [refresh])

  return { stats, refresh }
}