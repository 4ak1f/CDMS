import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '../utils/api'
import FeedbackWidget from './FeedbackWidget'

export default function VideoAnalysis({ onResult }) {
  const [file,         setFile]         = useState(null)
  const [loading,      setLoading]      = useState(false)
  const [result,       setResult]       = useState(null)
  const [progress,     setProgress]     = useState(0)
  const [showFeedback, setShowFeedback] = useState(false)

  const analyze = async () => {
    if (!file) return
    setLoading(true)
    setProgress(0)
    const interval = setInterval(() => setProgress(p => Math.min(p + 2, 90)), 400)
    try {
      const data = await api.analyzeVideo(file)
      setResult(data)
      if (onResult) onResult(data)
      setProgress(100)
      window.lastPredictedCount   = data.max_person_count
      window.lastSceneFingerprint = data.scene_fingerprint || 'unknown'
      window.lastSceneType        = data.scene_type || 'unknown'
      setShowFeedback(true)
    } catch { alert('Video analysis failed') }
    clearInterval(interval)
    setLoading(false)
  }

  const riskColor = { SAFE: 'var(--accent-green)', WARNING: 'var(--accent-amber)', DANGER: 'var(--accent-red)', OVERCROWDED: 'var(--accent-red)' }

  return (
    <div className="glass-card" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border-glass)' }}>
        <span className="card-label" style={{ marginBottom: 0 }}>Video Analysis</span>
      </div>
      <div style={{ flex: 1, padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div
          onClick={() => document.getElementById('vidInput').click()}
          style={{ border: '2px dashed var(--border-glass)', borderRadius: 12, padding: 24, textAlign: 'center', cursor: 'pointer', transition: 'all 0.3s ease' }}
        >
          <input
            id="vidInput"
            type="file"
            accept="video/*"
            style={{ display: 'none' }}
            onClick={e => { e.target.value = '' }}
            onChange={e => setFile(e.target.files[0])}
          />
          <div style={{ fontSize: 28, marginBottom: 8 }}>{file ? '✅' : '🎬'}</div>
          <div style={{ fontSize: 13, color: 'var(--accent-cyan)', fontWeight: 500 }}>
            {file ? file.name : 'Click to upload video'}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>MP4, AVI, MOV supported</div>
        </div>

        {loading && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)' }}>
              <span>Processing frames...</span><span>{progress}%</span>
            </div>
            <div style={{ height: 4, borderRadius: 2, background: 'var(--border-glass)', overflow: 'hidden' }}>
              <motion.div
                animate={{ width: `${progress}%` }}
                transition={{ ease: 'easeOut' }}
                style={{ height: '100%', background: 'linear-gradient(90deg, var(--accent-cyan), var(--accent-green))', borderRadius: 2 }}
              />
            </div>
          </div>
        )}

        <motion.button
          whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
          onClick={analyze} disabled={!file || loading}
          style={{ width: '100%', padding: '12px', borderRadius: 12, background: 'var(--accent-cyan)', color: '#000', fontWeight: 700, fontSize: 13, border: 'none', cursor: (!file || loading) ? 'not-allowed' : 'pointer', opacity: (!file || loading) ? 0.4 : 1 }}
        >
          {loading ? 'Processing...' : 'Analyze Video'}
        </motion.button>

        <AnimatePresence>
          {result && (
            <motion.div
              initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
              style={{ borderRadius: 12, border: `1px solid ${riskColor[result.overall_risk]}33`, background: `${riskColor[result.overall_risk]}0d`, padding: 16 }}
            >
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: 12 }}>
                <span style={{
                  fontSize: 11, fontWeight: 700, padding: '3px 12px',
                  borderRadius: 100, letterSpacing: 1.5, textTransform: 'uppercase',
                  background: result.overall_risk === 'SAFE' ? 'rgba(0,255,136,0.1)' : result.overall_risk === 'WARNING' ? 'rgba(245,158,11,0.12)' : 'rgba(255,59,92,0.12)',
                  color: riskColor[result.overall_risk] || riskColor.SAFE,
                  border: `1px solid ${result.overall_risk === 'SAFE' ? 'rgba(0,255,136,0.25)' : result.overall_risk === 'WARNING' ? 'rgba(245,158,11,0.3)' : 'rgba(255,59,92,0.3)'}`,
                }}>
                  {result.overall_risk}
                </span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                {[
                  { label: 'Frames',     val: result.frames_analyzed   },
                  { label: 'Avg People', val: result.avg_person_count  },
                  { label: 'Peak',       val: result.max_person_count  },
                  { label: '⚠ Frames',  val: result.danger_frames, red: true },
                ].map(s => (
                  <div key={s.label} style={{ background: 'rgba(0,0,0,0.2)', borderRadius: 8, padding: '8px', textAlign: 'center' }}>
                    <div style={{ fontWeight: 700, fontSize: 18, color: s.red ? 'var(--accent-red)' : 'var(--accent-cyan)' }}>{s.val}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{s.label}</div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <AnimatePresence>
        {showFeedback && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ duration: 0.25 }}
            style={{
              position: 'fixed', bottom: 28, right: 28,
              width: 360, zIndex: 150,
              borderRadius: 20,
              background: 'var(--bg-glass-card)',
              border: '1px solid var(--border-glass)',
              backdropFilter: 'blur(24px)',
              WebkitBackdropFilter: 'blur(24px)',
              padding: 24,
              boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
            }}
          >
            <FeedbackWidget onClose={() => setShowFeedback(false)} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
