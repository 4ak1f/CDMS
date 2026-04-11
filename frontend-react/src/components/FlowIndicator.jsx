import { motion } from 'framer-motion'
import { AlertTriangle } from 'lucide-react'

const DIRECTIONS = {
  'Up':        { icon: '↑', label: 'Moving Up' },
  'Down':      { icon: '↓', label: 'Moving Down' },
  'Left':      { icon: '←', label: 'Moving Left' },
  'Right':     { icon: '→', label: 'Moving Right' },
  'Inward':    { icon: '⊕', label: 'Converging' },
  'Outward':   { icon: '⊗', label: 'Dispersing' },
  'Unknown':   { icon: '·', label: 'No Movement' },
  'Turbulent': { icon: '↯', label: 'Turbulent' },
}

export default function FlowIndicator({ flowData, compact = false }) {
  if (!flowData) return null

  const direction = String(flowData.flow_direction || flowData.direction || 'Unknown')
  const speed     = parseFloat(flowData.flow_speed ?? flowData.rate_per_min ?? flowData.speed ?? 0) || 0
  const surge     = Boolean(flowData.surge_detected)
  const state     = String(flowData.flow_state || (surge ? 'SURGE' : speed > 3 ? 'GATHERING' : speed < -3 ? 'DISPERSING' : 'STABLE'))

  // Strip arrow prefix from flow_detection direction strings like "→ Right"
  const dirKey = direction.replace(/^[↑↓←→↗↘↙↖⊕⊗↯·]\s*/, '').split(' ')[0] || 'Unknown'
  const dirInfo = DIRECTIONS[dirKey] || DIRECTIONS['Unknown']

  const stateColor = surge ? 'var(--accent-red)' :
    state === 'GATHERING' ? 'var(--accent-amber)' :
    state === 'DISPERSING' ? 'var(--accent-cyan)' : 'var(--accent-green)'

  if (compact) return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <span style={{ fontSize: 16, lineHeight: 1 }}>{dirInfo.icon}</span>
      <span style={{ fontSize: 11, fontWeight: 700, color: stateColor }}>{state}</span>
      {speed > 0 && <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{speed.toFixed(1)}</span>}
      {surge && <AlertTriangle size={12} style={{ color: 'var(--accent-red)' }} />}
    </div>
  )

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        padding: '14px 16px',
        background: surge ? 'rgba(255,59,92,0.08)' : 'var(--bg-glass)',
        border: `1px solid ${surge ? 'rgba(255,59,92,0.3)' : 'var(--border-glass)'}`,
        borderRadius: 12,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
        <div className="card-label" style={{ margin: 0 }}>Crowd Flow</div>
        {surge && (
          <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 100,
            background: 'rgba(255,59,92,0.15)', color: 'var(--accent-red)',
            border: '1px solid rgba(255,59,92,0.3)', letterSpacing: 1 }}>
            SURGE
          </span>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
        <div style={{ textAlign: 'center', padding: '10px 8px', background: 'var(--bg-glass)',
          borderRadius: 10, border: '1px solid var(--border-glass)' }}>
          <div style={{ fontSize: 24, lineHeight: 1, marginBottom: 4 }}>{dirInfo.icon}</div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: 1 }}>DIRECTION</div>
          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', marginTop: 2 }}>
            {dirInfo.label}
          </div>
        </div>

        <div style={{ textAlign: 'center', padding: '10px 8px', background: 'var(--bg-glass)',
          borderRadius: 10, border: '1px solid var(--border-glass)' }}>
          <div style={{ fontSize: 20, fontWeight: 800, color: stateColor, fontFamily: "'Space Grotesk', sans-serif",
            lineHeight: 1, marginBottom: 4 }}>
            {speed.toFixed(1)}
          </div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: 1 }}>SPEED</div>
          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginTop: 2 }}>units/sec</div>
        </div>

        <div style={{ textAlign: 'center', padding: '10px 8px', background: `${stateColor}12`,
          borderRadius: 10, border: `1px solid ${stateColor}30` }}>
          <div style={{ fontSize: 12, fontWeight: 800, color: stateColor, lineHeight: 1,
            marginBottom: 4, marginTop: 4 }}>{state}</div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: 1 }}>STATE</div>
          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginTop: 2 }}>
            {surge ? 'DANGER' : speed > 3 ? 'HIGH' : speed > 1 ? 'MODERATE' : 'LOW'}
          </div>
        </div>
      </div>

      {surge && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          style={{ marginTop: 10, padding: '8px 12px', borderRadius: 8,
            background: 'rgba(255,59,92,0.1)', border: '1px solid rgba(255,59,92,0.2)',
            fontSize: 12, color: 'var(--accent-red)', fontWeight: 600 }}>
          Crowd surge detected — risk of stampede. Immediate attention required.
        </motion.div>
      )}
    </motion.div>
  )
}
