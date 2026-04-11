import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard, Video, Activity, AlertTriangle,
  FileWarning, History, BarChart2, Camera, Map,
  HelpCircle, BookOpen, Sun, Moon, Bell, Settings, ChevronRight,
  X, Database, Wifi, WifiOff, MessageSquare, Users
} from 'lucide-react'
import { useTheme } from '../context/ThemeContext'
import { useAuth } from '../context/AuthContext'
import OrbBackground from './OrbBackground'
import CDMSLogo from './CDMSLogo'
import FeedbackWidget from './FeedbackWidget'

const NAV = [
  { section: 'MAIN' },
  { label: 'Dashboard',      path: '/',           icon: LayoutDashboard },
  { label: 'Live View',      path: '/live',        icon: Video,          liveIndicator: true },
  { label: 'System Monitor', path: '/monitor',     icon: Activity },
  { section: 'ANALYSIS' },
  { label: 'Risk Analysis',  path: '/risk',        icon: AlertTriangle },
  { label: 'Incident Logs',  path: '/incidents',   icon: FileWarning },
  { label: 'Historical',     path: '/historical',  icon: History },
  { label: 'Analytics',      path: '/analytics',   icon: BarChart2 },
  { section: 'CONFIG' },
  { label: 'Assets',         path: '/assets',      icon: Camera },
  { label: 'Sectors',        path: '/sectors',     icon: Map },
  { label: 'Users',          path: '/users',       icon: Users },
]

function UserBadge() {
  const { user, logout } = useAuth()
  if (!user) return null
  const roleColors = { admin: '#ff3b5c', operator: '#6366f1', viewer: '#06b6d4' }
  return (
    <div style={{ padding: '10px 10px 8px', borderTop: '1px solid var(--border-glass)', marginBottom: 4 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{ width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
          background: `${roleColors[user.role] || '#6366f1'}20`,
          border: `1px solid ${roleColors[user.role] || '#6366f1'}40`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 11, fontWeight: 700, color: roleColors[user.role] || '#6366f1' }}>
          {user.name?.charAt(0).toUpperCase()}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)',
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {user.name}
          </div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'capitalize' }}>
            {user.role}
          </div>
        </div>
        <button onClick={logout} title="Sign out"
          style={{ background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--text-muted)', padding: 4, borderRadius: 6,
            fontSize: 11, flexShrink: 0 }}>
          ⎋
        </button>
      </div>
    </div>
  )
}

export default function Layout({ children, isLive = false }) {
  const { pathname } = useLocation()
  const { toggle, isDark, theme } = useTheme()
  const [notifCount] = useState(0)
  const [mae, setMae] = useState(null)
  const [showSettings, setShowSettings] = useState(false)
  const [showSupport,  setShowSupport]  = useState(false)
  const [showDocs,     setShowDocs]     = useState(false)
  const [showFeedback, setShowFeedback] = useState(false)
  const [cloudConnected, setCloudConnected] = useState(false)

  useEffect(() => {
    fetch('/system/stats').then(r => r.json()).then(d => {
      if (d.model_mae != null) setMae(d.model_mae)
    }).catch(() => {})
  }, [])

  useEffect(() => {
    fetch('/cloud/status')
      .then(r => r.json())
      .then(d => setCloudConnected(d.supabase_connected))
      .catch(() => {})
  }, [])

  const pageTitle  = NAV.find(n => n.path === pathname)?.label || 'Dashboard'
  const parentPath = pathname === '/' ? null : 'Dashboard'

  return (
    <div style={{ display: 'flex', minHeight: '100vh', position: 'relative' }}>
      <OrbBackground />

      <motion.aside
        initial={{ x: -240, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.4, ease: [0.25,0.46,0.45,0.94] }}
        style={{
          position: 'fixed', left: 0, top: 0, bottom: 0, width: 240, zIndex: 50,
          background: 'var(--sidebar-bg)',
          borderRight: '1px solid var(--sidebar-border)',
          backdropFilter: 'blur(30px)', WebkitBackdropFilter: 'blur(30px)',
          display: 'flex', flexDirection: 'column', padding: '0 12px 16px',
          overflowY: 'auto', overflowX: 'hidden',
        }}
      >
        <Link to="/" style={{ textDecoration: 'none' }}>
          <div style={{ padding: '16px 12px 14px', borderBottom: '1px solid var(--border-glass)', marginBottom: 8 }}>
            <CDMSLogo size={36} showText={true} />
          </div>
        </Link>

        <nav style={{ flex: 1 }}>
          {NAV.map((item, i) => {
            if (item.section) return (
              <div key={i} style={{ fontSize: 9, fontWeight: 700, letterSpacing: '2.5px', textTransform: 'uppercase', color: 'var(--text-muted)', padding: '16px 10px 6px' }}>
                {item.section}
              </div>
            )
            const active = pathname === item.path
            const Icon = item.icon
            return (
              <motion.div key={item.path} initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.04 }}>
                <Link to={item.path} style={{ textDecoration: 'none', display: 'block', marginBottom: 2 }}>
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: 10, padding: '9px 10px', borderRadius: 12,
                    background: active ? 'rgba(99,102,241,0.12)' : 'transparent',
                    border: active ? '1px solid rgba(99,102,241,0.25)' : '1px solid transparent',
                    color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
                    fontSize: 13, fontWeight: active ? 600 : 400,
                    position: 'relative', overflow: 'hidden',
                  }}>
                    {active && <div style={{ position: 'absolute', left: 0, top: '20%', bottom: '20%', width: 3, background: 'linear-gradient(180deg, #6366f1, #06b6d4)', borderRadius: '0 2px 2px 0' }} />}
                    <Icon size={15} style={{ color: active ? 'var(--accent-purple)' : 'inherit', flexShrink: 0 }} />
                    <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.label}</span>
                    {item.liveIndicator && isLive && <div style={{ marginLeft: 'auto', width: 7, height: 7, borderRadius: '50%', background: '#00ff88', boxShadow: '0 0 6px #00ff88', flexShrink: 0 }} />}
                  </div>
                </Link>
              </motion.div>
            )
          })}
        </nav>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <UserBadge />
          {[
            { icon: MessageSquare, label: 'Submit Feedback', action: () => setShowFeedback(true) },
            { icon: HelpCircle,    label: 'Support',         action: () => setShowSupport(true) },
            { icon: BookOpen,      label: 'Documentation',   action: () => setShowDocs(true) },
          ].map(({ icon: Icon, label, action }) => (
            <div
              key={label}
              onClick={action}
              style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px', borderRadius: 10, color: 'var(--text-muted)', fontSize: 12, cursor: 'pointer', transition: 'color 0.2s' }}
              onMouseEnter={e => e.currentTarget.style.color = 'var(--text-secondary)'}
              onMouseLeave={e => e.currentTarget.style.color = 'var(--text-muted)'}
            >
              <Icon size={14} />{label}
            </div>
          ))}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 10px 0', fontSize: 11, color: 'var(--text-muted)' }}>
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent-green)', boxShadow: '0 0 6px var(--accent-green)' }} />
            All systems operational
          </div>
        </div>
      </motion.aside>

      <div style={{ marginLeft: 240, flex: 1, display: 'flex', flexDirection: 'column', position: 'relative', zIndex: 1 }}>
        <motion.header
          initial={{ y: -60, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.4 }}
          style={{
            position: 'sticky', top: 0, zIndex: 40, height: 60,
            background: 'var(--header-bg)',
            borderBottom: '1px solid var(--border-glass)',
            backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)',
            display: 'flex', alignItems: 'center', padding: '0 24px', gap: 12,
          }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            {parentPath && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: 'var(--text-muted)', marginBottom: 1 }}>
                <span>{parentPath}</span><ChevronRight size={10} /><span style={{ color: 'var(--text-secondary)' }}>{pageTitle}</span>
              </div>
            )}
            <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 16, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {pageTitle}
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
            <div id="mae-badge" style={{ padding: '5px 12px', borderRadius: 100, border: '1px solid var(--border-glass)', background: 'var(--bg-glass)', fontSize: 11, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
              MAE <span style={{ color: 'var(--accent-cyan)', fontWeight: 700 }}>{mae != null ? mae : '—'}</span>
            </div>
            <motion.div
              animate={isLive ? { boxShadow: ['0 0 0 0 rgba(0,255,136,0.4)', '0 0 0 6px rgba(0,255,136,0)', '0 0 0 0 rgba(0,255,136,0)'] } : {}}
              transition={{ duration: 2, repeat: Infinity }}
              style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '5px 14px', borderRadius: 100, border: `1px solid ${isLive ? 'rgba(0,255,136,0.3)' : 'var(--border-glass)'}`, background: isLive ? 'rgba(0,255,136,0.07)' : 'var(--bg-glass)', fontSize: 10, fontWeight: 800, letterSpacing: 2, color: isLive ? 'var(--accent-green)' : 'var(--text-muted)' }}
            >
              <motion.div animate={isLive ? { opacity: [1,0.3,1] } : {}} transition={{ duration: 1, repeat: Infinity }} style={{ width: 6, height: 6, borderRadius: '50%', background: isLive ? 'var(--accent-green)' : 'var(--text-muted)' }} />
              {isLive ? 'LIVE' : 'STANDBY'}
            </motion.div>
            <div style={{ position: 'relative', cursor: 'pointer' }}>
              <Bell size={18} style={{ color: 'var(--text-secondary)' }} />
              {notifCount > 0 && <div style={{ position: 'absolute', top: -4, right: -4, width: 14, height: 14, borderRadius: '50%', background: 'var(--accent-red)', fontSize: 8, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{notifCount}</div>}
            </div>
            <motion.button whileTap={{ scale: 0.9 }} onClick={toggle} style={{ width: 36, height: 36, borderRadius: 10, background: 'var(--bg-glass)', border: '1px solid var(--border-glass)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', color: 'var(--text-secondary)' }}>
              {isDark ? <Sun size={16} /> : <Moon size={16} />}
            </motion.button>
            <motion.div whileTap={{ scale: 0.9 }} onClick={() => setShowSettings(true)} style={{ cursor: 'pointer' }}>
              <Settings size={18} style={{ color: 'var(--text-secondary)' }} />
            </motion.div>
          </div>
        </motion.header>

        <main style={{ flex: 1, padding: '24px', overflowY: 'auto' }}>
          {children}
        </main>
      </div>

      {/* ── Settings Modal ── */}
      <AnimatePresence>
        {showSettings && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={() => setShowSettings(false)}
            style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', backdropFilter: 'blur(4px)' }}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95 }}
              onClick={e => e.stopPropagation()}
              className="glass-card"
              style={{ width: 480, padding: 28, position: 'relative' }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
                <div className="section-heading">System Settings</div>
                <X size={18} style={{ cursor: 'pointer', color: 'var(--text-muted)' }} onClick={() => setShowSettings(false)} />
              </div>

              {/* Cloud sync status */}
              <div style={{ marginBottom: 20 }}>
                <div className="card-label">Cloud Sync</div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', background: 'var(--bg-glass)', borderRadius: 12, border: '1px solid var(--border-glass)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    {cloudConnected
                      ? <Wifi size={16} style={{ color: 'var(--accent-green)' }} />
                      : <WifiOff size={16} style={{ color: 'var(--text-muted)' }} />}
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>Supabase Cloud</div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                        {cloudConnected
                          ? 'Connected — auto-archiving every 100 detections'
                          : 'Not connected — check .env configuration'}
                      </div>
                    </div>
                  </div>
                  <span className={`badge ${cloudConnected ? 'badge-green' : 'badge-red'}`}>
                    {cloudConnected ? 'LIVE' : 'OFFLINE'}
                  </span>
                </div>
              </div>

              {/* Manual archive button */}
              <div style={{ marginBottom: 20 }}>
                <div className="card-label">Manual Archive</div>
                <button
                  className="cdms-btn cdms-btn-primary"
                  style={{ width: '100%' }}
                  onClick={async () => {
                    const res = await fetch('/cloud/archive', { method: 'POST' }).then(r => r.json())
                    alert(res.status === 'ok'
                      ? `✅ Archived ${res.archived} records to cloud`
                      : `⚠️ ${res.error || res.status}`)
                  }}
                >
                  <Database size={14} /> Archive Local Data to Cloud Now
                </button>
              </div>

              {/* Theme */}
              <div style={{ marginBottom: 20 }}>
                <div className="card-label">Appearance</div>
                <div style={{ display: 'flex', gap: 8 }}>
                  {['dark', 'light'].map(t => (
                    <button
                      key={t}
                      onClick={() => { if (t !== theme) toggle() }}
                      className="cdms-btn"
                      style={{
                        flex: 1,
                        background:   theme === t ? 'rgba(99,102,241,0.15)' : 'var(--bg-glass)',
                        borderColor:  theme === t ? 'var(--accent-purple)'   : 'var(--border-glass)',
                        color:        theme === t ? 'var(--accent-purple)'   : 'var(--text-secondary)',
                        textTransform: 'capitalize',
                      }}
                    >
                      {t === 'dark' ? '🌙' : '☀️'} {t.charAt(0).toUpperCase() + t.slice(1)} Mode
                    </button>
                  ))}
                </div>
              </div>

              {/* Device ID */}
              <div>
                <div className="card-label">Device Identifier</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', padding: '8px 12px', background: 'var(--bg-glass)', borderRadius: 8, fontFamily: 'monospace' }}>
                  {navigator.userAgent.split(')')[0].split('(')[1] || 'Unknown device'}
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Support Modal ── */}
      <AnimatePresence>
        {showSupport && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={() => setShowSupport(false)}
            style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', backdropFilter: 'blur(4px)' }}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95 }}
              onClick={e => e.stopPropagation()}
              className="glass-card"
              style={{ width: 440, padding: 28 }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                <div className="section-heading">Support</div>
                <X size={18} style={{ cursor: 'pointer', color: 'var(--text-muted)' }} onClick={() => setShowSupport(false)} />
              </div>
              {[
                { label: 'GitHub Repository',  value: 'github.com/4ak1f/CDMS',                     href: 'https://github.com/4ak1f/CDMS' },
                { label: 'HuggingFace Space',  value: 'huggingface.co/spaces/4AK1F/CDMS',           href: 'https://huggingface.co/spaces/4AK1F/CDMS' },
                { label: 'Report an Issue',    value: 'Open GitHub Issues',                         href: 'https://github.com/4ak1f/CDMS/issues' },
              ].map(item => (
                <a key={item.label} href={item.href} target="_blank" rel="noreferrer" style={{ textDecoration: 'none', display: 'block', marginBottom: 10 }}>
                  <div style={{ padding: '12px 16px', background: 'var(--bg-glass)', borderRadius: 12, border: '1px solid var(--border-glass)' }}>
                    <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 2, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 3 }}>{item.label}</div>
                    <div style={{ fontSize: 13, color: 'var(--accent-cyan)' }}>{item.value}</div>
                  </div>
                </a>
              ))}
              <div style={{ marginTop: 16, padding: '12px 16px', background: 'rgba(99,102,241,0.08)', borderRadius: 12, border: '1px solid rgba(99,102,241,0.2)' }}>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                  CDMS v1.0 — AI-powered crowd monitoring system.<br />
                  Model MAE: {mae ?? '—'} | Architecture: VGG16 + Dilated CNN
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Feedback Modal ── */}
      <AnimatePresence>
        {showFeedback && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={() => setShowFeedback(false)}
            style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', backdropFilter: 'blur(4px)' }}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95 }}
              onClick={e => e.stopPropagation()}
              className="glass-card"
              style={{ width: 400, padding: 28 }}
            >
              <FeedbackWidget onClose={() => setShowFeedback(false)} />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Documentation Modal ── */}
      <AnimatePresence>
        {showDocs && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={() => setShowDocs(false)}
            style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', backdropFilter: 'blur(4px)' }}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95 }}
              onClick={e => e.stopPropagation()}
              className="glass-card"
              style={{ width: 520, padding: 28, maxHeight: '80vh', overflowY: 'auto' }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                <div className="section-heading">Documentation</div>
                <X size={18} style={{ cursor: 'pointer', color: 'var(--text-muted)' }} onClick={() => setShowDocs(false)} />
              </div>
              {[
                { title: 'Getting Started',    desc: 'Start the camera feed from the Dashboard or Live View page. The system automatically detects crowd density and triggers alerts.' },
                { title: 'Crowd Modes',        desc: 'Auto mode selects the best algorithm. Use Sparse for 1–10 people, Moderate for 10–50, Dense for 50–200, Mega for 200+ people.' },
                { title: 'Scene Learning',     desc: 'Submit feedback after each analysis to improve accuracy. After 3 corrections for a scene, the system converges and self-calibrates.' },
                { title: 'Thresholds',         desc: 'Configure Warning and Danger thresholds in Assets page or Risk Analysis. Default: Warning=10, Danger=25 people.' },
                { title: 'Cloud Sync',         desc: 'All detections sync to Supabase cloud automatically. Every 100 detections triggers an auto-archive and local database reset.' },
                { title: 'Model Performance',  desc: 'Current model MAE: 2.52 (world-class accuracy). Architecture: VGG16 frontend with Dilated CNN backend, trained on ShanghaiTech + JHU datasets.' },
              ].map((item, i) => (
                <div key={i} style={{ marginBottom: 16, paddingBottom: 16, borderBottom: i < 5 ? '1px solid var(--border-glass)' : 'none' }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 5 }}>{item.title}</div>
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{item.desc}</div>
                </div>
              ))}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
