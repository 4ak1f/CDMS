import { useState } from 'react'
import { motion } from 'framer-motion'
import { useAuth } from '../context/AuthContext'
import CDMSLogo from '../components/CDMSLogo'

export default function LoginPage() {
  const { login }         = useAuth()
  const [email, setEmail] = useState('')
  const [pass,  setPass]  = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, pass)
    } catch(err) {
      setError(err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh', background: 'var(--bg-base)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      position: 'relative', overflow: 'hidden'
    }}>
      {/* Background orbs */}
      {[
        { size: 500, left: '-10%', top: '-10%', color: 'rgba(99,102,241,0.15)' },
        { size: 400, right: '-5%', bottom: '10%', color: 'rgba(6,182,212,0.12)' },
      ].map((orb, i) => (
        <motion.div key={i}
          animate={{ y: [0, -20, 0], scale: [1, 1.05, 1] }}
          transition={{ duration: 10 + i*2, repeat: Infinity, ease: 'easeInOut' }}
          style={{
            position: 'absolute', width: orb.size, height: orb.size,
            left: orb.left, top: orb.top, right: orb.right, bottom: orb.bottom,
            borderRadius: '50%',
            background: `radial-gradient(circle, ${orb.color}, transparent 70%)`,
            filter: 'blur(60px)', pointerEvents: 'none',
          }}
        />
      ))}

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="glass-card"
        style={{ width: 400, padding: 40, position: 'relative', zIndex: 1 }}
      >
        {/* Logo */}
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 32 }}>
          <CDMSLogo size={32} showText={true} />
        </div>

        <div style={{ marginBottom: 28, textAlign: 'center' }}>
          <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 20, color: 'var(--text-primary)', marginBottom: 6 }}>
            Sign in to CDMS
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            Crowd Disaster Management System
          </div>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <div className="card-label">Email</div>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="admin@cdms.local"
              className="cdms-input"
              required
              autoFocus
            />
          </div>
          <div>
            <div className="card-label">Password</div>
            <input
              type="password"
              value={pass}
              onChange={e => setPass(e.target.value)}
              placeholder="••••••••"
              className="cdms-input"
              required
            />
          </div>

          {error && (
            <motion.div
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              style={{ padding: '10px 14px', borderRadius: 10,
                background: 'rgba(220,38,38,0.08)', border: '1px solid rgba(220,38,38,0.2)',
                fontSize: 13, color: 'var(--accent-red)' }}
            >
              {error}
            </motion.div>
          )}

          <motion.button
            whileTap={{ scale: 0.98 }}
            type="submit"
            disabled={loading}
            className="cdms-btn cdms-btn-primary"
            style={{ width: '100%', marginTop: 6, opacity: loading ? 0.7 : 1 }}
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </motion.button>
        </form>

        <div style={{ marginTop: 20, padding: '12px 16px', borderRadius: 10,
          background: 'var(--bg-glass)', border: '1px solid var(--border-glass)',
          fontSize: 12, color: 'var(--text-muted)', textAlign: 'center' }}>
          Default: admin@cdms.local / admin123<br />
          <span style={{ color: 'var(--accent-amber)', fontSize: 11 }}>Change password after first login</span>
        </div>
      </motion.div>
    </div>
  )
}
