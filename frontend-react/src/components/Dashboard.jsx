import { useState, useCallback, useEffect } from 'react'
import { motion } from 'framer-motion'
import StatCard from './StatCard'
import PageTransition from './PageTransition'
import WebcamMonitor from './WebcamMonitor'
import RiskGauge from './RiskGauge'
import MultiCameraPanel from './MultiCameraPanel'
import ImageAnalysis from './ImageAnalysis'
import VideoAnalysis from './VideoAnalysis'
import CrowdChart from './CrowdChart'
import HistoryTable from './HistoryTable'
import AlertBanner from './AlertBanner'
import AnomalyPanel from './AnomalyPanel'
import FlowIndicator from './FlowIndicator'
import { useStats } from '../hooks/useStats'

function CapacityBar({ current, max, status }) {
  const pct = Math.min(Math.round(current / Math.max(max, 1) * 100), 100)
  const colors = {
    normal:   'var(--accent-green)',
    caution:  'var(--accent-cyan)',
    warning:  'var(--accent-amber)',
    critical: 'var(--accent-red)'
  }
  const color = colors[status] || colors.normal
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card"
      style={{ padding: '14px 20px' }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <div className="card-label" style={{ margin: 0 }}>Location Capacity</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{current} / {max} people</span>
          <span style={{ fontSize: 11, fontWeight: 700, padding: '2px 10px', borderRadius: 100,
            background: `${color}18`, border: `1px solid ${color}44`, color }}>
            {pct}% {status.toUpperCase()}
          </span>
        </div>
      </div>
      <div style={{ height: 6, background: 'var(--bg-glass)', borderRadius: 3, overflow: 'hidden' }}>
        <motion.div
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          style={{ height: '100%', background: color, borderRadius: 3,
            boxShadow: `0 0 8px ${color}66` }}
        />
      </div>
    </motion.div>
  )
}

export default function Dashboard({ onLiveChange }) {
  const { stats, refresh } = useStats()
  const [risk,            setRisk]            = useState('SAFE')
  const [count,           setCount]           = useState(0)
  const [message,         setMessage]         = useState('System ready. Start camera or upload media.')
  const [zones,           setZones]           = useState([])
  const [alert,           setAlert]           = useState(null)
  const [confidenceScore, setConfidenceScore] = useState(null)
  const [locationCfg,     setLocationCfg]     = useState({ max_capacity: 100, caution_pct: 0.5, warning_pct: 0.75, critical_pct: 0.9 })
  const [capacityStatus,  setCapacityStatus]  = useState('normal')
  const [latestAnomaly,   setLatestAnomaly]   = useState(null)
  const [latestFlow,      setLatestFlow]      = useState(null)
  const [flowData,        setFlowData]        = useState(null)

  useEffect(() => {
    fetch('/location/config').then(r => r.json()).then(cfg => {
      if (cfg && cfg.max_capacity) setLocationCfg(cfg)
    }).catch(() => {})
  }, [])

  const computeCapacityStatus = useCallback((cnt, cfg) => {
    const pct = cnt / Math.max(cfg.max_capacity, 1) * 100
    if (pct >= cfg.critical_pct * 100) return 'critical'
    if (pct >= cfg.warning_pct  * 100) return 'warning'
    if (pct >= cfg.caution_pct  * 100) return 'caution'
    return 'normal'
  }, [])

  const handleData = useCallback((data) => {
    if (data.risk_level)                 setRisk(data.risk_level)
    if (data.person_count !== undefined) {
      setCount(data.person_count)
      setCapacityStatus(computeCapacityStatus(data.person_count, locationCfg))
    }
    if (data.message)                    setMessage(data.message)
    if (data.zones)                      setZones(data.zones)
    if (data.confidence_score !== undefined) setConfidenceScore(data.confidence_score)
    if (data.anomaly)                    setLatestAnomaly(data.anomaly)
    if (data.crowd_flow)                 setLatestFlow(data.crowd_flow)
    if (data.flow_direction || data.flow_state || data.flow_result ||
        (data.direction !== undefined)) {
      setFlowData({
        flow_direction: String(data.flow_direction || data.direction || 'Unknown'),
        flow_speed:     parseFloat(data.flow_speed ?? data.rate_per_min ?? data.speed ?? 0) || 0,
        flow_state:     String(data.flow_state || ''),
        surge_detected: Boolean(data.surge_detected),
        rate_per_min:   parseFloat(data.rate_per_min ?? 0) || 0,
      })
    }
    if (data.scene_type) window.lastSceneType = data.scene_type
    if (data.risk_level === 'DANGER' || data.risk_level === 'OVERCROWDED') setAlert({ message: data.message })
    refresh()
  }, [refresh, locationCfg, computeCapacityStatus])

  const handleWebcamData = useCallback((data) => {
    if (onLiveChange) onLiveChange(true)
    handleData(data)
  }, [handleData, onLiveChange])

  const s = (i) => ({ initial: { opacity: 0, y: 20 }, animate: { opacity: 1, y: 0 }, transition: { delay: i * 0.08, duration: 0.4 } })

  return (
    <PageTransition>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        {/* Row 1: stat cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
          <StatCard label="Total Detections" value={stats.total_detections} color="var(--accent-cyan)"   delay={0}   />
          <StatCard label="Total Alerts"     value={stats.total_alerts}     color="var(--accent-violet)" delay={0.08}/>
          <StatCard label="Avg Crowd Size"   value={stats.avg_crowd}        color="var(--accent-green)"  delay={0.16} decimals={1}/>
          <StatCard label="Peak Count"       value={stats.peak_crowd}       color="var(--accent-red)"    delay={0.24}/>
        </div>

        {/* Row 2: capacity bar */}
        <CapacityBar current={count} max={locationCfg.max_capacity} status={capacityStatus} />

        {/* Row 3: webcam (2fr) · risk gauge (1fr) · anomaly panel (1fr) */}
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: 16 }}>
          <motion.div {...s(1)}><WebcamMonitor onData={handleWebcamData} /></motion.div>
          <motion.div {...s(2)} style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <RiskGauge count={count} risk={risk} message={message} />
            {confidenceScore !== null && (
              <div style={{ fontSize: 11, color: 'var(--text-muted)', textAlign: 'center', padding: '4px 0' }}>
                Confidence: <span style={{ color: confidenceScore > 70 ? 'var(--accent-green)' : confidenceScore > 40 ? 'var(--accent-amber)' : 'var(--accent-red)', fontWeight: 600 }}>
                  {confidenceScore}%
                </span>
              </div>
            )}
          </motion.div>
          <motion.div {...s(3)}>
            <AnomalyPanel latestAnomaly={latestAnomaly} latestFlow={latestFlow} />
          </motion.div>
        </div>

        {/* Row 3b: flow indicator */}
        {flowData && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
            <FlowIndicator flowData={flowData} />
          </motion.div>
        )}

        {/* Row 4: multi-camera (1fr) · crowd chart (1fr) */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <motion.div {...s(4)}><MultiCameraPanel onAggregateUpdate={(data) => {
            if (data.total_people !== undefined && data.camera_count > 0) {
              setCount(data.total_people)
              if (data.risk_level) setRisk(data.risk_level)
            }
          }} /></motion.div>
          <motion.div {...s(5)}><CrowdChart stats={stats} onRefresh={refresh} /></motion.div>
        </div>

        {/* Row 5: image analysis · video analysis */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 16 }}>
          <motion.div {...s(6)}><ImageAnalysis onResult={handleData} /></motion.div>
          <motion.div {...s(7)}><VideoAnalysis onResult={handleData} /></motion.div>
        </div>

        {/* Row 6: history */}
        <motion.div {...s(8)}><HistoryTable /></motion.div>
      </div>
      <AlertBanner alert={alert} onDismiss={() => setAlert(null)} />
    </PageTransition>
  )
}
