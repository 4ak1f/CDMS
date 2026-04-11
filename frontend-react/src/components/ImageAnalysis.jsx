import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '../utils/api'
import FeedbackWidget from './FeedbackWidget'

export default function ImageAnalysis({ onResult }) {
  const [file,         setFile]         = useState(null)
  const [loading,      setLoading]      = useState(false)
  const [result,       setResult]       = useState(null)
  const [dragging,     setDragging]     = useState(false)
  const [showFeedback, setShowFeedback] = useState(false)

  const convertHeicIfNeeded = async (f) => {
    if (!f) return f
    const name = f.name.toLowerCase()
    if (!name.endsWith('.heic') && !name.endsWith('.heif')) return f
    try {
      const script = document.createElement('script')
      script.src = 'https://cdn.jsdelivr.net/npm/heic2any@0.0.4/dist/heic2any.min.js'
      document.head.appendChild(script)
      await new Promise(resolve => { script.onload = resolve; setTimeout(resolve, 3000) })
      const blob = await window.heic2any({ blob: f, toType: 'image/jpeg', quality: 0.9 })
      const converted = Array.isArray(blob) ? blob[0] : blob
      return new File([converted], name.replace(/\.heic$/i, '.jpg').replace(/\.heif$/i, '.jpg'), { type: 'image/jpeg' })
    } catch(e) {
      console.warn('HEIC conversion failed:', e)
      return f
    }
  }

  const handleFileSelect = async (f) => {
    if (!f) return
    const converted = await convertHeicIfNeeded(f)
    setFile(converted)
  }

  const analyze = async () => {
    if (!file) return
    setLoading(true)
    try {
      const fileToSend = await convertHeicIfNeeded(file)
      const data = await api.analyzeImage(fileToSend)
      setResult(data)
      if (onResult) onResult(data)
      window.lastPredictedCount    = data.person_count
      window.lastSceneFingerprint  = data.scene_fingerprint || 'unknown'
      window.lastSceneType         = data.scene_type || 'unknown'
      setShowFeedback(true)
    } catch { alert('Analysis failed') }
    setLoading(false)
  }

  const onDrop = useCallback((e) => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFileSelect(f)
  }, [])

  const riskColor = {
    SAFE:        'var(--accent-green)',
    WARNING:     'var(--accent-amber)',
    DANGER:      'var(--accent-red)',
    OVERCROWDED: 'var(--accent-red)',
  }

  const riskBg = {
    SAFE:        'rgba(0,255,136,0.1)',
    WARNING:     'rgba(245,158,11,0.12)',
    DANGER:      'rgba(255,59,92,0.12)',
    OVERCROWDED: 'rgba(255,59,92,0.12)',
  }

  const riskBorder = {
    SAFE:        'rgba(0,255,136,0.25)',
    WARNING:     'rgba(245,158,11,0.3)',
    DANGER:      'rgba(255,59,92,0.3)',
    OVERCROWDED: 'rgba(255,59,92,0.3)',
  }

  return (
    <div className="glass-card" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border-glass)' }}>
        <span className="card-label" style={{ marginBottom: 0 }}>Image Analysis</span>
      </div>
      <div style={{ flex: 1, padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div
          onDrop={onDrop}
          onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onClick={() => document.getElementById('imgInput').click()}
          style={{
            border: `2px dashed ${dragging ? 'var(--accent-purple)' : 'var(--border-glass)'}`,
            borderRadius: 12, padding: 24, textAlign: 'center', cursor: 'pointer',
            background: dragging ? 'rgba(99,102,241,0.05)' : 'transparent',
            transition: 'all 0.3s ease'
          }}
        >
          <input
            id="imgInput"
            type="file"
            accept="image/*,.heic,.heif,image/heic,image/heif"
            style={{ display: 'none' }}
            onClick={e => { e.target.value = '' }}
            onChange={e => handleFileSelect(e.target.files[0])}
          />
          <div style={{ fontSize: 28, marginBottom: 8 }}>{file ? '✅' : '🖼️'}</div>
          <div style={{ fontSize: 13, color: 'var(--accent-cyan)', fontWeight: 500 }}>
            {file ? file.name : 'Drop image or click to upload'}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>JPG, PNG, HEIC supported</div>
        </div>

        <motion.button
          whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
          onClick={analyze} disabled={!file || loading}
          style={{ width: '100%', padding: '12px', borderRadius: 12, background: 'var(--accent-cyan)', color: '#000', fontWeight: 700, fontSize: 13, border: 'none', cursor: (!file || loading) ? 'not-allowed' : 'pointer', opacity: (!file || loading) ? 0.4 : 1 }}
        >
          {loading ? (
            <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
              <div style={{ width: 14, height: 14, border: '2px solid rgba(0,0,0,0.3)', borderTopColor: '#000', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
              Analyzing...
            </span>
          ) : 'Analyze Image'}
        </motion.button>

        <AnimatePresence>
          {result && (
            <motion.div
              initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
              style={{ borderRadius: 12, border: `1px solid ${riskColor[result.risk_level]}33`, background: `${riskColor[result.risk_level]}0d`, padding: 16 }}
            >
              {/* Risk badge — compact, not giant text */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                <span style={{
                  fontSize: 11, fontWeight: 700, padding: '3px 12px',
                  borderRadius: 100, letterSpacing: 1.5, textTransform: 'uppercase',
                  background: riskBg[result.risk_level]    || riskBg.SAFE,
                  color:      riskColor[result.risk_level] || riskColor.SAFE,
                  border:     `1px solid ${riskBorder[result.risk_level] || riskBorder.SAFE}`,
                }}>
                  {result.risk_level}
                </span>
                {result.scene_type && (
                  <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{result.scene_type}</span>
                )}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 12 }}>
                <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: 8, padding: '8px', textAlign: 'center' }}>
                  <div style={{ color: 'var(--accent-cyan)', fontWeight: 700, fontSize: 18 }}>{result.person_count}</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>People</div>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: 8, padding: '8px', textAlign: 'center' }}>
                  <div style={{ color: 'var(--accent-cyan)', fontWeight: 700, fontSize: 18 }}>{result.density_score}</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>Density</div>
                </div>
              </div>
              {result.annotated_image && (
                <img src={`data:image/jpeg;base64,${result.annotated_image}`} alt="Result" style={{ width: '100%', borderRadius: 8 }} />
              )}
              {result.scene_type && result.scene_type.includes('dense') && result.person_count < 100 && (
                <div style={{ fontSize: 11, color: 'var(--accent-amber)', marginTop: 4, padding: '6px 10px',
                  background: 'rgba(245,158,11,0.08)', borderRadius: 8, border: '1px solid rgba(245,158,11,0.2)' }}>
                  Ultra-dense crowd detected. Try switching to Dense or Mega mode for better accuracy.
                  Submit feedback after analysis to help the model calibrate.
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {result && (
          <button
            className="cdms-btn"
            onClick={analyze}
            disabled={loading}
            style={{ marginTop: 8, width: '100%', fontSize: 12 }}
          >
            {loading ? 'Analyzing...' : '🔄 Re-analyze'}
          </button>
        )}
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
