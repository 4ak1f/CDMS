import { useState, useEffect } from 'react'
import PageTransition from '../components/PageTransition'
import { api } from '../utils/api'
import { useAuth } from '../context/AuthContext'

const PRESETS = {
  library:   { warning: 20,   danger: 40   },
  street:    { warning: 100,  danger: 200  },
  concert:   { warning: 500,  danger: 1000 },
  stadium:   { warning: 1000, danger: 3000 },
  station:   { warning: 200,  danger: 400  },
  religious: { warning: 300,  danger: 800  },
}
const MODES = ['auto','sparse','moderate','dense','mega']
const INTERVAL_OPTIONS = [
  { label: '1 min',  value: 1  },
  { label: '5 min',  value: 5  },
  { label: '15 min', value: 15 },
  { label: '30 min', value: 30 },
  { label: '1 hr',   value: 60 },
]

function SMSConfig({ token }) {
  const [status,  setStatus]  = useState(null)
  const [config,  setConfig]  = useState({ TWILIO_SID: '', TWILIO_TOKEN: '', TWILIO_FROM: '', TWILIO_TO: '' })
  const [saving,  setSaving]  = useState(false)
  const [testing, setTesting] = useState(false)
  const [msg,     setMsg]     = useState('')

  useEffect(() => {
    fetch('/sms/status').then(r => r.json()).then(setStatus).catch(() => {})
  }, [])

  const save = async () => {
    setSaving(true)
    const res = await fetch('/sms/configure', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(config)
    }).then(r => r.json())
    setMsg(res.message || res.error || 'Saved')
    setSaving(false)
  }

  const test = async () => {
    setTesting(true)
    const res = await fetch('/sms/test', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` }
    }).then(r => r.json())
    setMsg(res.sent ? `✅ SMS sent!` : `❌ ${res.reason}`)
    setTesting(false)
  }

  return (
    <div className="glass-card" style={{ padding: 20 }}>
      <div className="card-label">SMS Alerts (Twilio)</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <div style={{ width: 8, height: 8, borderRadius: '50%',
          background: status?.enabled ? 'var(--accent-green)' : 'var(--text-muted)',
          boxShadow: status?.enabled ? '0 0 6px var(--accent-green)' : 'none' }} />
        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          {status?.enabled ? 'Configured and active' : 'Not configured'}
        </span>
      </div>

      {!status?.enabled && (
        <div style={{ marginBottom: 14, padding: '10px 14px', borderRadius: 10,
          background: 'rgba(245,158,11,0.07)', border: '1px solid rgba(245,158,11,0.2)',
          fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
          Sign up free at <strong>twilio.com</strong> → get Account SID, Auth Token, and a phone number.
          Paste them below.
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 14 }}>
        {['TWILIO_SID', 'TWILIO_TOKEN', 'TWILIO_FROM', 'TWILIO_TO'].map(key => (
          <div key={key}>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 4,
              letterSpacing: 1, textTransform: 'uppercase' }}>
              {key.replace('TWILIO_', '').replace('_', ' ')}
              {key === 'TWILIO_FROM' && ' (your Twilio number)'}
              {key === 'TWILIO_TO' && ' (alert recipient)'}
            </div>
            <input
              type={key.includes('TOKEN') ? 'password' : 'text'}
              placeholder={key === 'TWILIO_FROM' || key === 'TWILIO_TO' ? '+1234567890' : ''}
              value={config[key]}
              onChange={e => setConfig({...config, [key]: e.target.value})}
              className="cdms-input"
            />
          </div>
        ))}
      </div>

      {msg && (
        <div style={{ marginBottom: 12, fontSize: 12,
          color: msg.includes('✅') ? 'var(--accent-green)' : 'var(--accent-amber)' }}>
          {msg}
        </div>
      )}

      <div style={{ display: 'flex', gap: 8 }}>
        <button className="cdms-btn cdms-btn-primary" onClick={save}
          disabled={saving} style={{ flex: 1 }}>
          {saving ? 'Saving...' : 'Save Config'}
        </button>
        <button className="cdms-btn" onClick={test}
          disabled={testing || !status?.enabled} style={{ flex: 1 }}>
          {testing ? 'Sending...' : 'Send Test SMS'}
        </button>
      </div>
    </div>
  )
}

function DeadManSwitch({ token }) {
  const [status,   setStatus]   = useState(null)
  const [minutes,  setMinutes]  = useState(10)
  const [msg,      setMsg]      = useState('')

  const load = () => {
    fetch('/deadman/status').then(r => r.json()).then(setStatus).catch(() => {})
  }
  useEffect(() => { load(); const id = setInterval(load, 10000); return () => clearInterval(id) }, [])

  const enable = async () => {
    const res = await fetch('/deadman/enable', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ minutes })
    }).then(r => r.json())
    setMsg(res.status === 'enabled' ? `Enabled — triggers after ${minutes}m silence` : res.error || 'Error')
    load()
  }

  const disable = async () => {
    await fetch('/deadman/disable', { method: 'POST', headers: { Authorization: `Bearer ${token}` } })
    setMsg('Disabled')
    load()
  }

  const secsSince = status?.seconds_since_heartbeat
  const secsLeft  = status?.seconds_until_trigger

  return (
    <div className="glass-card" style={{ padding: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div className="card-label" style={{ marginBottom: 0 }}>Dead Man's Switch</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%',
            background: status?.enabled ? 'var(--accent-green)' : 'var(--text-muted)',
            boxShadow: status?.enabled ? '0 0 6px var(--accent-green)' : 'none' }} />
          <span style={{ fontSize: 12, color: status?.enabled ? 'var(--accent-green)' : 'var(--text-muted)', fontWeight: 600 }}>
            {status?.enabled ? 'Active' : 'Inactive'}
          </span>
        </div>
      </div>

      <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 14, lineHeight: 1.6 }}>
        Sends an email alert if no crowd analysis runs within the timeout window. Useful for detecting
        system failures or camera disconnects.
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
        <div style={{ padding: '10px 14px', borderRadius: 10, background: 'var(--bg-glass)',
          border: '1px solid var(--border-glass)' }}>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 4 }}>LAST HEARTBEAT</div>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>
            {secsSince !== null && secsSince !== undefined ? `${secsSince}s ago` : '—'}
          </div>
        </div>
        <div style={{ padding: '10px 14px', borderRadius: 10, background: 'var(--bg-glass)',
          border: '1px solid var(--border-glass)' }}>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 4 }}>TRIGGERS IN</div>
          <div style={{ fontSize: 13, fontWeight: 700,
            color: secsLeft !== null && secsLeft !== undefined && secsLeft < 60 ? 'var(--accent-red)' : 'var(--text-primary)' }}>
            {secsLeft !== null && secsLeft !== undefined ? `${secsLeft}s` : '—'}
          </div>
        </div>
      </div>

      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8 }}>Timeout</div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {[5, 10, 15, 30, 60].map(m => (
            <button key={m} onClick={() => setMinutes(m)}
              style={{ padding: '6px 14px', borderRadius: 8, fontSize: 12, cursor: 'pointer', border: '1px solid',
                borderColor: minutes === m ? 'var(--accent-purple)' : 'var(--border-glass)',
                background: minutes === m ? 'rgba(99,102,241,0.15)' : 'var(--bg-glass)',
                color: minutes === m ? 'var(--accent-purple)' : 'var(--text-secondary)',
                fontWeight: minutes === m ? 700 : 400 }}>
              {m}m
            </button>
          ))}
        </div>
      </div>

      {msg && (
        <div style={{ marginBottom: 12, fontSize: 12,
          color: msg.startsWith('Enabled') ? 'var(--accent-green)' : msg === 'Disabled' ? 'var(--text-muted)' : 'var(--accent-amber)' }}>
          {msg}
        </div>
      )}

      <div style={{ display: 'flex', gap: 8 }}>
        <button className="cdms-btn cdms-btn-primary" onClick={enable}
          disabled={status?.enabled} style={{ flex: 1, opacity: status?.enabled ? 0.5 : 1 }}>
          Enable
        </button>
        <button className="cdms-btn" onClick={disable}
          disabled={!status?.enabled} style={{ flex: 1, opacity: !status?.enabled ? 0.5 : 1 }}>
          Disable
        </button>
      </div>
    </div>
  )
}

export default function Assets() {
  const { token } = useAuth()
  const [zones,        setZones]    = useState({})
  const [warning,      setW]        = useState(50)
  const [danger,       setD]        = useState(100)
  const [mode,         setMode]     = useState('auto')
  const [activePreset, setPreset]   = useState(null)
  const [saved,        setSaved]    = useState('')

  // Location capacity state
  const [locName,     setLocName]     = useState('Main Location')
  const [maxCap,      setMaxCap]      = useState(100)
  const [cautionPct,  setCautionPct]  = useState(50)
  const [warningPct,  setWarningPct]  = useState(75)
  const [criticalPct, setCriticalPct] = useState(90)
  const [locSaved,    setLocSaved]    = useState(false)

  // Scheduler state
  const [schedEnabled,  setSchedEnabled]  = useState(false)
  const [schedInterval, setSchedInterval] = useState(5)
  const [schedLastRun,  setSchedLastRun]  = useState(null)
  const [schedLastResult, setSchedLastResult] = useState(null)
  const [schedRunCount, setSchedRunCount] = useState(0)
  const [schedRunning,  setSchedRunning]  = useState(false)

  useEffect(() => {
    api.getZones().then(z => { if (z && typeof z === 'object') setZones(z) }).catch(() => {})
    api.getThresholds().then(t => { setW(t.warning_threshold || t.warning || 50); setD(t.danger_threshold || t.danger || 100) }).catch(() => {})
    fetch('/location/config').then(r => r.json()).then(cfg => {
      if (!cfg) return
      setLocName(cfg.name || 'Main Location')
      setMaxCap(cfg.max_capacity || 100)
      setCautionPct(Math.round((cfg.caution_pct  || 0.5)  * 100))
      setWarningPct(Math.round((cfg.warning_pct  || 0.75) * 100))
      setCriticalPct(Math.round((cfg.critical_pct || 0.9)  * 100))
    }).catch(() => {})
    fetch('/schedule/config').then(r => r.json()).then(cfg => {
      if (!cfg) return
      setSchedEnabled(cfg.enabled || false)
      setSchedInterval(cfg.interval_minutes || 5)
      setSchedLastRun(cfg.last_run || null)
      setSchedLastResult(cfg.last_result || null)
      setSchedRunCount(cfg.run_count || 0)
    }).catch(() => {})
  }, [])

  const saveThresholds = async () => {
    if (warning >= danger) return alert('Warning must be less than danger')
    await api.updateThresholds({ warning_threshold: warning, danger_threshold: danger })
    setSaved('thresholds'); setTimeout(() => setSaved(''), 2000)
  }
  const saveZones = async () => {
    const payload = {}
    for (let i = 1; i <= 9; i++) {
      payload[`zone${i}`] = { name: zones[`zone${i}`]?.name || `Zone ${i}`, capacity: zones[`zone${i}`]?.capacity || 0 }
    }
    await fetch('/zones/config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
    setSaved('zones'); setTimeout(() => setSaved(''), 2000)
  }
  const applyPreset = async (key) => {
    const p = PRESETS[key]; if (!p) return
    setW(p.warning); setD(p.danger); setPreset(key)
    await api.updateThresholds({ warning_threshold: p.warning, danger_threshold: p.danger })
    setSaved('preset'); setTimeout(() => setSaved(''), 2000)
  }
  const updateZone = (i, field, value) => {
    setZones(z => ({ ...z, [`zone${i}`]: { ...z[`zone${i}`], [field]: field === 'capacity' ? Number(value) : value } }))
  }

  const saveLocationConfig = async () => {
    await fetch('/location/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: locName,
        max_capacity: maxCap,
        caution_pct:  cautionPct  / 100,
        warning_pct:  warningPct  / 100,
        critical_pct: criticalPct / 100,
      })
    })
    setLocSaved(true)
    setTimeout(() => setLocSaved(false), 2000)
  }

  const toggleSchedule = async () => {
    if (schedEnabled) {
      await fetch('/schedule/stop', { method: 'POST' })
      setSchedEnabled(false)
    } else {
      const res = await fetch('/schedule/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ interval_minutes: schedInterval })
      })
      const data = await res.json()
      if (!data.error) setSchedEnabled(true)
    }
  }

  const runNow = async () => {
    setSchedRunning(true)
    try {
      const res = await fetch('/schedule/run-now', { method: 'POST' })
      const data = await res.json()
      if (data.result) {
        setSchedLastResult(data.result)
        setSchedLastRun(new Date().toISOString())
        setSchedRunCount(c => c + 1)
      }
    } finally {
      setSchedRunning(false)
    }
  }

  const cautionTrigger  = Math.round(maxCap * cautionPct  / 100)
  const warningTrigger  = Math.round(maxCap * warningPct  / 100)
  const criticalTrigger = Math.round(maxCap * criticalPct / 100)

  return (
    <PageTransition>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div className="glass-card" style={{ padding: 20 }}>
            <div className="card-label">Camera Configuration</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, padding: 16, borderRadius: 12, background: 'var(--bg-glass)', border: '1px solid var(--border-glass)', marginBottom: 12 }}>
              <div style={{ width: 40, height: 40, borderRadius: 10, background: 'rgba(0,255,136,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20 }}>📹</div>
              <div>
                <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>CAM_01 // CDMS</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>Primary webcam — localhost · 640×480</div>
              </div>
              <div style={{ marginLeft: 'auto', padding: '3px 10px', borderRadius: 100, background: 'rgba(0,255,136,0.1)', color: 'var(--accent-green)', fontSize: 10, fontWeight: 700 }}>ACTIVE</div>
            </div>
            <div className="card-label" style={{ marginTop: 16 }}>Crowd Mode</div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {MODES.map(m => (
                <button key={m} onClick={() => setMode(m)} style={{ padding: '7px 16px', borderRadius: 8, border: '1px solid', borderColor: mode === m ? 'var(--accent-purple)' : 'var(--border-glass)', background: mode === m ? 'rgba(99,102,241,0.15)' : 'var(--bg-glass)', color: mode === m ? 'var(--accent-purple)' : 'var(--text-secondary)', fontSize: 12, fontWeight: mode === m ? 700 : 400, cursor: 'pointer', textTransform: 'capitalize' }}>
                  {m}
                </button>
              ))}
            </div>
          </div>

          <div className="glass-card" style={{ padding: 20 }}>
            <div className="card-label">Quick Presets</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 16 }}>
              {Object.entries({ library: '📚', street: '🏙', concert: '🎵', stadium: '🏟', station: '🚉', religious: '🕌' }).map(([key, emoji]) => (
                <button key={key} onClick={() => applyPreset(key)} style={{ padding: '8px 4px', borderRadius: 8, border: '1px solid', borderColor: activePreset === key ? 'var(--accent-purple)' : 'var(--border-glass)', background: activePreset === key ? 'rgba(99,102,241,0.15)' : 'var(--bg-glass)', color: activePreset === key ? 'var(--accent-purple)' : 'var(--text-secondary)', fontSize: 11, fontWeight: activePreset === key ? 700 : 400, cursor: 'pointer', textTransform: 'capitalize' }}>
                  {emoji} {key}
                </button>
              ))}
            </div>
            {saved === 'preset' && <div style={{ fontSize: 11, color: 'var(--accent-green)', marginBottom: 8 }}>✓ Preset applied</div>}
            <div className="card-label" style={{ marginTop: 16 }}>Threshold Config</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <span style={{ color: 'var(--text-secondary)', fontSize: 12 }}>Warning</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 20, fontWeight: 800, color: 'var(--accent-amber)', fontFamily: "'Space Grotesk', sans-serif" }}>{warning}</span>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>people</span>
                  </div>
                </div>
                <input
                  type="range"
                  min="1"
                  max="5000"
                  step="1"
                  value={warning}
                  onChange={e => setW(parseInt(e.target.value))}
                  style={{ width: '100%', accentColor: 'var(--accent-amber)', padding: 0, height: 6, cursor: 'pointer' }}
                />
                <input
                  type="number"
                  min="1"
                  max="5000"
                  value={warning}
                  onChange={e => setW(Math.max(1, parseInt(e.target.value) || 1))}
                  style={{ marginTop: 6, width: 80, textAlign: 'center', padding: '4px 8px', borderRadius: 6, border: '1px solid var(--border-glass)', background: 'var(--bg-glass)', color: 'var(--accent-amber)', fontSize: 13, fontWeight: 700, outline: 'none' }}
                />
              </div>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <span style={{ color: 'var(--text-secondary)', fontSize: 12 }}>Danger</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 20, fontWeight: 800, color: 'var(--accent-red)', fontFamily: "'Space Grotesk', sans-serif" }}>{danger}</span>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>people</span>
                  </div>
                </div>
                <input
                  type="range"
                  min="1"
                  max="10000"
                  step="1"
                  value={danger}
                  onChange={e => setD(parseInt(e.target.value))}
                  style={{ width: '100%', accentColor: 'var(--accent-red)', padding: 0, height: 6, cursor: 'pointer' }}
                />
                <input
                  type="number"
                  min="1"
                  max="10000"
                  value={danger}
                  onChange={e => setD(Math.max(1, parseInt(e.target.value) || 1))}
                  style={{ marginTop: 6, width: 80, textAlign: 'center', padding: '4px 8px', borderRadius: 6, border: '1px solid var(--border-glass)', background: 'var(--bg-glass)', color: 'var(--accent-red)', fontSize: 13, fontWeight: 700, outline: 'none' }}
                />
              </div>
              <button onClick={saveThresholds} style={{ padding: '8px 16px', borderRadius: 8, background: saved === 'thresholds' ? 'var(--accent-green)' : 'var(--accent-purple)', color: '#fff', fontWeight: 700, fontSize: 12, cursor: 'pointer', border: 'none' }}>
                {saved === 'thresholds' ? '✓ Saved' : 'Save Thresholds'}
              </button>
            </div>
          </div>
        </div>

        <div className="glass-card" style={{ padding: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div className="card-label" style={{ marginBottom: 0 }}>Zone Editor (3×3 Grid)</div>
            <button onClick={saveZones} style={{ padding: '7px 16px', borderRadius: 8, background: saved === 'zones' ? 'var(--accent-green)' : 'var(--accent-purple)', color: '#fff', fontWeight: 700, fontSize: 12, cursor: 'pointer', border: 'none' }}>
              {saved === 'zones' ? '✓ Saved' : 'Save Zones'}
            </button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
            {[...Array(9)].map((_, i) => {
              const z = zones[`zone${i+1}`] || {}
              return (
                <div key={i} style={{ padding: 14, borderRadius: 12, background: 'var(--bg-glass)', border: '1px solid var(--border-glass)' }}>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 8 }}>ZONE {i+1}</div>
                  <input value={z.name || `Zone ${i+1}`} onChange={e => updateZone(i+1, 'name', e.target.value)} placeholder="Zone name" style={{ width: '100%', padding: '5px 8px', borderRadius: 6, border: '1px solid var(--border-glass)', background: 'transparent', color: 'var(--text-primary)', fontSize: 12, marginBottom: 6, outline: 'none' }} />
                  <input value={z.capacity || ''} onChange={e => updateZone(i+1, 'capacity', e.target.value)} placeholder="Max capacity" type="number" style={{ width: '100%', padding: '5px 8px', borderRadius: 6, border: '1px solid var(--border-glass)', background: 'transparent', color: 'var(--accent-cyan)', fontSize: 12, outline: 'none' }} />
                </div>
              )
            })}
          </div>
        </div>

        {/* ── Location Capacity ───────────────────────────────────────────── */}
        <div className="glass-card" style={{ padding: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div className="card-label" style={{ marginBottom: 0 }}>Location Capacity</div>
            <button onClick={saveLocationConfig} style={{ padding: '7px 16px', borderRadius: 8, background: locSaved ? 'var(--accent-green)' : 'var(--accent-purple)', color: '#fff', fontWeight: 700, fontSize: 12, cursor: 'pointer', border: 'none' }}>
              {locSaved ? '✓ Saved' : 'Save Config'}
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
            <div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>Location Name</div>
              <input value={locName} onChange={e => setLocName(e.target.value)} style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: '1px solid var(--border-glass)', background: 'var(--bg-glass)', color: 'var(--text-primary)', fontSize: 13, outline: 'none' }} />
            </div>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Max Capacity</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 20, fontWeight: 800, color: 'var(--accent-cyan)', fontFamily: "'Space Grotesk', sans-serif" }}>{maxCap}</span>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>people</span>
                </div>
              </div>
              <input
                type="range"
                min="10"
                max="100000"
                step="10"
                value={maxCap}
                onChange={e => setMaxCap(parseInt(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--accent-cyan)', padding: 0, height: 6, cursor: 'pointer' }}
              />
              <input
                type="number"
                min="10"
                max="100000"
                step="10"
                value={maxCap}
                onChange={e => setMaxCap(Math.max(10, parseInt(e.target.value) || 10))}
                style={{ marginTop: 6, width: 100, textAlign: 'center', padding: '4px 8px', borderRadius: 6, border: '1px solid var(--border-glass)', background: 'var(--bg-glass)', color: 'var(--accent-cyan)', fontSize: 13, fontWeight: 700, outline: 'none' }}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 14 }}>
            {[
              { label: 'Caution %',  value: cautionPct,  set: setCautionPct,  color: 'var(--accent-cyan)'  },
              { label: 'Warning %',  value: warningPct,  set: setWarningPct,  color: 'var(--accent-amber)' },
              { label: 'Critical %', value: criticalPct, set: setCriticalPct, color: 'var(--accent-red)'   },
            ].map(({ label, value, set, color }) => (
              <div key={label}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 6 }}>
                  <span style={{ color: 'var(--text-muted)' }}>{label}</span>
                  <span style={{ color, fontWeight: 700 }}>{value}%</span>
                </div>
                <input type="range" min={1} max={99} value={value} onChange={e => set(Number(e.target.value))} style={{ width: '100%', accentColor: color }} />
              </div>
            ))}
          </div>

          <div style={{ padding: '10px 14px', borderRadius: 10, background: 'var(--bg-glass)', border: '1px solid var(--border-glass)', fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.8 }}>
            At <strong style={{ color: 'var(--text-primary)' }}>{maxCap}</strong> max capacity:
            caution at <span style={{ color: 'var(--accent-cyan)', fontWeight: 700 }}>{cautionTrigger}</span>,
            warning at <span style={{ color: 'var(--accent-amber)', fontWeight: 700 }}>{warningTrigger}</span>,
            critical at <span style={{ color: 'var(--accent-red)', fontWeight: 700 }}>{criticalTrigger}</span> people
          </div>
        </div>

        {/* ── Auto Analysis (Scheduler) ────────────────────────────────────── */}
        <div className="glass-card" style={{ padding: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div className="card-label" style={{ marginBottom: 0 }}>Auto Analysis</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              {schedRunCount > 0 && (
                <span style={{ fontSize: 11, padding: '2px 10px', borderRadius: 100, background: 'rgba(99,102,241,0.12)', color: 'var(--accent-purple)', fontWeight: 700 }}>
                  {schedRunCount} runs
                </span>
              )}
              <div
                onClick={toggleSchedule}
                style={{ width: 44, height: 24, borderRadius: 100, background: schedEnabled ? 'var(--accent-green)' : 'var(--bg-glass)', border: '1px solid var(--border-glass)', cursor: 'pointer', position: 'relative', transition: 'background 0.2s' }}
              >
                <div style={{ width: 18, height: 18, borderRadius: '50%', background: '#fff', position: 'absolute', top: 2, left: schedEnabled ? 22 : 2, transition: 'left 0.2s' }} />
              </div>
              <span style={{ fontSize: 12, color: schedEnabled ? 'var(--accent-green)' : 'var(--text-muted)', fontWeight: 600 }}>
                {schedEnabled ? 'Enabled' : 'Disabled'}
              </span>
            </div>
          </div>

          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8 }}>Interval</div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {INTERVAL_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setSchedInterval(opt.value)}
                  style={{ padding: '6px 14px', borderRadius: 8, border: '1px solid', borderColor: schedInterval === opt.value ? 'var(--accent-purple)' : 'var(--border-glass)', background: schedInterval === opt.value ? 'rgba(99,102,241,0.15)' : 'var(--bg-glass)', color: schedInterval === opt.value ? 'var(--accent-purple)' : 'var(--text-secondary)', fontSize: 12, fontWeight: schedInterval === opt.value ? 700 : 400, cursor: 'pointer' }}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
            <button
              onClick={runNow}
              disabled={schedRunning}
              style={{ padding: '8px 18px', borderRadius: 8, background: 'rgba(99,102,241,0.15)', border: '1px solid rgba(99,102,241,0.3)', color: 'var(--accent-purple)', fontSize: 12, fontWeight: 700, cursor: schedRunning ? 'default' : 'pointer', opacity: schedRunning ? 0.6 : 1 }}
            >
              {schedRunning ? '⏳ Running…' : '▶ Run Now'}
            </button>
          </div>

          {schedLastRun && (
            <div style={{ padding: '10px 14px', borderRadius: 10, background: 'var(--bg-glass)', border: '1px solid var(--border-glass)', fontSize: 12 }}>
              <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>
                Last run: <span style={{ color: 'var(--text-secondary)' }}>{new Date(schedLastRun).toLocaleString()}</span>
              </div>
              {schedLastResult && !schedLastResult.error && (
                <div style={{ color: 'var(--text-secondary)' }}>
                  Result: <span style={{ color: 'var(--accent-cyan)', fontWeight: 700 }}>{schedLastResult.person_count ?? '—'} people</span>
                  {' · '}
                  <span style={{ color: schedLastResult.risk_level === 'DANGER' ? 'var(--accent-red)' : schedLastResult.risk_level === 'WARNING' ? 'var(--accent-amber)' : 'var(--accent-green)', fontWeight: 700 }}>{schedLastResult.risk_level || 'SAFE'}</span>
                </div>
              )}
              {schedLastResult?.error && (
                <div style={{ color: 'var(--accent-amber)' }}>⚠ {schedLastResult.error}</div>
              )}
            </div>
          )}
        </div>

        <SMSConfig token={token} />
        <DeadManSwitch token={token} />
      </div>
    </PageTransition>
  )
}
