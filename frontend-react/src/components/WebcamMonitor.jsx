import { useRef, useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { useWebSocket } from '../hooks/useWebSocket'

export default function WebcamMonitor({ onData, onFps }) {
  const videoRef  = useRef(null)
  const canvasRef = useRef(null)
  const resultRef = useRef(null)
  const streamRef = useRef(null)

  const [active,   setActive]  = useState(false)
  const [overlay,  setOverlay] = useState(null)
  const [wsError,  setWsError] = useState(null)

  const handleMessage = useCallback((data) => {
    setOverlay({ count: data.person_count, risk: data.risk_level })
    if (onData) onData(data)

    if (resultRef.current) {
      const img = new Image()
      img.onload = () => {
        const ctx = resultRef.current.getContext('2d')
        ctx.drawImage(img, 0, 0, 640, 480)
      }
      img.src = 'data:image/jpeg;base64,' + data.frame
    }
  }, [onData])

  const { connect, disconnect } = useWebSocket(handleMessage)

  const start = async () => {
    setWsError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: 'user' }
      })
      streamRef.current = stream
      videoRef.current.srcObject = stream
      await videoRef.current.play()
      connect(videoRef, canvasRef)
      setActive(true)
    } catch(e) {
      if (e.name === 'NotAllowedError') {
        setWsError('Camera permission denied. Allow camera access in browser settings.')
      } else if (e.name === 'NotFoundError') {
        setWsError('No camera found. Check camera connection.')
      } else {
        setWsError(`Camera error: ${e.message}`)
      }
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

  const riskColor = { SAFE: 'var(--accent-green)', WARNING: 'var(--accent-amber)', DANGER: 'var(--accent-red)' }

  return (
    <div className="glass-card" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border-glass)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span className="card-label" style={{ marginBottom: 0 }}>Live Webcam Monitor</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 7, height: 7, borderRadius: '50%', background: active ? 'var(--accent-green)' : 'var(--text-muted)', boxShadow: active ? '0 0 6px var(--accent-green)' : 'none' }} />
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{active ? 'Live' : 'Offline'}</span>
        </div>
      </div>

      <div style={{ flex: 1, padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
        <video ref={videoRef} style={{ display: 'none' }} muted playsInline />
        <canvas ref={canvasRef} width="640" height="480" style={{ display: 'none' }} />

        <div style={{ position: 'relative', borderRadius: 12, overflow: 'hidden', background: '#000', flex: 1, minHeight: 240 }}>
          <canvas ref={resultRef} width="640" height="480" style={{ width: '100%', borderRadius: 12, display: 'block' }} />

          {!active && (
            <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 40, marginBottom: 12, opacity: 0.3 }}>📷</div>
                <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Camera inactive</div>
              </div>
            </div>
          )}

          {overlay && active && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              style={{
                position: 'absolute', top: 12, left: 12,
                padding: '6px 14px', borderRadius: 100,
                background: 'rgba(0,0,0,0.6)',
                backdropFilter: 'blur(8px)',
                border: '1px solid rgba(255,255,255,0.15)',
                fontSize: 13, fontWeight: 700,
                color: riskColor[overlay.risk] || 'var(--accent-green)',
                display: 'flex', alignItems: 'center', gap: 8,
              }}
            >
              <span>{overlay.count} people</span>
              <span style={{ opacity: 0.6, fontWeight: 400, fontSize: 11 }}>|</span>
              <span>{overlay.risk}</span>
            </motion.div>
          )}

          {active && (
            <div style={{ position: 'absolute', top: 12, left: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'rgba(255,59,92,0.15)', border: '1px solid rgba(255,59,92,0.3)', borderRadius: 100, padding: '4px 10px' }}>
                <motion.div animate={{ opacity: [1, 0.3, 1] }} transition={{ duration: 1, repeat: Infinity }} style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent-red)' }} />
                <span style={{ fontSize: 10, fontWeight: 800, color: 'var(--accent-red)', letterSpacing: 1 }}>REC</span>
              </div>
            </div>
          )}
        </div>

        {wsError && (
          <div style={{ padding: '10px 14px', borderRadius: 10,
            background: 'rgba(220,38,38,0.08)', border: '1px solid rgba(220,38,38,0.2)',
            fontSize: 12, color: 'var(--accent-red)' }}>
            {wsError}
          </div>
        )}

        <div style={{ display: 'flex', gap: 10 }}>
          <motion.button
            whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
            onClick={start} disabled={active}
            style={{ flex: 1, padding: '10px', borderRadius: 12, background: 'var(--accent-cyan)', color: '#000', fontWeight: 700, fontSize: 13, border: 'none', cursor: active ? 'not-allowed' : 'pointer', opacity: active ? 0.4 : 1 }}
          >
            ▶ Start Camera
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
            onClick={stop} disabled={!active}
            style={{ flex: 1, padding: '10px', borderRadius: 12, background: 'rgba(255,59,92,0.12)', border: '1px solid rgba(255,59,92,0.3)', color: 'var(--accent-red)', fontWeight: 700, fontSize: 13, cursor: !active ? 'not-allowed' : 'pointer', opacity: !active ? 0.4 : 1 }}
          >
            ⏹ Stop
          </motion.button>
        </div>
      </div>
    </div>
  )
}
