import { useRef, useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { useWebSocket } from '../hooks/useWebSocket'

export default function WebcamMonitor({ onData }) {
  const videoRef  = useRef(null)
  const canvasRef = useRef(null)
  const resultRef = useRef(null)
  const streamRef = useRef(null)

  const [active, setActive]   = useState(false)
  const [overlay, setOverlay] = useState(null)

  const handleMessage = useCallback((data) => {
    setOverlay({ count: data.person_count, risk: data.risk_level })
    onData(data)

    if (resultRef.current) {
      const img = new Image()
      img.onload = () => {
        const ctx = resultRef.current.getContext('2d')
        ctx.drawImage(img, 0, 0, 640, 480)
      }
      img.src = 'data:image/jpeg;base64,' + data.frame
    }
  }, [onData])

  const { connected, connect, disconnect } = useWebSocket(handleMessage)

  const start = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 }
      })
      streamRef.current = stream
      videoRef.current.srcObject = stream
      await videoRef.current.play()
      connect(videoRef, canvasRef)
      setActive(true)
    } catch {
      alert('Camera permission denied.')
    }
  }

  const stop = () => {
    disconnect()
    streamRef.current?.getTracks().forEach(t => t.stop())
    setActive(false)
    setOverlay(null)
    const ctx = resultRef.current?.getContext('2d')
    if (ctx) { ctx.fillStyle = '#000'; ctx.fillRect(0, 0, 640, 480) }
  }

  const riskColor = { SAFE: '#00ff88', WARNING: '#ff9500', DANGER: '#ff3b5c' }

  return (
    <div className="card h-full flex flex-col">
      <div className="card-header">
        <span className="card-title">📹 Live Webcam Monitor</span>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${active ? 'bg-safe animate-pulse' : 'bg-slate-600'}`} />
          <span className="text-xs text-slate-500">{active ? 'Live' : 'Offline'}</span>
        </div>
      </div>

      <div className="flex-1 p-4 flex flex-col gap-3">
        {/* Hidden video element for capture */}
        <video ref={videoRef} className="hidden" muted playsInline />
        <canvas ref={canvasRef} width="640" height="480" className="hidden" />

        {/* Display canvas */}
        <div className="relative rounded-xl overflow-hidden bg-black flex-1 min-h-[240px]">
          <canvas
            ref={resultRef}
            width="640"
            height="480"
            className="w-full h-full object-cover"
          />

          {!active && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div className="text-4xl mb-3 opacity-30">📷</div>
                <div className="text-slate-600 text-sm">Camera inactive</div>
              </div>
            </div>
          )}

          {overlay && active && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="absolute top-3 right-3 glass rounded-xl p-3 text-xs"
            >
              <div className="font-bold text-white">People: {overlay.count}</div>
              <div style={{ color: riskColor[overlay.risk] }} className="font-bold">
                {overlay.risk}
              </div>
            </motion.div>
          )}

          {active && (
            <div className="absolute top-3 left-3">
              <div className="flex items-center gap-1.5 bg-danger/20 border border-danger/40 rounded-full px-2 py-1">
                <div className="w-1.5 h-1.5 rounded-full bg-danger animate-pulse" />
                <span className="text-danger text-[10px] font-bold">REC</span>
              </div>
            </div>
          )}
        </div>

        <div className="flex gap-2">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={start}
            disabled={active}
            className="flex-1 btn-primary py-2.5 rounded-xl text-sm font-semibold disabled:opacity-40 disabled:cursor-not-allowed"
          >
            ▶ Start Camera
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={stop}
            disabled={!active}
            className="flex-1 bg-danger/20 border border-danger/30 text-danger py-2.5 rounded-xl text-sm font-semibold disabled:opacity-40 disabled:cursor-not-allowed hover:bg-danger/30 transition-colors"
          >
            ⏹ Stop
          </motion.button>
        </div>
      </div>
    </div>
  )
}