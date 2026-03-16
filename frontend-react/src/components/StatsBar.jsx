import { motion } from 'framer-motion'

const STATS = [
  { key: 'total_detections', label: 'Total Detections', color: '#00d4ff' },
  { key: 'total_alerts',     label: 'Total Alerts',     color: '#ff3b5c' },
  { key: 'avg_crowd',        label: 'Avg Crowd Size',   color: '#00ff88' },
  { key: 'peak_crowd',       label: 'Peak Count',       color: '#ff9500' },
]

export default function StatsBar({ stats }) {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(4, 1fr)',
      borderBottom: '1px solid rgba(30,45,74,0.5)',
      background: 'rgba(8,12,20,0.8)'
    }}>
      {STATS.map((s, i) => (
        <motion.div
          key={s.key}
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1,  y: 0   }}
          transition={{ delay: i * 0.1 }}
          style={{
            padding: '18px 24px',
            textAlign: 'center',
            borderRight: i < 3 ? '1px solid rgba(30,45,74,0.5)' : 'none',
            position: 'relative',
            overflow: 'hidden'
          }}
        >
          {/* Bottom accent line */}
          <div style={{
            position: 'absolute',
            bottom: 0, left: '50%',
            transform: 'translateX(-50%)',
            width: '40%', height: 2,
            background: `linear-gradient(90deg, transparent, ${s.color}, transparent)`,
            opacity: 0.5
          }} />

          <motion.div
            key={stats[s.key]}
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1,   opacity: 1 }}
            style={{
              fontSize: '2.2rem',
              fontWeight: 900,
              color: s.color,
              lineHeight: 1,
              textShadow: `0 0 20px ${s.color}60`
            }}
          >
            {stats[s.key] || 0}
          </motion.div>
          <div style={{
            fontSize: '0.68rem',
            color: '#475569',
            marginTop: 6,
            textTransform: 'uppercase',
            letterSpacing: 1.5,
            fontWeight: 600
          }}>
            {s.label}
          </div>
        </motion.div>
      ))}
    </div>
  )
}