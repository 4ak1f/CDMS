import { useState } from 'react'
import { X, Send } from 'lucide-react'
import { motion } from 'framer-motion'
import api from '../utils/api'

export default function FeedbackWidget({ onClose }) {
  const [predicted, setPredicted] = useState(window.lastPredictedCount || '')
  const [actual, setActual]       = useState('')
  const [scene, setScene]         = useState(() => window.lastSceneType || 'sparse_indoor')
  const [submitted, setSubmitted] = useState(false)
  const [loading, setLoading]     = useState(false)

  const scenes = [
    'sparse_indoor','moderate_indoor','dense_indoor',
    'sparse_outdoor','moderate_outdoor','dense_outdoor'
  ]

  const diff = predicted && actual ? parseInt(actual) - parseInt(predicted) : null

  const handleSubmit = async () => {
    if (!predicted || !actual) return
    setLoading(true)
    try {
      await api.submitFeedback({
        predicted_count:   parseInt(predicted),
        actual_count:      parseInt(actual),
        scene_type:        scene,
        scene_fingerprint: window.lastSceneFingerprint || 'unknown'
      })
      setSubmitted(true)
      setTimeout(() => onClose?.(), 2200)
    } catch(e) {
      alert('Submission failed — check connection')
    } finally {
      setLoading(false)
    }
  }

  if (submitted) return (
    <motion.div
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      style={{ textAlign: 'center', padding: '32px 0' }}
    >
      <div style={{
        width: 56, height: 56, borderRadius: '50%',
        background: 'rgba(5,150,105,0.12)',
        border: '1px solid rgba(5,150,105,0.3)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        margin: '0 auto 16px', fontSize: 24
      }}>✓</div>
      <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--accent-green)', marginBottom: 6 }}>
        Feedback received
      </div>
      <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
        Model will self-calibrate for this scene
      </div>
    </motion.div>
  )

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
        <div>
          <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 16, color: 'var(--text-primary)', marginBottom: 4 }}>
            Correct the Model
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5 }}>
            Your corrections help the AI learn this scene
          </div>
        </div>
        <X size={16} style={{ cursor: 'pointer', color: 'var(--text-muted)', marginTop: 2, flexShrink: 0 }} onClick={onClose} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
        <div>
          <div className="card-label">Model predicted</div>
          <input
            type="number" min="0"
            value={predicted}
            onChange={e => setPredicted(e.target.value)}
            placeholder="e.g. 5"
            className="cdms-input"
          />
        </div>
        <div>
          <div className="card-label">Actual count</div>
          <input
            type="number" min="0"
            value={actual}
            onChange={e => setActual(e.target.value)}
            placeholder="e.g. 3"
            className="cdms-input"
          />
        </div>
      </div>

      <div style={{ marginBottom: 14 }}>
        <div className="card-label">Scene type</div>
        <select value={scene} onChange={e => setScene(e.target.value)} className="cdms-input">
          {scenes.map(s => (
            <option key={s} value={s} style={{ background: 'var(--bg-base)' }}>
              {s.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </option>
          ))}
        </select>
      </div>

      {diff !== null && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            marginBottom: 14, padding: '10px 14px', borderRadius: 10,
            background: diff < 0 ? 'rgba(220,38,38,0.07)' : diff > 0 ? 'rgba(5,150,105,0.07)' : 'rgba(99,102,241,0.07)',
            border: `1px solid ${diff < 0 ? 'rgba(220,38,38,0.2)' : diff > 0 ? 'rgba(5,150,105,0.2)' : 'rgba(99,102,241,0.2)'}`,
            fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5
          }}
        >
          {diff === 0
            ? '✓ Perfect prediction — no adjustment needed'
            : diff < 0
            ? `Model overcounted by ${Math.abs(diff)} — confidence threshold will increase`
            : `Model undercounted by ${diff} — sensitivity will increase`}
        </motion.div>
      )}

      <button
        className="cdms-btn cdms-btn-primary"
        onClick={handleSubmit}
        disabled={!predicted || !actual || loading}
        style={{
          width: '100%',
          opacity: (!predicted || !actual || loading) ? 0.5 : 1,
          cursor: (!predicted || !actual || loading) ? 'not-allowed' : 'pointer'
        }}
      >
        <Send size={13} />
        {loading ? 'Submitting...' : 'Submit Feedback'}
      </button>
    </div>
  )
}
