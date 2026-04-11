import { motion } from 'framer-motion'

const ZONE_COLOR = {
  SAFE:    { bg: 'rgba(0,255,136,0.05)',   border: 'rgba(0,255,136,0.2)',   text: 'var(--accent-green)' },
  WARNING: { bg: 'rgba(245,158,11,0.05)',  border: 'rgba(245,158,11,0.2)',  text: 'var(--accent-amber)' },
  DANGER:  { bg: 'rgba(255,59,92,0.05)',   border: 'rgba(255,59,92,0.2)',   text: 'var(--accent-red)'   },
}

export default function ZoneGrid({ zones }) {
  const defaultZones = Array.from({ length: 9 }, (_, i) => ({ zone: `Zone ${i + 1}`, risk: 'SAFE', count: 0 }))
  const displayZones = zones?.length ? zones : defaultZones

  return (
    <div className="glass-card" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border-glass)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span className="card-label" style={{ marginBottom: 0 }}>Zone Monitor</span>
        <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>3×3 grid</span>
      </div>
      <div style={{ flex: 1, padding: 16 }}>
        <p style={{ color: 'var(--text-muted)', fontSize: 11, marginBottom: 12 }}>Real-time zone density analysis</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
          {displayZones.map((z, i) => {
            const style = ZONE_COLOR[z.risk] || ZONE_COLOR.SAFE
            const displayCount = z.count !== undefined
              ? Math.min(Math.round(z.count), 9999)
              : z.density !== undefined
              ? Math.min(Math.round(z.density * 100), 9999)
              : 0
            return (
              <motion.div
                key={z.zone}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.05 }}
                style={{ borderRadius: 10, border: `1px solid ${style.border}`, background: style.bg, padding: '10px 8px', textAlign: 'center', transition: 'all 0.5s ease' }}
              >
                <div style={{ fontSize: 9, color: 'var(--text-muted)', marginBottom: 4 }}>{z.zone}</div>
                <div style={{ fontWeight: 700, fontSize: 11, color: style.text }}>{z.risk}</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>~{displayCount}</div>
              </motion.div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
