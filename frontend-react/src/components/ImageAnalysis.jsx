import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '../utils/api'

export default function ImageAnalysis({ onResult }) {
  const [file,    setFile]    = useState(null)
  const [loading, setLoading] = useState(false)
  const [result,  setResult]  = useState(null)
  const [dragging, setDragging] = useState(false)

  const analyze = async () => {
    if (!file) return
    setLoading(true)
    try {
      const data = await api.analyzeImage(file)
      setResult(data)
      onResult(data)
    } catch { alert('Analysis failed') }
    setLoading(false)
  }

  const onDrop = useCallback((e) => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f?.type.startsWith('image/')) setFile(f)
  }, [])

  const riskColor = { SAFE: 'text-safe', WARNING: 'text-warning', DANGER: 'text-danger' }
  const riskBorder = { SAFE: 'border-safe/30', WARNING: 'border-warning/30', DANGER: 'border-danger/30' }
  const riskBg = { SAFE: 'bg-safe/5', WARNING: 'bg-warning/5', DANGER: 'bg-danger/5' }

  return (
    <div className="card h-full flex flex-col">
      <div className="card-header">
        <span className="card-title">📷 Image Analysis</span>
      </div>
      <div className="flex-1 p-4 flex flex-col gap-3">

        <div
          onDrop={onDrop}
          onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onClick={() => document.getElementById('imgInput').click()}
          className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all
            ${dragging ? 'border-accent bg-accent/5' : 'border-border hover:border-accent/50 hover:bg-accent/3'}`}
        >
          <input
            id="imgInput" type="file" accept="image/*" className="hidden"
            onChange={e => setFile(e.target.files[0])}
          />
          <div className="text-3xl mb-2">{file ? '✅' : '🖼️'}</div>
          <div className="text-accent text-sm font-medium">
            {file ? file.name : 'Drop image or click to upload'}
          </div>
          <div className="text-slate-600 text-xs mt-1">JPG, PNG supported</div>
        </div>

        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={analyze}
          disabled={!file || loading}
          className="btn-primary w-full py-3 rounded-xl font-semibold disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <div className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
              Analyzing...
            </span>
          ) : 'Analyze Image'}
        </motion.button>

        <AnimatePresence>
          {result && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y:  0 }}
              className={`rounded-xl border p-4 ${riskBg[result.risk_level]} ${riskBorder[result.risk_level]}`}
            >
              <div className={`text-xl font-black mb-2 ${riskColor[result.risk_level]}`}>
                {result.risk_level}
              </div>
              <div className="grid grid-cols-2 gap-2 mb-3">
                <div className="bg-black/20 rounded-lg p-2 text-center">
                  <div className="text-accent font-bold text-lg">{result.person_count}</div>
                  <div className="text-slate-500 text-xs">People</div>
                </div>
                <div className="bg-black/20 rounded-lg p-2 text-center">
                  <div className="text-accent font-bold text-lg">{result.density_score}</div>
                  <div className="text-slate-500 text-xs">Density</div>
                </div>
              </div>
              {result.annotated_image && (
                <img
                  src={`data:image/jpeg;base64,${result.annotated_image}`}
                  alt="Result"
                  className="w-full rounded-lg"
                />
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}