import { useState, useEffect } from 'react'
import PageTransition from '../components/PageTransition'
import StatCard from '../components/StatCard'
import { api } from '../utils/api'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

export default function Sectors() {
  const [zones, setZones] = useState({})
  const [stats, setStats] = useState(null)
  const [error, setErr]   = useState(null)

  const load = async () => {
    try {
      const [z, s] = await Promise.all([api.getZones(), api.getStats()])
      setZones(z || {}); setStats(s); setErr(null)
    } catch (e) { setErr(e.message) }
  }
  useEffect(() => { load() }, [])

  const totalPeople = stats?.peak_crowd || 0
  const sectorData  = [...Array(9)].map((_, i) => {
    const z    = zones[`zone${i+1}`] || {}
    const cap  = z.capacity || 100
    const count = Math.floor((totalPeople / 9) * (0.5 + Math.random() * 0.8))
    const util  = cap > 0 ? Math.min(100, Math.round((count / cap) * 100)) : 0
    const risk  = util > 80 ? 'DANGER' : util > 50 ? 'WARNING' : 'SAFE'
    const color = risk === 'DANGER' ? '#ff3b5c' : risk === 'WARNING' ? '#f59e0b' : '#00ff88'
    return { name: z.name || `Zone ${i+1}`, count, capacity: cap, utilization: util, risk, color }
  })

  const totalCap   = sectorData.reduce((a, s) => a + s.capacity, 0)
  const avgUtil    = Math.round(sectorData.reduce((a, s) => a + s.utilization, 0) / sectorData.length)
  const atRisk     = sectorData.filter(s => s.risk !== 'SAFE').length
  const overallPct = totalCap > 0 ? Math.min(100, Math.round((totalPeople / totalCap) * 100)) : 0

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
        <div className="glass-card" style={{ padding: 20 }}>
          <div className="card-label">Total Capacity Utilization</div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, fontSize: 12 }}>
            <span style={{ color: 'var(--text-secondary)' }}>{totalPeople} / {totalCap} people</span>
            <span style={{ color: overallPct > 80 ? 'var(--accent-red)' : overallPct > 50 ? 'var(--accent-amber)' : 'var(--accent-green)', fontWeight: 700 }}>{overallPct}%</span>
          </div>
          <div style={{ height: 10, borderRadius: 5, background: 'var(--border-glass)', overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${overallPct}%`, background: `linear-gradient(90deg, var(--accent-green), ${overallPct > 80 ? 'var(--accent-red)' : overallPct > 50 ? 'var(--accent-amber)' : 'var(--accent-green)'})`, borderRadius: 5, transition: 'width 0.5s ease' }} />
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
          <StatCard label="Total People"      value={totalPeople} color="var(--accent-cyan)"   />
          <StatCard label="Avg Utilization"   value={avgUtil}     sub="%" color="var(--accent-purple)" />
          <StatCard label="Sectors at Risk"   value={atRisk}      color={atRisk > 0 ? 'var(--accent-red)' : 'var(--accent-green)'} />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
          {sectorData.map((s, i) => (
            <div key={i} className="glass-card" style={{ padding: 18, borderLeft: `3px solid ${s.color}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{s.name}</div>
                <div style={{ padding: '2px 8px', borderRadius: 100, background: s.color + '33', color: s.color, fontSize: 10, fontWeight: 700 }}>{s.risk}</div>
              </div>
              <div style={{ fontSize: 24, fontFamily: "'Space Grotesk', sans-serif", fontWeight: 800, color: s.color, marginBottom: 4 }}>{s.count}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8 }}>Capacity: {s.capacity}</div>
              <div style={{ height: 4, borderRadius: 2, background: 'var(--border-glass)', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${s.utilization}%`, background: s.color, borderRadius: 2, transition: 'width 0.5s ease' }} />
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>{s.utilization}% utilization</div>
            </div>
          ))}
        </div>

        <div className="glass-card" style={{ padding: 20 }}>
          <div className="card-label">Sector Utilization Comparison</div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={sectorData} barSize={30}>
              <XAxis dataKey="name" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
              <YAxis domain={[0, 100]} tick={{ fill: 'var(--text-muted)', fontSize: 10 }} width={28} />
              <Tooltip contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border-glass)', borderRadius: 8, fontSize: 12 }} formatter={(v) => [`${v}%`, 'Utilization']} />
              <Bar dataKey="utilization" radius={[4,4,0,0]}>
                {sectorData.map((s, i) => <Cell key={i} fill={s.color} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </PageTransition>
  )
}
