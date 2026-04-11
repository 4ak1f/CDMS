import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertTriangle, TrendingUp, TrendingDown, Minus, Activity } from 'lucide-react'

const SEVERITY_COLOR = {
  critical: 'var(--accent-red)',
  high:     'var(--accent-amber)',
  medium:   'var(--accent-cyan)',
  low:      'var(--accent-green)',
}

const SEVERITY_BG = {
  critical: 'rgba(239,68,68,0.08)',
  high:     'rgba(245,158,11,0.08)',
  medium:   'rgba(6,182,212,0.08)',
  low:      'rgba(34,197,94,0.08)',
}

function FlowIcon({ direction }) {
  if (direction === 'increasing') return <TrendingUp size={14} color="var(--accent-red)" />
  if (direction === 'decreasing') return <TrendingDown size={14} color="var(--accent-cyan)" />
  return <Minus size={14} color="var(--accent-green)" />
}

export default function AnomalyPanel({ latestAnomaly, latestFlow }) {
  const [history, setHistory]   = useState([])
  const [stats,   setStats]     = useState(null)
  const [loading, setLoading]   = useState(false)

  useEffect(() => {
    fetchHistory()
    const id = setInterval(fetchHistory, 15000)
    return () => clearInterval(id)
  }, [])

  // Prepend live anomaly when it arrives
  useEffect(() => {
    if (!latestAnomaly) return
    setHistory(prev => [
      { ...latestAnomaly, timestamp: new Date().toISOString(), id: Date.now() },
      ...prev.slice(0, 9),
    ])
  }, [latestAnomaly])

  async function fetchHistory() {
    setLoading(true)
    try {
      const res = await fetch('/anomaly/history')
      if (!res.ok) return
      const data = await res.json()
      setStats(data.stats)
      if (data.recent?.length) setHistory(data.recent)
    } catch (_) {
      // Supabase might not be configured — fail silently
    } finally {
      setLoading(false)
    }
  }

  const flow = latestFlow || {}

  return (
    <div className="glass-card" style={{ padding: '16px 18px', height: '100%', display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Activity size={15} color="var(--accent-violet)" />
          <span className="card-label" style={{ margin: 0 }}>Anomaly Detection</span>
        </div>
        {loading && (
          <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>syncing…</span>
        )}
      </div>

      {/* Flow state */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10,
                    padding: '8px 12px', borderRadius: 8,
                    background: 'var(--bg-glass)', border: '1px solid var(--border-subtle)' }}>
        <FlowIcon direction={flow.direction} />
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', textTransform: 'capitalize' }}>
            {flow.direction || 'stable'} crowd
            {flow.rate_per_min !== undefined && (
              <span style={{ marginLeft: 6, color: 'var(--text-muted)' }}>
                {flow.rate_per_min > 0 ? '+' : ''}{flow.rate_per_min} /min
              </span>
            )}
          </div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>
            trend: {flow.trend || '—'} · window: {flow.window_size ?? '—'} readings
          </div>
        </div>
      </div>

      {/* Stats row */}
      {stats && (
        <div style={{ display: 'flex', gap: 8 }}>
          {[
            { label: 'Total', value: stats.total },
            { label: 'Critical', value: stats.by_severity?.critical || 0, color: 'var(--accent-red)' },
            { label: 'High',     value: stats.by_severity?.high     || 0, color: 'var(--accent-amber)' },
          ].map(({ label, value, color }) => (
            <div key={label} style={{ flex: 1, textAlign: 'center', padding: '6px 4px',
                                      background: 'var(--bg-glass)', borderRadius: 6,
                                      border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: color || 'var(--text-primary)' }}>{value}</div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Anomaly feed */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
        <AnimatePresence initial={false}>
          {history.length === 0 ? (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: 12,
                          marginTop: 12, padding: '12px 0' }}>
              No anomalies detected
            </div>
          ) : history.map((a, i) => {
            const sev   = a.severity || 'medium'
            const color = SEVERITY_COLOR[sev] || 'var(--accent-cyan)'
            const bg    = SEVERITY_BG[sev]    || 'rgba(6,182,212,0.08)'
            return (
              <motion.div
                key={a.id || a.timestamp || i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                transition={{ duration: 0.25 }}
                style={{ padding: '8px 10px', borderRadius: 8,
                         background: bg, border: `1px solid ${color}33`,
                         display: 'flex', flexDirection: 'column', gap: 3 }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <AlertTriangle size={11} color={color} />
                  <span style={{ fontSize: 10, fontWeight: 700, color,
                                 textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    {sev}
                  </span>
                  <span style={{ fontSize: 10, color: 'var(--text-muted)', marginLeft: 'auto' }}>
                    {a.timestamp ? new Date(a.timestamp).toLocaleTimeString() : ''}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                  {a.description || a.type}
                </div>
                {a.person_count !== undefined && (
                  <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                    Count: {a.person_count}
                    {a.z_score !== undefined && ` · Z: ${a.z_score}`}
                    {a.rate_of_change !== undefined && ` · Rate: ${a.rate_of_change > 0 ? '+' : ''}${a.rate_of_change}/min`}
                  </div>
                )}
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>
    </div>
  )
}
