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
          className="fixed top-20 right-6 z-50 max-w-sm"
        >
          <div className="glass rounded-2xl p-5 border border-danger/40 glow-danger">
            <div className="flex items-start gap-3">
              <div className="text-2xl animate-bounce">🚨</div>
              <div>
                <div className="text-danger font-bold text-sm mb-1">
                  DANGER ALERT TRIGGERED
                </div>
                <div className="text-slate-400 text-xs leading-relaxed">
                  {alert.message}
                </div>
                <div className="text-slate-500 text-xs mt-2">
                  PDF report auto-generated • Email sent
                </div>
              </div>
              <button
                onClick={onDismiss}
                className="text-slate-500 hover:text-white ml-auto text-lg leading-none"
              >×</button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}