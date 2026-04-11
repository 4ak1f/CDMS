import { useState, useEffect } from 'react'
import PageTransition from '../components/PageTransition'
import StatCard from '../components/StatCard'
import { api } from '../utils/api'

export default function IncidentLogs() {
  const [incidents, setInc]     = useState([])
  const [filter,    setFilter]  = useState('ALL')
  const [search,    setSearch]  = useState('')
  const [expanded,  setExpanded]= useState(null)
  const [loading,   setLoading] = useState(true)
  const [error,     setError]   = useState(null)

  const load = async () => {
    try {
      const data = await api.getIncidents()
      setInc(Array.isArray(data) ? data : [])
      setError(null)
    } catch (e) { setError(e.message) } finally { setLoading(false) }
  }
  useEffect(() => { load(); const id = setInterval(load, 30000); return () => clearInterval(id) }, [])

  const filtered = incidents.filter(inc => {
    if (filter !== 'ALL' && inc.risk_level !== filter) return false
    if (search && !inc.message?.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const lastIncident = incidents[0]?.timestamp || '—'
  const warnCount    = incidents.filter(i => i.risk_level === 'WARNING').length
  const dangerCount  = incidents.filter(i => i.risk_level === 'DANGER' || i.risk_level === 'OVERCROWDED').length

  const exportCSV = () => {
    const rows = [['Timestamp','Count','Density','Risk','Message'], ...filtered.map(r => [r.timestamp, r.person_count, r.density_score, r.risk_level, r.message])]
    const csv = rows.map(r => r.map(v => `"${v}"`).join(',')).join('\n')
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' })); a.download = 'incidents.csv'; a.click()
  }
  const clearAll = async () => { if (!confirm('Clear all logs?')) return; await api.clearLogs(); load() }

  if (error) return (
    <PageTransition>
      <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
        {error} <button onClick={load} style={{ marginLeft: 12, color: 'var(--accent-purple)', cursor: 'pointer', background: 'none', border: 'none' }}>Retry</button>
      </div>
    </PageTransition>
  )

  return (
    <PageTransition>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
          <StatCard label="Total Incidents" value={incidents.length} color="var(--accent-cyan)"  />
          <StatCard label="Warnings"        value={warnCount}        color="var(--accent-amber)" />
          <StatCard label="Dangers"         value={dangerCount}      color="var(--accent-red)"   />
          <div className="glass-card" style={{ padding: '20px 22px' }}>
            <div className="card-label">Last Incident</div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', wordBreak: 'break-all' }}>{lastIncident}</div>
          </div>
        </div>

        <div className="glass-card" style={{ padding: 20 }}>
          <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
            {['ALL','WARNING','DANGER'].map(f => (
              <button key={f} onClick={() => setFilter(f)} style={{ padding: '6px 16px', borderRadius: 8, border: '1px solid', borderColor: filter === f ? 'var(--accent-purple)' : 'var(--border-glass)', background: filter === f ? 'rgba(99,102,241,0.12)' : 'var(--bg-glass)', color: filter === f ? 'var(--accent-purple)' : 'var(--text-secondary)', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
                {f}
              </button>
            ))}
            <input
              placeholder="Search messages..."
              value={search} onChange={e => setSearch(e.target.value)}
              style={{ flex: 1, minWidth: 160, padding: '6px 14px', borderRadius: 8, border: '1px solid var(--border-glass)', background: 'var(--bg-glass)', color: 'var(--text-primary)', fontSize: 12, outline: 'none' }}
            />
            <button onClick={exportCSV} style={{ padding: '6px 14px', borderRadius: 8, border: '1px solid var(--border-glass)', background: 'var(--bg-glass)', color: 'var(--accent-cyan)', fontSize: 12, cursor: 'pointer' }}>Export CSV</button>
            <button onClick={clearAll}  style={{ padding: '6px 14px', borderRadius: 8, border: '1px solid rgba(255,59,92,0.3)', background: 'var(--bg-glass)', color: 'var(--accent-red)', fontSize: 12, cursor: 'pointer' }}>Clear Logs</button>
          </div>

          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {[...Array(4)].map((_, i) => <div key={i} style={{ height: 48, borderRadius: 10, background: 'var(--bg-glass)' }} />)}
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {filtered.map((inc, i) => {
                const color = inc.risk_level === 'DANGER' || inc.risk_level === 'OVERCROWDED' ? 'var(--accent-red)' : 'var(--accent-amber)'
                return (
                  <div key={i}>
                    <div onClick={() => setExpanded(expanded === i ? null : i)} style={{ display: 'grid', gridTemplateColumns: '1.5fr 60px 80px 80px 2fr', gap: 12, alignItems: 'center', padding: '10px 14px', borderRadius: 10, background: 'var(--bg-glass)', borderLeft: `3px solid ${color}`, cursor: 'pointer', fontSize: 12 }}>
                      <span style={{ color: 'var(--text-muted)' }}>{inc.timestamp}</span>
                      <span style={{ color: 'var(--text-primary)', fontWeight: 700 }}>{inc.person_count}</span>
                      <span style={{ color: 'var(--text-secondary)' }}>{inc.density_score}</span>
                      <span style={{ color, fontWeight: 700 }}>{inc.risk_level}</span>
                      <span style={{ color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{inc.message}</span>
                    </div>
                    {expanded === i && (
                      <div style={{ padding: '12px 14px', borderRadius: '0 0 10px 10px', background: 'rgba(99,102,241,0.06)', border: '1px solid var(--border-glass)', borderTop: 'none', fontSize: 12, color: 'var(--text-secondary)', marginTop: -4 }}>
                        <strong style={{ color: 'var(--text-primary)' }}>Full message:</strong> {inc.message}<br />
                        <strong style={{ color: 'var(--text-primary)' }}>Density:</strong> {inc.density_score} &nbsp; <strong style={{ color: 'var(--text-primary)' }}>Count:</strong> {inc.person_count}
                      </div>
                    )}
                  </div>
                )
              })}
              {filtered.length === 0 && <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>No incidents found</div>}
            </div>
          )}
        </div>
      </div>
    </PageTransition>
  )
}
