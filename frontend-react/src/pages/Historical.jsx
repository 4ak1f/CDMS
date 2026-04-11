import { useState, useEffect } from 'react'
import PageTransition from '../components/PageTransition'
import StatCard from '../components/StatCard'
import { api } from '../utils/api'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

const PAGE_SIZE = 20

function CloudStats() {
  const [stats,   setStats]   = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/cloud/stats')
      .then(r => r.json())
      .then(d => { setStats(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  if (loading) return <div className="skeleton" style={{ height: 60 }} />
  if (!stats?.connected) return (
    <div style={{ fontSize: 13, color: 'var(--text-muted)', textAlign: 'center', padding: 20 }}>
      Cloud not connected — configure Supabase in Settings
    </div>
  )

  const s = stats.stats || {}
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
      {[
        { label: 'Total Cloud Records', value: s.total       || 0,   color: 'var(--accent-cyan)'   },
        { label: 'Cloud Avg Count',     value: s.avg_count   || 0,   color: 'var(--accent-purple)' },
        { label: 'Cloud Peak',          value: s.peak_count  || 0,   color: 'var(--accent-red)'    },
        { label: 'Latest Record',       value: s.latest_timestamp ? new Date(s.latest_timestamp).toLocaleDateString() : '—', color: 'var(--accent-green)', isText: true },
      ].map((item, i) => (
        <div key={i} style={{ padding: '14px 16px', background: 'var(--bg-glass)', borderRadius: 12, border: '1px solid var(--border-glass)' }}>
          <div className="card-label" style={{ marginBottom: 8 }}>{item.label}</div>
          <div style={{
            fontSize: item.isText ? 14 : 24,
            fontWeight: 700,
            color: item.color,
            fontFamily: item.isText ? 'Inter, sans-serif' : "'Space Grotesk', sans-serif",
          }}>
            {item.value}
          </div>
        </div>
      ))}
    </div>
  )
}

export default function Historical() {
  const [history,     setHist]      = useState([])
  const [page,        setPage]      = useState(0)
  const [range,       setRange]     = useState('24h')
  const [loading,     setLoad]      = useState(true)
  const [error,       setErr]       = useState(null)
  const [archiving,   setArchiving] = useState(false)
  const [lastArchive, setLastArchive] = useState(null)

  const loadHistory = async () => {
    try {
      setLoad(true)
      const d = await api.getHistory()
      setHist(Array.isArray(d) ? d : [])
      setErr(null)
    } catch (e) {
      setErr(e.message)
    } finally {
      setLoad(false)
    }
  }

  useEffect(() => { loadHistory() }, [range])

  const handleArchiveAndReset = async () => {
    if (!window.confirm('Archive all local detections to cloud and reset local history? This cannot be undone.')) return
    setArchiving(true)
    try {
      const res = await fetch('/cloud/archive', { method: 'POST' }).then(r => r.json())
      if (res.status === 'ok') {
        setLastArchive(new Date().toLocaleString())
        await loadHistory()
        alert(`✅ Archived ${res.archived} records to Supabase cloud. Local history reset.`)
      } else {
        alert(`⚠️ Archive failed: ${res.error}`)
      }
    } catch {
      alert('Archive failed — check cloud connection in Settings')
    } finally {
      setArchiving(false)
    }
  }

  const counts     = history.map(r => r.person_count || 0)
  const avg        = counts.length ? Math.round(counts.reduce((a, b) => a + b, 0) / counts.length) : 0
  const peak       = counts.length ? Math.max(...counts) : 0
  const chartData  = history.slice(0, 100).map((r, i) => ({ i, v: r.person_count || 0 }))
  const paged      = history.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)
  const totalPages = Math.ceil(history.length / PAGE_SIZE)

  const exportCSV = () => {
    const rows = [
      ['Timestamp', 'Count', 'Density', 'Risk', 'Message'],
      ...history.map(r => [r.timestamp, r.person_count, r.density_score, r.risk_level, r.message]),
    ]
    const csv = rows.map(r => r.map(v => `"${v}"`).join(',')).join('\n')
    const a = document.createElement('a')
    a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
    a.download = 'history.csv'
    a.click()
  }

  if (error) return (
    <PageTransition>
      <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
        {error} <button onClick={loadHistory} style={{ marginLeft: 12, color: 'var(--accent-purple)', cursor: 'pointer', background: 'none', border: 'none' }}>Retry</button>
      </div>
    </PageTransition>
  )

  return (
    <PageTransition>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        {/* ── Controls row ── */}
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          {['24h', '7d', '30d'].map(r => (
            <button
              key={r}
              onClick={() => setRange(r)}
              style={{
                padding: '6px 16px', borderRadius: 8, border: '1px solid',
                borderColor: range === r ? 'var(--accent-purple)' : 'var(--border-glass)',
                background:  range === r ? 'rgba(99,102,241,0.12)' : 'var(--bg-glass)',
                color:       range === r ? 'var(--accent-purple)'   : 'var(--text-secondary)',
                fontSize: 12, fontWeight: 600, cursor: 'pointer',
              }}
            >
              {r}
            </button>
          ))}
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <button
              onClick={exportCSV}
              className="cdms-btn"
              style={{ color: 'var(--accent-cyan)', fontSize: 12 }}
            >
              Export CSV
            </button>
            <button
              className="cdms-btn cdms-btn-danger"
              onClick={handleArchiveAndReset}
              disabled={archiving}
              style={{ opacity: archiving ? 0.6 : 1, fontSize: 12 }}
            >
              {archiving ? '⏳ Archiving...' : '☁️ Archive & Reset'}
            </button>
          </div>
        </div>
        {lastArchive && (
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: -12 }}>
            Last archived: {lastArchive}
          </div>
        )}

        {/* ── Stat cards ── */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
          <StatCard label="Total Detections" value={history.length} color="var(--accent-cyan)"   />
          <StatCard label="Average Crowd"    value={avg}            color="var(--accent-purple)"  />
          <StatCard label="Peak Count"       value={peak}           color="var(--accent-red)"     />
          <StatCard label="Showing"          value={history.length} sub="detections" color="var(--accent-violet)" />
        </div>

        {/* ── Chart ── */}
        <div className="glass-card" style={{ padding: 20 }}>
          <div className="card-label">Crowd Count Over Time</div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData}>
              <XAxis dataKey="i" hide />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} width={28} />
              <Tooltip contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border-glass)', borderRadius: 8, fontSize: 12 }} />
              <Line type="monotone" dataKey="v" stroke="var(--accent-cyan)" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* ── Table ── */}
        <div className="glass-card" style={{ padding: 20 }}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr>{['Timestamp', 'Count', 'Density', 'Risk', 'Message'].map(h => (
                  <th key={h} style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, borderBottom: '1px solid var(--border-glass)', whiteSpace: 'nowrap' }}>{h}</th>
                ))}</tr>
              </thead>
              <tbody>
                {loading ? [...Array(5)].map((_, i) => (
                  <tr key={i}><td colSpan={5} style={{ padding: 12 }}><div style={{ height: 28, borderRadius: 6, background: 'var(--bg-glass)' }} /></td></tr>
                )) : paged.map((row, i) => {
                  const color = row.risk_level === 'DANGER' ? 'var(--accent-red)' : row.risk_level === 'WARNING' ? 'var(--accent-amber)' : 'var(--accent-green)'
                  return (
                    <tr key={i} style={{ borderBottom: '1px solid var(--border-glass)' }}>
                      <td style={{ padding: '8px 12px', color: 'var(--text-muted)' }}>{row.timestamp}</td>
                      <td style={{ padding: '8px 12px', color: 'var(--text-primary)', fontWeight: 700 }}>{row.person_count}</td>
                      <td style={{ padding: '8px 12px', color: 'var(--text-secondary)' }}>{row.density_score}</td>
                      <td style={{ padding: '8px 12px' }}><span style={{ padding: '2px 8px', borderRadius: 100, background: color + '22', color, fontSize: 10, fontWeight: 700 }}>{row.risk_level}</span></td>
                      <td style={{ padding: '8px 12px', color: 'var(--text-secondary)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{row.message}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 16, justifyContent: 'center' }}>
            <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0} style={{ padding: '6px 14px', borderRadius: 8, border: '1px solid var(--border-glass)', background: 'var(--bg-glass)', color: 'var(--text-secondary)', fontSize: 12, cursor: 'pointer', opacity: page === 0 ? 0.4 : 1 }}>← Prev</button>
            <span style={{ padding: '6px 14px', color: 'var(--text-muted)', fontSize: 12 }}>Page {page + 1} / {totalPages || 1}</span>
            <button onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1} style={{ padding: '6px 14px', borderRadius: 8, border: '1px solid var(--border-glass)', background: 'var(--bg-glass)', color: 'var(--text-secondary)', fontSize: 12, cursor: 'pointer', opacity: page >= totalPages - 1 ? 0.4 : 1 }}>Next →</button>
          </div>
        </div>

        {/* ── Cloud stats ── */}
        <div className="glass-card" style={{ padding: 20 }}>
          <div className="card-label">Cloud Database (Supabase)</div>
          <CloudStats />
        </div>
      </div>
    </PageTransition>
  )
}
