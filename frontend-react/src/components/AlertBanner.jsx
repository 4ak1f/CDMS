import { motion, AnimatePresence } from 'framer-motion'
import { useEffect } from 'react'

export default function AlertBanner({ alert, onDismiss }) {
  useEffect(() => {
    if (!alert) return
    const t = setTimeout(onDismiss, 6000)
    return () => clearTimeout(t)
  }, [alert, onDismiss])

  return (
    <AnimatePresence>
      {alert && (
        <motion.div
          initial={{ x: 400, opacity: 0 }}
          animate={{ x: 0,   opacity: 1 }}
          exit={{   x: 400, opacity: 0 }}
          transition={{ type: 'spring', damping: 20 }}
          style={{ position: 'fixed', top: 80, right: 24, zIndex: 9999, maxWidth: 360 }}
        >
          <div className="glass-card" style={{ padding: 20, border: '1px solid rgba(255,59,92,0.4)', boxShadow: '0 0 30px rgba(255,59,92,0.2)' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
              <div style={{ fontSize: 24, animation: 'bounce 1s infinite' }}>🚨</div>
              <div style={{ flex: 1 }}>
                <div style={{ color: 'var(--accent-red)', fontWeight: 700, fontSize: 13, marginBottom: 6 }}>
                  DANGER ALERT TRIGGERED
                </div>
                <div style={{ color: 'var(--text-secondary)', fontSize: 12, lineHeight: 1.5 }}>
                  {alert.message}
                </div>
                <div style={{ color: 'var(--text-muted)', fontSize: 11, marginTop: 8 }}>
                  PDF report auto-generated • Email sent
                </div>
              </div>
              <button
                onClick={onDismiss}
                style={{ color: 'var(--text-muted)', background: 'none', border: 'none', fontSize: 20, cursor: 'pointer', lineHeight: 1, padding: 0 }}
              >×</button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
