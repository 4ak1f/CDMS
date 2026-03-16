import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { api } from '../utils/api'

const BADGE = {
  SAFE:    'bg-safe/10    text-safe    border border-safe/20',
  WARNING: 'bg-warning/10 text-warning border border-warning/20',
  DANGER:  'bg-danger/10  text-danger  border border-danger/20',
}

export default function HistoryTable() {
  const [history,  setHistory]  = useState([])
  const [reports,  setReports]  = useState([])
  const [generating, setGenerating] = useState(false)

  const load = async () => {
    try {
      const [hist, reps] = await Promise.all([api.getHistory(), api.getReports()])
      setHistory(hist)
      setReports(reps.reports || [])
    } catch {}
  }

  useEffect(() => { load() }, [])

  const generateReport = async () => {
    setGenerating(true)
    try {
      await api.generateReport()
      await load()
    } catch {}
    setGenerating(false)
  }

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">📋 Detection History</span>
        <div className="flex items-center gap-2">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={generateReport}
            disabled={generating}
            className="text-xs bg-accent/10 text-accent border border-accent/20 rounded-lg px-3 py-1.5 hover:bg-accent/20 transition-colors disabled:opacity-40"
          >
            {generating ? '⏳ Generating...' : '📄 Generate Report'}
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={load}
            className="text-xs text-slate-500 hover:text-accent border border-border rounded-lg px-3 py-1.5 transition-colors"
          >
            ↻ Refresh
          </motion.button>
        </div>
      </div>

      {reports.length > 0 && (
  <div className="px-5 py-3 border-b border-border bg-accent/3">
    <div className="text-xs text-slate-500 mb-2 font-semibold uppercase tracking-wider">📁 Generated Reports</div>
    <div className="flex flex-wrap gap-2">
      {reports.map(r => (
        <a>
          key={r}
          href={`/reports/download/${r}`}
          target="_blank"
          rel="noreferrer"
          className="text-xs bg-surface border border-border rounded-lg px-3 py-1.5 text-accent hover:border-accent/40 transition-colors"
          📄 {r}
        </a>
      ))}
    </div>
  </div>
)}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              {['Timestamp', 'People', 'Density', 'Risk Level', 'Message'].map(h => (
                <th key={h} className="text-left px-5 py-3 text-slate-500 font-semibold text-xs uppercase tracking-wider">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {history.length === 0 ? (
              <tr>
                <td colSpan="5" className="text-center py-12 text-slate-600">
                  No detections yet — run an analysis to see results
                </td>
              </tr>
            ) : history.map((row, i) => (
              <motion.tr
                key={i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x:  0  }}
                transition={{ delay: i * 0.03 }}
                className="border-b border-border/50 hover:bg-white/2 transition-colors"
              >
                <td className="px-5 py-3 text-slate-500 font-mono text-xs">{row.timestamp}</td>
                <td className="px-5 py-3 font-bold text-white">{row.person_count}</td>
                <td className="px-5 py-3 text-slate-400">{row.density_score}</td>
                <td className="px-5 py-3">
                  <span className={`px-3 py-1 rounded-full text-xs font-bold ${BADGE[row.risk_level]}`}>
                    {row.risk_level}
                  </span>
                </td>
                <td className="px-5 py-3 text-slate-500 text-xs">{row.message}</td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}