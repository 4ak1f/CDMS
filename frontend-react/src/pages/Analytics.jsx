import { useState, useEffect } from 'react'
import PageTransition from '../components/PageTransition'
import { api } from '../utils/api'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

function WeeklyComparison() {
  const [data, setData] = useState(null)

  useEffect(() => {
    fetch('/analytics/weekly').then(r => r.json()).then(setData).catch(() => {})
  }, [])

  if (!data) return null

  const { this_week: tw, last_week: lw, changes: ch } = data

  const Metric = ({ label, thisVal, lastVal, change, color, suffix = '' }) => {
    const up = change > 0
    const changeColor = label === 'Alert Rate' || label === 'Alerts'
      ? (up ? 'var(--accent-red)' : 'var(--accent-green)')
      : (up ? 'var(--accent-green)' : 'var(--accent-red)')
    return (
      <div style={{ padding: '14px 16px', borderRadius: 12, background: 'var(--bg-glass)',
        border: '1px solid var(--border-glass)' }}>
        <div style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: 1, marginBottom: 8 }}>
          {label.toUpperCase()}
        </div>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, marginBottom: 6 }}>
          <span style={{ fontSize: 24, fontWeight: 800, color, fontFamily: "'Space Grotesk', sans-serif" }}>
            {thisVal}{suffix}
          </span>
          {change !== null && (
            <span style={{ fontSize: 11, fontWeight: 700, color: changeColor, marginBottom: 4 }}>
              {up ? '▲' : '▼'} {Math.abs(change)}%
            </span>
          )}
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          Last week: <span style={{ color: 'var(--text-secondary)' }}>{lastVal}{suffix}</span>
        </div>
      </div>
    )
  }

  return (
    <div className="glass-card" style={{ padding: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div className="card-label" style={{ marginBottom: 0 }}>Week-over-Week Comparison</div>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          This week: {tw.total} detections &nbsp;·&nbsp; Last week: {lw.total} detections
        </span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        <Metric label="Avg Crowd"  thisVal={tw.avg}        lastVal={lw.avg}        change={ch.avg_crowd}  color="var(--accent-cyan)"   />
        <Metric label="Peak Count" thisVal={tw.peak}       lastVal={lw.peak}       change={ch.peak_crowd} color="var(--accent-violet)" />
        <Metric label="Alerts"     thisVal={tw.alerts}     lastVal={lw.alerts}     change={ch.alerts}     color="var(--accent-amber)"  />
        <Metric label="Alert Rate" thisVal={tw.alert_rate} lastVal={lw.alert_rate} change={ch.alert_rate} color="var(--accent-red)"    suffix="%" />
      </div>
    </div>
  )
}

function maeQuality(mae) {
  if (mae < 5)  return { label: 'World Class', color: 'var(--accent-green)' }
  if (mae < 10) return { label: 'Excellent',   color: 'var(--accent-cyan)'  }
  if (mae < 15) return { label: 'Good',        color: 'var(--accent-amber)' }
  if (mae < 20) return { label: 'Fair',        color: 'var(--accent-violet)'}
  return           { label: 'Needs Training', color: 'var(--accent-red)'   }
}

export default function Analytics() {
  const [sys,   setSys]  = useState(null)
  const [cal,   setCal]  = useState(null)
  const [fb,    setFb]   = useState(null)
  const [error, setErr]  = useState(null)

  const load = async () => {
    try {
      const [s, c, f] = await Promise.all([api.getSystemStats(), api.getCalibration(), api.getFeedback()])
      setSys(s); setCal(c); setFb(f); setErr(null)
    } catch (e) { setErr(e.message) }
  }
  useEffect(() => { load() }, [])

  if (error) return (
    <PageTransition>
      <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
        {error} <button onClick={load} style={{ marginLeft: 12, color: 'var(--accent-purple)', cursor: 'pointer', background: 'none', border: 'none' }}>Retry</button>
      </div>
    </PageTransition>
  )

  const mae      = sys?.model_mae || 0
  const quality  = maeQuality(mae)
  const fbStats  = fb?.stats || {}
  const learned  = cal?.scene_learning || []
  const barData  = Object.entries(fbStats).map(([scene, s]) => ({ scene: scene.replace(/_/g, ' '), count: s.sample_count || 0 }))
  const totalFb  = cal?.total_feedback_samples || 0

  return (
    <PageTransition>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        <WeeklyComparison />
        <div className="glass-card" style={{ padding: 28 }}>
          <div className="card-label">Model Performance</div>
          <div style={{ display: 'flex', gap: 24, alignItems: 'center', flexWrap: 'wrap' }}>
            <div style={{ fontSize: 64, fontFamily: "'Space Grotesk', sans-serif", fontWeight: 800, color: quality.color, filter: `drop-shadow(0 0 24px ${quality.color}66)` }}>{mae.toFixed(2)}</div>
            <div>
              <div style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 10 }}>Mean Absolute Error (lower = better)</div>
              <div style={{ display: 'inline-block', padding: '5px 16px', borderRadius: 100, background: quality.color + '22', color: quality.color, fontSize: 13, fontWeight: 700, marginBottom: 10 }}>{quality.label}</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.8 }}>
                Architecture: <span style={{ color: 'var(--text-secondary)' }}>VGG16 + Dilated CNN (CSRNet-style)</span><br />
                Training data: <span style={{ color: 'var(--text-secondary)' }}>ShanghaiTech A+B · JHU-Crowd++ · Mall</span><br />
                Inference: <span style={{ color: 'var(--text-secondary)' }}>Multi-scale (384/512/640px) · 3-run median</span><br />
                Ensemble: <span style={{ color: 'var(--text-secondary)' }}>YOLO (sparse) · Density (moderate) · CSRNet (mega)</span>
              </div>
            </div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div className="glass-card" style={{ padding: 20 }}>
            <div className="card-label">Feedback Samples by Scene ({totalFb} total)</div>
            {barData.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={barData} layout="vertical">
                  <XAxis type="number" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                  <YAxis type="category" dataKey="scene" tick={{ fill: 'var(--text-secondary)', fontSize: 10 }} width={120} />
                  <Tooltip contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border-glass)', borderRadius: 8, fontSize: 12 }} />
                  <Bar dataKey="count" fill="var(--accent-purple)" radius={[0,4,4,0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : <div style={{ color: 'var(--text-muted)', fontSize: 13, padding: '20px 0' }}>No feedback samples yet</div>}
          </div>

          <div className="glass-card" style={{ padding: 20 }}>
            <div className="card-label">Scene Learning Summary ({learned.length} scenes)</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 240, overflowY: 'auto' }}>
              {learned.map(s => {
                const statusColor = s.status === 'converged' ? 'var(--accent-green)' : s.status === 'overcounting' ? 'var(--accent-red)' : 'var(--accent-amber)'
                const scalePct = Math.min(100, (s.scale / 4) * 100)
                return (
                  <div key={s.scene} style={{ padding: '10px 12px', borderRadius: 10, background: 'var(--bg-glass)', border: '1px solid var(--border-glass)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                      <span style={{ fontSize: 11, color: 'var(--text-secondary)', fontFamily: 'monospace' }}>{s.scene}</span>
                      <span style={{ fontSize: 10, padding: '1px 8px', borderRadius: 100, background: statusColor + '22', color: statusColor, fontWeight: 700 }}>{s.status}</span>
                    </div>
                    <div style={{ height: 4, borderRadius: 2, background: 'var(--border-glass)', overflow: 'hidden', marginBottom: 4 }}>
                      <div style={{ height: '100%', width: `${scalePct}%`, background: 'linear-gradient(90deg, var(--accent-purple), var(--accent-cyan))', borderRadius: 2 }} />
                    </div>
                    <div style={{ display: 'flex', gap: 12, fontSize: 10, color: 'var(--text-muted)' }}>
                      <span>Scale: <span style={{ color: 'var(--accent-cyan)' }}>{s.scale}</span></span>
                      <span>Corrections: <span style={{ color: 'var(--text-secondary)' }}>{s.corrections}</span></span>
                      <span>Accuracy: <span style={{ color: 'var(--text-secondary)' }}>{s.accuracy}</span></span>
                    </div>
                  </div>
                )
              })}
              {learned.length === 0 && <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No scenes learned yet. Submit feedback after analyzing images.</div>}
            </div>
          </div>
        </div>
      </div>
    </PageTransition>
  )
}
