import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '../utils/api'

export default function VideoAnalysis({ onResult }) {
  const [file,    setFile]    = useState(null)
  const [loading, setLoading] = useState(false)
  const [result,  setResult]  = useState(null)
  const [progress, setProgress] = useState(0)

  const analyze = async () => {
    if (!file) return
    setLoading(true)
    setProgress(0)
    const interval = setInterval(() => setProgress(p => Math.min(p + 2, 90)), 400)
    try {
      const data = await api.analyzeVideo(file)
      setResult(data)
      onResult(data)
      setProgress(100)
    } catch { alert('Video analysis failed') }
    clearInterval(interval)
    setLoading(false)
  }

  const riskColor  = { SAFE: 'text-safe',    WARNING: 'text-warning',    DANGER: 'text-danger'    }
  const riskBorder = { SAFE: 'border-safe/30', WARNING: 'border-warning/30', DANGER: 'border-danger/30' }
  const riskBg     = { SAFE: 'bg-safe/5',    WARNING: 'bg-warning/5',    DANGER: 'bg-danger/5'    }

  return (
    <div className="card h-full flex flex-col">
      <div className="card-header">
        <span className="card-title">🎥 Video Analysis</span>
      </div>
      <div className="flex-1 p-4 flex flex-col gap-3">

        <div
          onClick={() => document.getElementById('vidInput').click()}
          className="border-2 border-dashed border-border rounded-xl p-6 text-center cursor-pointer hover:border-accent/50 hover:bg-accent/3 transition-all"
        >
          <input
            id="vidInput" type="file" accept="video/*" className="hidden"
            onChange={e => setFile(e.target.files[0])}
          />
          <div className="text-3xl mb-2">{file ? '✅' : '🎬'}</div>
          <div className="text-accent text-sm font-medium">
            {file ? file.name : 'Click to upload video'}
          </div>
          <div className="text-slate-600 text-xs mt-1">MP4, AVI, MOV supported</div>
        </div>

        {loading && (
          <div className="space-y-2">
            <div className="flex justify-between text-xs text-slate-500">
              <span>Processing frames...</span>
              <span>{progress}%</span>
            </div>
            <div className="h-1.5 bg-border rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-accent to-safe rounded-full"
                animate={{ width: `${progress}%` }}
                transition={{ ease: 'easeOut' }}
              />
            </div>
          </div>
        )}

        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={analyze}
          disabled={!file || loading}
          className="btn-primary w-full py-3 rounded-xl font-semibold disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading ? 'Processing...' : 'Analyze Video'}
        </motion.button>

        <AnimatePresence>
          {result && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y:  0 }}
              className={`rounded-xl border p-4 ${riskBg[result.overall_risk]} ${riskBorder[result.overall_risk]}`}
            >
              <div className={`text-xl font-black mb-3 ${riskColor[result.overall_risk]}`}>
                Overall: {result.overall_risk}
              </div>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { label: 'Frames',     val: result.frames_analyzed   },
                  { label: 'Avg People', val: result.avg_person_count  },
                  { label: 'Peak',       val: result.max_person_count  },
                  { label: '⚠ Frames',  val: result.danger_frames, red: true },
                ].map(s => (
                  <div key={s.label} className="bg-black/20 rounded-lg p-2 text-center">
                    <div className={`font-bold text-lg ${s.red ? 'text-danger' : 'text-accent'}`}>{s.val}</div>
                    <div className="text-slate-500 text-xs">{s.label}</div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}