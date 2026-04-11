import { useState, useEffect } from 'react'
import PageTransition from '../components/PageTransition'
import StatCard from '../components/StatCard'
import { api } from '../utils/api'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'

export default function SystemMonitor() {
  const [sys,     setSys]  = useState(null)
  const [cal,     setCal]  = useState(null)
  const [history, setHist] = useState([])
  const [error,   setError] = useState(null)
  const [tick,    setTick]  = useState(0)

  const load = async () => {
    try {
      const [s, c] = await Promise.all([api.getSystemStats(), api.getCalibration()])
      setSys(s); setCal(c)
      setHist(h => [...h.slice(-29), { tick, cpu: s.cpu_percent, ram: s.memory_percent }])
      setTick(t => t + 1)
      setError(null)
    } catch (e) { setError(e.message) }
  }

  useEffect(() => { load(); const id = setInterval(load, 10000); return () => clearInterval(id) }, [])

  if (error) return (
    <PageTransition>
      <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
        {error} <button onClick={load} style={{ marginLeft: 12, color: 'var(--accent-purple)', cursor: 'pointer', background: 'none', border: 'none' }}>Retry</button>
      </div>
    </PageTransition>
  )

  const maeQuality = (mae) => mae < 5 ? { label: 'World Class', color: 'var(--accent-green)' } : mae < 10 ? { label: 'Excellent', color: 'var(--accent-cyan)' } : mae < 15 ? { label: 'Good', color: 'var(--accent-amber)' } : mae < 20 ? { label: 'Fair', color: 'var(--accent-violet)' } : { label: 'Needs Training', color: 'var(--accent-red)' }
  const mae     = sys?.model_mae || 0
  const quality = maeQuality(mae)
  const learned = cal?.scene_learning || []

  return (
    <PageTransition>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 16 }}>
          <StatCard label="CPU"       value={sys?.cpu_percent      || 0} sub="%"  color="var(--accent-cyan)"   delay={0}    />
          <StatCard label="RAM %"     value={sys?.memory_percent   || 0} sub="%"  color="var(--accent-violet)" delay={0.08} />
          <StatCard label="RAM Used"  value={sys?.memory_used_gb   || 0} sub="GB" color="var(--accent-purple)" delay={0.16} decimals={1} />
          <div className="glass-card" style={{ padding: '20px 22px' }}>
            <div className="card-label">Uptime</div>
            <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--accent-green)' }}>{sys?.uptime_human || '—'}</div>
          </div>
          <StatCard label="Model MAE" value={mae} color={quality.color} delay={0.32} decimals={2} />
        </div>

        <div className="glass-card" style={{ padding: 20 }}>
          <div className="card-label">CPU & RAM — Last 30 Readings</div>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={history}>
              <XAxis dataKey="tick" hide />
              <YAxis domain={[0, 100]} tick={{ fill: 'var(--text-muted)', fontSize: 10 }} width={28} />
              <Tooltip contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border-glass)', borderRadius: 8, fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 11, color: 'var(--text-secondary)' }} />
              <Line type="monotone" dataKey="cpu" stroke="var(--accent-cyan)"   strokeWidth={2} dot={false} name="CPU %" />
              <Line type="monotone" dataKey="ram" stroke="var(--accent-violet)" strokeWidth={2} dot={false} name="RAM %" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="glass-card" style={{ padding: 20 }}>
          <div className="card-label">Model Info</div>
          <div style={{ display: 'flex', gap: 20, alignItems: 'center', flexWrap: 'wrap' }}>
            <div style={{ fontSize: 56, fontFamily: "'Space Grotesk', sans-serif", fontWeight: 800, color: quality.color, filter: `drop-shadow(0 0 20px ${quality.color}66)` }}>{mae.toFixed(2)}</div>
            <div>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8 }}>Mean Absolute Error</div>
              <div style={{ display: 'inline-block', padding: '4px 14px', borderRadius: 100, background: quality.color + '22', color: quality.color, fontSize: 12, fontWeight: 700 }}>{quality.label}</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 10, lineHeight: 1.7 }}>
                Architecture: VGG16 + Dilated CNN<br />
                Dataset: ShanghaiTech A+B + JHU-Crowd++<br />
                Ensemble: YOLO / Density / CSRNet
              </div>
            </div>
          </div>
        </div>

        {learned.length > 0 && (
          <div className="glass-card" style={{ padding: 20 }}>
            <div className="card-label">Scene Learning Table ({learned.length} scenes)</div>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                <thead>
                  <tr>{['Fingerprint','Scale','Conf','IOU','Corrections','Status','Accuracy'].map(h => (
                    <th key={h} style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '1px', borderBottom: '1px solid var(--border-glass)', whiteSpace: 'nowrap' }}>{h}</th>
                  ))}</tr>
                </thead>
                <tbody>
                  {learned.map((s, i) => {
                    const statusColor = s.status === 'converged' ? 'var(--accent-green)' : s.status === 'overcounting' ? 'var(--accent-red)' : 'var(--accent-amber)'
                    return (
                      <tr key={s.scene} style={{ borderBottom: '1px solid var(--border-glass)', background: i % 2 === 0 ? 'var(--bg-glass)' : 'transparent' }}>
                        <td style={{ padding: '8px 12px', color: 'var(--text-secondary)', fontFamily: 'monospace' }}>{s.scene}</td>
                        <td style={{ padding: '8px 12px', color: 'var(--accent-cyan)', fontWeight: 700 }}>{s.scale}</td>
                        <td style={{ padding: '8px 12px', color: 'var(--text-secondary)' }}>{s.conf}</td>
                        <td style={{ padding: '8px 12px', color: 'var(--text-secondary)' }}>{s.iou}</td>
                        <td style={{ padding: '8px 12px', color: 'var(--text-secondary)' }}>{s.corrections}</td>
                        <td style={{ padding: '8px 12px' }}><span style={{ padding: '2px 10px', borderRadius: 100, background: statusColor + '22', color: statusColor, fontSize: 10, fontWeight: 700 }}>{s.status}</span></td>
                        <td style={{ padding: '8px 12px', color: 'var(--text-secondary)' }}>{s.accuracy}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </PageTransition>
  )
}
