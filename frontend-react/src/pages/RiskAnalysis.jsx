import { useState, useEffect } from 'react'
import PageTransition from '../components/PageTransition'
import StatCard from '../components/StatCard'
import RiskGauge from '../components/RiskGauge'
import { api } from '../utils/api'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

export default function RiskAnalysis() {
  const [stats,     setStats]   = useState(null)
  const [incidents, setInc]     = useState([])
  const [warning,   setW]       = useState(50)
  const [danger,    setD]       = useState(100)
  const [saved,     setSaved]   = useState(false)
  const [error,     setError]   = useState(null)

  const load = async () => {
    try {
      const [s, i, t] = await Promise.all([api.getStats(), api.getIncidents(), api.getThresholds()])
      setStats(s); setInc(Array.isArray(i) ? i : [])
      setW(t.warning_threshold || t.warning || 50)
      setD(t.danger_threshold  || t.danger  || 100)
      setError(null)
    } catch (e) { setError(e.message) }
  }
  useEffect(() => { load() }, [])

  const save = async () => {
    if (warning >= danger) return alert('Warning must be less than danger threshold')
    await api.updateThresholds({ warning_threshold: warning, danger_threshold: danger })
    setSaved(true); setTimeout(() => setSaved(false), 2000); load()
  }

  const dist      = stats?.risk_distribution || {}
  const chartData = (stats?.recent_counts || []).map((v, i) => ({ i, v }))
  const latestCount = stats?.peak_crowd || 0
  const latestRisk  = latestCount >= danger ? 'DANGER' : latestCount >= warning ? 'WARNING' : 'SAFE'

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
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
          <div className="glass-card" style={{ padding: 24, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <RiskGauge count={latestCount} risk={latestRisk} message={`Peak: ${latestCount} people`} />
          </div>
          <div style={{ display: 'grid', gridTemplateRows: '1fr 1fr 1fr', gap: 12 }}>
            <StatCard label="Safe Events"    value={dist.SAFE    || 0} color="var(--accent-green)" />
            <StatCard label="Warning Events" value={dist.WARNING || 0} color="var(--accent-amber)" />
            <StatCard label="Danger Events"  value={dist.DANGER  || 0} color="var(--accent-red)"   />
          </div>
          <div className="glass-card" style={{ padding: 20 }}>
            <div className="card-label">Recent Trend</div>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={chartData}>
                <XAxis dataKey="i" hide />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} width={28} />
                <Tooltip contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border-glass)', borderRadius: 8, fontSize: 12 }} />
                <Line type="monotone" dataKey="v" stroke="var(--accent-purple)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div className="glass-card" style={{ padding: 20 }}>
            <div className="card-label">Recent Incidents</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {incidents.slice(0, 5).map((inc, i) => {
                const color = inc.risk_level === 'DANGER' ? 'var(--accent-red)' : 'var(--accent-amber)'
                return (
                  <div key={i} style={{ padding: '10px 14px', borderRadius: 10, background: 'var(--bg-glass)', border: `1px solid ${color}33`, borderLeft: `3px solid ${color}` }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ color, fontSize: 11, fontWeight: 700 }}>{inc.risk_level}</span>
                      <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>{inc.timestamp}</span>
                    </div>
                    <div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>{inc.message}</div>
                  </div>
                )
              })}
              {incidents.length === 0 && <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No recent incidents</div>}
            </div>
          </div>

          <div className="glass-card" style={{ padding: 20 }}>
            <div className="card-label">Threshold Editor</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Warning Threshold</span>
                  <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent-amber)' }}>{warning}</span>
                </div>
                <input type="range" min={1} max={200} value={warning} onChange={e => setW(Number(e.target.value))} style={{ width: '100%', accentColor: 'var(--accent-amber)' }} />
              </div>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Danger Threshold</span>
                  <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent-red)' }}>{danger}</span>
                </div>
                <input type="range" min={1} max={500} value={danger} onChange={e => setD(Number(e.target.value))} style={{ width: '100%', accentColor: 'var(--accent-red)' }} />
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', padding: '8px 12px', borderRadius: 8, background: 'var(--bg-glass)' }}>
                At current settings: <span style={{ color: 'var(--accent-amber)' }}>{warning}+ people</span> triggers WARNING, <span style={{ color: 'var(--accent-red)' }}>{danger}+ people</span> triggers DANGER
              </div>
              <button onClick={save} style={{ padding: '10px 20px', borderRadius: 10, background: saved ? 'var(--accent-green)' : 'var(--accent-purple)', color: '#fff', fontWeight: 700, fontSize: 13, cursor: 'pointer', border: 'none' }}>
                {saved ? '✓ Saved!' : 'Save Thresholds'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </PageTransition>
  )
}
