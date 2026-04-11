import { useState, useEffect } from 'react'
import PageTransition from '../components/PageTransition'
import StatCard from '../components/StatCard'
import WebcamMonitor from '../components/WebcamMonitor'
import RiskGauge from '../components/RiskGauge'
import ZoneGrid from '../components/ZoneGrid'
import { api } from '../utils/api'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

export default function LiveView() {
  const [liveData,    setLiveData]  = useState({ person_count: 0, risk_level: 'SAFE', message: 'Connecting...', zones: [] })
  const [countHistory,setHistory]   = useState([])
  const [calibration, setCal]       = useState(null)
  const [fps,         setFps]       = useState(0)
  const [inferenceMs, setInfMs]     = useState(0)
  const [sceneType,   setSceneType] = useState('—')
  const [cameras,     setCameras]   = useState([])
  const [sessionCode, setSession]   = useState(null)

  useEffect(() => {
    api.getCalibration().then(setCal).catch(() => {})
    const id = setInterval(async () => {
      try {
        const s = await api.getStats()
        if (s.recent_counts?.length) {
          setHistory(s.recent_counts.slice(-60).map((v, i) => ({ i, v })))
        }
      } catch {}
    }, 8000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    const pollCameras = async () => {
      try {
        const res = await fetch('/session/current').then(r => r.json())
        if (res.active && res.cameras) {
          setCameras(res.cameras.filter(c => c.active))
          setSession(res.code)
        }
      } catch(e) {}
    }
    pollCameras()
    const interval = setInterval(pollCameras, 3000)
    return () => clearInterval(interval)
  }, [])

  const handleWebcamData = (data) => {
    setLiveData(data)
    if (data.scene_type)   setSceneType(data.scene_type)
    if (data.inference_ms) setInfMs(data.inference_ms)
    setHistory(h => [...h.slice(-59), { i: h.length, v: data.person_count || 0 }])
  }

  const learned = calibration?.scene_learning || []

  return (
    <PageTransition>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
          <StatCard label="Current Count"  value={liveData.person_count} color="var(--accent-cyan)"   delay={0}   />
          <StatCard label="FPS"            value={fps}                   color="var(--accent-green)"  delay={0.08}/>
          <StatCard label="Inference (ms)" value={inferenceMs}           color="var(--accent-violet)" delay={0.16}/>
          <div className="glass-card" style={{ padding: '20px 22px' }}>
            <div className="card-label">Scene Type</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--accent-amber)', wordBreak: 'break-word' }}>{sceneType}</div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
          <WebcamMonitor onData={handleWebcamData} onFps={setFps} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <RiskGauge count={liveData.person_count} risk={liveData.risk_level} message={liveData.message} />
            <ZoneGrid zones={liveData.zones || []} />
          </div>
        </div>

        <div className="glass-card" style={{ padding: 20 }}>
          <div className="card-label">Real-Time Crowd Count — Last 60 Readings</div>
          <ResponsiveContainer width="100%" height={120}>
            <AreaChart data={countHistory}>
              <defs>
                <linearGradient id="lv-grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="var(--accent-cyan)" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="var(--accent-cyan)" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <XAxis dataKey="i" hide />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} width={28} />
              <Tooltip contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border-glass)', borderRadius: 8, fontSize: 12 }} />
              <Area type="monotone" dataKey="v" stroke="var(--accent-cyan)" fill="url(#lv-grad)" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {cameras.length > 0 && (
          <div className="glass-card" style={{ padding: 20 }}>
            <div className="card-label">
              Connected Cameras ({cameras.length})
              {sessionCode && (
                <span style={{ marginLeft: 8, fontSize: 10,
                  color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                  {sessionCode}
                </span>
              )}
            </div>
            <div style={{ display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
              gap: 12 }}>
              {cameras.map(cam => {
                const riskColor = cam.risk_level === 'DANGER' ? 'var(--accent-red)' :
                  cam.risk_level === 'WARNING' ? 'var(--accent-amber)' : 'var(--accent-green)'
                return (
                  <div key={cam.id} style={{
                    padding: '14px 16px',
                    background: 'var(--bg-glass)',
                    border: '1px solid var(--border-glass)',
                    borderRadius: 12,
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between',
                      alignItems: 'center', marginBottom: 10 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{ width: 7, height: 7, borderRadius: '50%',
                          background: 'var(--accent-green)',
                          boxShadow: '0 0 6px var(--accent-green)' }} />
                        <span style={{ fontSize: 12, fontWeight: 600,
                          color: 'var(--text-primary)' }}>{cam.name}</span>
                      </div>
                      <span style={{ fontSize: 10, fontWeight: 700,
                        padding: '2px 8px', borderRadius: 100,
                        background: `${riskColor}15`,
                        color: riskColor,
                        border: `1px solid ${riskColor}30` }}>
                        {cam.risk_level}
                      </span>
                    </div>
                    <div style={{ fontSize: 32, fontWeight: 900,
                      color: riskColor, fontFamily: "'Space Grotesk', sans-serif",
                      lineHeight: 1, marginBottom: 4,
                      filter: `drop-shadow(0 0 8px ${riskColor}66)` }}>
                      {cam.person_count}
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)',
                      letterSpacing: 1, textTransform: 'uppercase' }}>
                      people detected
                    </div>
                    {cam.scene_type && cam.scene_type !== 'unknown' && (
                      <div style={{ fontSize: 10, color: 'var(--text-muted)',
                        marginTop: 6 }}>{cam.scene_type}</div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {learned.length > 0 && (
          <div className="glass-card" style={{ padding: 20 }}>
            <div className="card-label">Scene Learning</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
              {learned.slice(0, 6).map(s => (
                <div key={s.scene} style={{ padding: 14, borderRadius: 12, background: 'var(--bg-glass)', border: '1px solid var(--border-glass)' }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6, wordBreak: 'break-all' }}>{s.scene}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Scale: <span style={{ color: 'var(--accent-cyan)', fontWeight: 700 }}>{s.scale}</span></div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Corrections: <span style={{ color: 'var(--text-secondary)' }}>{s.corrections}</span></div>
                  <div style={{ fontSize: 10, marginTop: 6, padding: '2px 8px', borderRadius: 100, display: 'inline-block', background: s.status === 'converged' ? 'rgba(0,255,136,0.12)' : s.status === 'overcounting' ? 'rgba(255,59,92,0.12)' : 'rgba(245,158,11,0.12)', color: s.status === 'converged' ? 'var(--accent-green)' : s.status === 'overcounting' ? 'var(--accent-red)' : 'var(--accent-amber)' }}>
                    {s.status}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </PageTransition>
  )
}
