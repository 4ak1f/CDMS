import { motion, AnimatePresence } from 'framer-motion'

const RISK_CONFIG = {
  SAFE:    { color: 'var(--accent-green)',  shadow: '0 0 40px rgba(0,255,136,0.4)',  label: 'ALL CLEAR' },
  WARNING: { color: 'var(--accent-amber)',  shadow: '0 0 40px rgba(245,158,11,0.4)', label: 'WARNING'   },
  DANGER:  { color: 'var(--accent-red)',    shadow: '0 0 40px rgba(255,59,92,0.5)',  label: 'DANGER'    },
}

export default function RiskGauge({ count, risk, message }) {
  const cfg    = RISK_CONFIG[risk] || RISK_CONFIG.SAFE
  const radius = 54
  const circ   = 2 * Math.PI * radius
  const pct    = risk === 'SAFE' ? 0.25 : risk === 'WARNING' ? 0.65 : 1.0

  return (
    <div className="glass-card" style={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      boxShadow: risk !== 'SAFE' ? cfg.shadow : 'none',
      transition: 'box-shadow 0.5s ease'
    }}>
      <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border-glass)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span className="card-label" style={{ marginBottom: 0 }}>Risk Level</span>
        <motion.div
          animate={{ opacity: [1, 0.4, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
          style={{ width: 8, height: 8, borderRadius: '50%', background: cfg.color, boxShadow: `0 0 8px ${cfg.color}` }}
        />
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <div style={{ position: 'relative', filter: risk !== 'SAFE' ? `drop-shadow(0 0 16px ${cfg.color})` : 'none', transition: 'filter 0.5s ease' }}>
          <svg width="150" height="150" style={{ transform: 'rotate(-90deg)' }}>
            <circle cx="75" cy="75" r={radius} fill="none" stroke="var(--border-glass)" strokeWidth="10" />
            <motion.circle
              cx="75" cy="75" r={radius}
              fill="none"
              stroke={cfg.color}
              strokeWidth="10"
              strokeLinecap="round"
              strokeDasharray={circ}
              animate={{ strokeDashoffset: circ * (1 - pct) }}
              transition={{ duration: 1.2, ease: 'easeInOut' }}
            />
          </svg>
          <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            <AnimatePresence mode="wait">
              <motion.div key={count} initial={{ scale: 0.5, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} style={{ fontSize: '2.2rem', fontWeight: 900, color: 'var(--text-primary)', lineHeight: 1, fontFamily: "'Space Grotesk', sans-serif" }}>
                {count}
              </motion.div>
            </AnimatePresence>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: 4 }}>people</div>
          </div>
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={risk}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            style={{ marginTop: 20, padding: '8px 28px', borderRadius: 100, border: `1px solid ${cfg.color}44`, background: `${cfg.color}15`, color: cfg.color, fontSize: '1rem', fontWeight: 900, letterSpacing: 3, boxShadow: `0 0 20px ${cfg.color}30` }}
          >
            {cfg.label}
          </motion.div>
        </AnimatePresence>

        <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem', textAlign: 'center', marginTop: 12, maxWidth: 160, lineHeight: 1.5 }}>
          {message}
        </p>
      </div>
    </div>
  )
}
