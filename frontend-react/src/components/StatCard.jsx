import { motion } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'

function useCountUp(target, duration = 1000) {
  const [value, setValue] = useState(0)
  const start = useRef(null)
  useEffect(() => {
    start.current = null
    const step = (ts) => {
      if (!start.current) start.current = ts
      const progress = Math.min((ts - start.current) / duration, 1)
      setValue(Math.round(progress * target))
      if (progress < 1) requestAnimationFrame(step)
    }
    requestAnimationFrame(step)
  }, [target, duration])
  return value
}

export default function StatCard({ label, value, sub, color = 'var(--accent-cyan)', delay = 0, decimals = 0 }) {
  const numericValue = parseFloat(value) || 0
  const animated = useCountUp(numericValue)
  const displayValue = decimals > 0 ? numericValue.toFixed(decimals) : animated

  return (
    <motion.div
      className="glass-card"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4 }}
      style={{ padding: '20px 22px', position: 'relative', overflow: 'hidden' }}
    >
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 1, background: `linear-gradient(90deg, transparent, ${color}44, transparent)` }} />
      <div className="card-label">{label}</div>
      <div className="stat-value" style={{ fontSize: 34, color, filter: `drop-shadow(0 0 12px ${color}55)` }}>
        {displayValue}
      </div>
      {sub && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>{sub}</div>}
    </motion.div>
  )
}
