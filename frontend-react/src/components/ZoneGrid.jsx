import { motion } from 'framer-motion'

const ZONE_STYLES = {
  SAFE:    'bg-safe/5    border-safe/20    text-safe',
  WARNING: 'bg-warning/5 border-warning/20 text-warning',
  DANGER:  'bg-danger/5  border-danger/20  text-danger',
}

export default function ZoneGrid({ zones }) {
  const defaultZones = Array.from({ length: 9 }, (_, i) => ({
    zone: `Zone ${i + 1}`, risk: 'SAFE', count: 0
  }))

  const displayZones = zones?.length ? zones : defaultZones

  return (
    <div className="card h-full flex flex-col">
      <div className="card-header">
        <span className="card-title">🗺️ Zone Monitor</span>
        <span className="text-xs text-slate-600">3×3 grid</span>
      </div>
      <div className="flex-1 p-4">
        <p className="text-slate-600 text-xs mb-3">Real-time zone density analysis</p>
        <div className="grid grid-cols-3 gap-2">
          {displayZones.map((z, i) => (
            <motion.div
              key={z.zone}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1   }}
              transition={{ delay: i * 0.05 }}
              className={`rounded-xl border p-3 text-center transition-all duration-500 ${ZONE_STYLES[z.risk] || ZONE_STYLES.SAFE}`}
            >
              <div className="text-[10px] opacity-60 mb-1">{z.zone}</div>
              <div className="font-bold text-xs">{z.risk}</div>
              <div className="text-[10px] opacity-70 mt-1">~{z.count}</div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  )
}