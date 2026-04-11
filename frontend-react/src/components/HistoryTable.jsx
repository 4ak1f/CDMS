import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { api } from '../utils/api'

const BADGE_COLOR = {
  SAFE:    'var(--accent-green)',
  WARNING: 'var(--accent-amber)',
  DANGER:  'var(--accent-red)',
}

export default function HistoryTable() {
  const [history,    setHistory]    = useState([])
  const [generating, setGenerating] = useState(false)

  const load = async () => {
    try {
      const hist = await api.getHistory()
      setHistory(Array.isArray(hist) ? hist : [])
    } catch {}
  }

  useEffect(() => { load() }, [])

  const generateReport = async () => {
    setGenerating(true)
    try {
      await fetch('/reports/generate', { method: 'POST' })
      await load()
    } catch {}
    setGenerating(false)
  }

  return (
    <div className="glass-card">
      <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border-glass)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span className="card-label" style={{ marginBottom: 0 }}>Detection History</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <motion.button
            whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
            onClick={generateReport} disabled={generating}
            style={{ fontSize: 11, background: 'rgba(99,102,241,0.1)', color: 'var(--accent-purple)', border: '1px solid rgba(99,102,241,0.2)', borderRadius: 8, padding: '5px 12px', cursor: generating ? 'not-allowed' : 'pointer', opacity: generating ? 0.4 : 1 }}
          >
            {generating ? '⏳ Generating...' : '📄 Generate Report'}
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
            onClick={load}
            style={{ fontSize: 11, color: 'var(--text-muted)', border: '1px solid var(--border-glass)', borderRadius: 8, padding: '5px 12px', background: 'var(--bg-glass)', cursor: 'pointer' }}
          >
            ↻ Refresh
          </motion.button>
        </div>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-glass)' }}>
              {['Timestamp', 'People', 'Density', 'Risk Level', 'Message'].map(h => (
                <th key={h} style={{ textAlign: 'left', padding: '10px 20px', color: 'var(--text-muted)', fontWeight: 600, fontSize: 10, textTransform: 'uppercase', letterSpacing: '1.5px' }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {history.length === 0 ? (
              <tr>
                <td colSpan="5" style={{ textAlign: 'center', padding: '48px 20px', color: 'var(--text-muted)', fontSize: 13 }}>
                  No detections yet — run an analysis to see results
                </td>
              </tr>
            ) : history.map((row, i) => {
              const color = BADGE_COLOR[row.risk_level] || 'var(--text-muted)'
              return (
                <motion.tr
                  key={i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.03 }}
                  style={{ borderBottom: '1px solid var(--border-glass)' }}
                >
                  <td style={{ padding: '10px 20px', color: 'var(--text-muted)', fontFamily: 'monospace', fontSize: 11 }}>{row.timestamp}</td>
                  <td style={{ padding: '10px 20px', fontWeight: 700, color: 'var(--text-primary)' }}>{row.person_count}</td>
                  <td style={{ padding: '10px 20px', color: 'var(--text-secondary)' }}>{row.density_score}</td>
                  <td style={{ padding: '10px 20px' }}>
                    <span style={{ padding: '3px 10px', borderRadius: 100, background: color + '22', color, fontSize: 10, fontWeight: 700 }}>
                      {row.risk_level}
                    </span>
                  </td>
                  <td style={{ padding: '10px 20px', color: 'var(--text-muted)', fontSize: 11 }}>{row.message}</td>
                </motion.tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
