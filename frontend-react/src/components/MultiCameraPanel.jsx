import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, Camera, Copy, RefreshCw } from 'lucide-react'

function QRCode({ url, size = 120 }) {
  const [src, setSrc] = useState(null)
  useEffect(() => {
    setSrc(`https://api.qrserver.com/v1/create-qr-code/?size=${size}x${size}&data=${encodeURIComponent(url)}&bgcolor=05070f&color=ffffff&margin=2`)
  }, [url, size])
  return src ? <img src={src} alt="QR" style={{ borderRadius: 8, width: size, height: size }} /> : null
}

export default function MultiCameraPanel({ onAggregateUpdate }) {
  const [session,   setSession]   = useState(null)
  const [cameras,   setCameras]   = useState([])
  const [aggregate, setAggregate] = useState({})
  const [creating,     setCreating]     = useState(false)
  const [copied,       setCopied]       = useState(false)
  const [publicUrl,    setPublicUrl]    = useState('')
  const [ngrokStatus,  setNgrokStatus]  = useState('checking')

  const fetchSession = useCallback(async () => {
    try {
      const data = await fetch('/session/current').then(r => r.json())
      if (data.active) {
        setSession({ code: data.code, join_url: data.join_url })
        setCameras(data.cameras || [])
        setAggregate(data)
        onAggregateUpdate?.(data)
      }
    } catch(e) {}
  }, [onAggregateUpdate])

  useEffect(() => {
    fetchSession()
    // Fetch ngrok public URL
    fetch('/ngrok/url').then(r => r.json()).then(d => {
      if (d.url) {
        setPublicUrl(d.url)
        setNgrokStatus('connected')
      } else {
        setNgrokStatus('offline')
      }
    }).catch(() => setNgrokStatus('offline'))
  }, [fetchSession])

  useEffect(() => {
    if (!session) return
    const interval = setInterval(fetchSession, 3000)
    return () => clearInterval(interval)
  }, [session, fetchSession])

  const createSession = async () => {
    setCreating(true)
    try {
      const data = await fetch('/session/create', { method: 'POST' }).then(r => r.json())
      setSession(data)
      fetchSession()
    } catch(e) {
      alert('Failed to create session')
    } finally {
      setCreating(false)
    }
  }

  const getJoinUrl = () => {
    if (publicUrl) return `${publicUrl}/camera/${session?.code}`
    return `${window.location.protocol}//${window.location.hostname}:8000/camera/${session?.code}`
  }

  const copyLink = () => {
    navigator.clipboard.writeText(getJoinUrl())
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const riskColor = (r) => r === 'DANGER' ? 'var(--accent-red)' : r === 'WARNING' ? 'var(--accent-amber)' : 'var(--accent-green)'

  if (!session) return (
    <div className="glass-card" style={{ padding: 24, height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 16, textAlign: 'center' }}>
      <div style={{ width: 56, height: 56, borderRadius: '50%', background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Camera size={24} style={{ color: 'var(--accent-purple)' }} />
      </div>
      <div>
        <div className="section-heading" style={{ marginBottom: 6 }}>Multi-Camera</div>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.6 }}>
          Create a session to connect phones as cameras
        </div>
      </div>
      <motion.button
        whileTap={{ scale: 0.96 }}
        onClick={createSession}
        disabled={creating}
        className="cdms-btn cdms-btn-primary"
        style={{ width: '100%' }}
      >
        <Plus size={14} />
        {creating ? 'Creating...' : 'Start Camera Session'}
      </motion.button>
    </div>
  )

  const joinUrl = getJoinUrl()

  return (
    <div className="glass-card" style={{ padding: 20, height: '100%', display: 'flex', flexDirection: 'column', gap: 14, overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div className="card-label" style={{ margin: 0 }}>Multi-Camera</div>
          {ngrokStatus === 'connected' ? (
            <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 100, background: 'rgba(0,255,163,0.1)', border: '1px solid rgba(0,255,163,0.25)', color: 'var(--accent-green)', fontWeight: 700, letterSpacing: 0.5 }}>🌐 PUBLIC</span>
          ) : ngrokStatus === 'offline' ? (
            <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 100, background: 'rgba(251,191,36,0.1)', border: '1px solid rgba(251,191,36,0.25)', color: 'var(--accent-amber)', fontWeight: 700, letterSpacing: 0.5 }}>⚠ LOCAL ONLY</span>
          ) : null}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'monospace' }}>{session.code}</span>
          <motion.button whileTap={{ scale: 0.9 }} onClick={fetchSession} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 2 }}>
            <RefreshCw size={13} />
          </motion.button>
        </div>
      </div>

      {/* Aggregate stats */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        <div style={{ padding: '10px 12px', background: 'var(--bg-glass)', borderRadius: 10, border: '1px solid var(--border-glass)' }}>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: 2, textTransform: 'uppercase', marginBottom: 4 }}>Total People</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--accent-cyan)', fontFamily: "'Space Grotesk', sans-serif" }}>{aggregate.total_people || 0}</div>
        </div>
        <div style={{ padding: '10px 12px', background: 'var(--bg-glass)', borderRadius: 10, border: '1px solid var(--border-glass)' }}>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: 2, textTransform: 'uppercase', marginBottom: 4 }}>Cameras</div>
          <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--accent-purple)', fontFamily: "'Space Grotesk', sans-serif" }}>{cameras.filter(c => c.active).length}</div>
        </div>
      </div>

      {/* QR + link */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', padding: '12px', background: 'var(--bg-glass)', borderRadius: 12, border: '1px solid var(--border-glass)' }}>
        <QRCode url={joinUrl} size={80} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>Scan to join as camera</div>
          <div style={{ fontSize: 10, color: 'var(--text-secondary)', fontFamily: 'monospace', wordBreak: 'break-all', marginBottom: 8, lineHeight: 1.4 }}>
            {joinUrl.length > 40 ? joinUrl.slice(0, 40) + '...' : joinUrl}
          </div>
          <motion.button
            whileTap={{ scale: 0.95 }}
            onClick={copyLink}
            className="cdms-btn"
            style={{ fontSize: 11, padding: '5px 12px', width: '100%' }}
          >
            <Copy size={11} />
            {copied ? 'Copied!' : 'Copy Link'}
          </motion.button>
        </div>
      </div>

      {/* Camera list */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
        {cameras.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '16px 0', fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.7 }}>
            No cameras connected yet
            {ngrokStatus === 'connected' ? (
              <div style={{ fontSize: 11, marginTop: 6 }}>
                Scan the QR code on any phone —<br />works on any network
              </div>
            ) : ngrokStatus === 'offline' ? (
              <div style={{ fontSize: 11, marginTop: 6, color: 'var(--accent-amber)' }}>
                Phone must be on the same WiFi.<br />Run <code style={{ fontSize: 10 }}>start.sh</code> for public access.
              </div>
            ) : (
              <div style={{ fontSize: 11, marginTop: 6 }}>Share the link or QR code above</div>
            )}
          </div>
        ) : (
          <AnimatePresence>
            {cameras.map((cam, i) => (
              <motion.div
                key={cam.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                transition={{ delay: i * 0.05 }}
                style={{
                  padding: '10px 12px',
                  borderRadius: 10,
                  background: cam.active ? 'var(--bg-glass)' : 'transparent',
                  border: `1px solid ${cam.active ? 'var(--border-glass)' : 'transparent'}`,
                  opacity: cam.active ? 1 : 0.4,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
                    <div style={{ width: 7, height: 7, borderRadius: '50%', background: cam.active ? 'var(--accent-green)' : 'var(--text-muted)', flexShrink: 0, boxShadow: cam.active ? '0 0 6px var(--accent-green)' : 'none' }} />
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{cam.name}</div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                    <span style={{ fontSize: 16, fontWeight: 800, color: riskColor(cam.risk_level), fontFamily: "'Space Grotesk', sans-serif" }}>{cam.person_count}</span>
                    <span style={{ fontSize: 10, padding: '2px 7px', borderRadius: 100, fontWeight: 600, background: `${riskColor(cam.risk_level)}18`, color: riskColor(cam.risk_level) }}>{cam.risk_level}</span>
                  </div>
                </div>
                {cam.active && cam.scene_type && cam.scene_type !== 'unknown' && (
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4, paddingLeft: 15 }}>{cam.scene_type}</div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>
    </div>
  )
}
