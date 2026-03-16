import { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import ParticleBackground from './ParticleBackground'
import Header             from './Header'
import StatsBar           from './StatsBar'
import WebcamMonitor      from './WebcamMonitor'
import RiskGauge          from './RiskGauge'
import ZoneGrid           from './ZoneGrid'
import ImageAnalysis      from './ImageAnalysis'
import VideoAnalysis      from './VideoAnalysis'
import CrowdChart         from './CrowdChart'
import HistoryTable       from './HistoryTable'
import AlertBanner        from './AlertBanner'
import { useStats }       from '../hooks/useStats'

export default function Dashboard() {
  const { stats, refresh } = useStats()
  const [isLive,  setIsLive]  = useState(false)
  const [risk,    setRisk]    = useState('SAFE')
  const [count,   setCount]   = useState(0)
  const [message, setMessage] = useState('System ready. Start camera or upload media.')
  const [zones,   setZones]   = useState([])
  const [alert,   setAlert]   = useState(null)

  const handleData = useCallback((data) => {
    if (data.risk_level) setRisk(data.risk_level)
    if (data.person_count !== undefined) setCount(data.person_count)
    if (data.message)    setMessage(data.message)
    if (data.zones)      setZones(data.zones)
    if (data.alert || data.risk_level === 'DANGER') {
      setAlert({ message: data.message || 'Critical crowd density detected!' })
    }
    refresh()
  }, [refresh])

  const handleWebcamData = useCallback((data) => {
    setIsLive(true)
    handleData(data)
  }, [handleData])

  return (
    <div className="min-h-screen relative scanline bg-grid-pattern bg-grid"
  style={{ backgroundColor: '#080c14' }}>
      <ParticleBackground />

      <div className="relative z-10">
        <Header isLive={isLive} />
        <StatsBar stats={stats} />

        <main className="max-w-[1600px] mx-auto px-6 py-6 space-y-5">

          {/* Row 1: Webcam + Risk + Zones */}
<div className="grid grid-cols-4 gap-5">
  <motion.div
    className="col-span-2"
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y:  0 }}
    transition={{ delay: 0.1 }}
  >
    <WebcamMonitor onData={handleWebcamData} />
  </motion.div>

  <motion.div
    className="col-span-1"
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y:  0 }}
    transition={{ delay: 0.2 }}
  >
    <RiskGauge count={count} risk={risk} message={message} />
  </motion.div>

  <motion.div
    className="col-span-1"
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y:  0 }}
    transition={{ delay: 0.3 }}
  >
    <ZoneGrid zones={zones} />
  </motion.div>
</div>

          {/* Row 2: Image + Video + Chart */}
          <div className="grid grid-cols-3 gap-5">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y:  0 }}
              transition={{ delay: 0.4 }}
            >
              <ImageAnalysis onResult={handleData} />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y:  0 }}
              transition={{ delay: 0.5 }}
            >
              <VideoAnalysis onResult={handleData} />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y:  0 }}
              transition={{ delay: 0.6 }}
            >
              <CrowdChart stats={stats} onRefresh={refresh} />
            </motion.div>
          </div>

          {/* Row 3: History */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y:  0 }}
            transition={{ delay: 0.7 }}
          >
            <HistoryTable />
          </motion.div>

        </main>
      </div>

      <AlertBanner alert={alert} onDismiss={() => setAlert(null)} />
    </div>
  )
}