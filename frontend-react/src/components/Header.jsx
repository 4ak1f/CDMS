import { motion } from 'framer-motion'

export default function Header({ isLive }) {
  return (
    <motion.header
      initial={{ y: -60, opacity: 0 }}
      animate={{ y: 0,   opacity: 1 }}
      style={{
        background: 'linear-gradient(135deg, rgba(8,12,20,0.98) 0%, rgba(13,20,36,0.98) 100%)',
        borderBottom: '1px solid rgba(0,212,255,0.1)',
        padding: '0 32px',
        height: 64,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 40,
        backdropFilter: 'blur(20px)',
        boxShadow: '0 4px 30px rgba(0,0,0,0.5)'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <div style={{
          width: 38, height: 38,
          background: 'linear-gradient(135deg, #ff3b5c, #ff9500)',
          borderRadius: 10,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 18,
          boxShadow: '0 4px 15px rgba(255,59,92,0.4)'
        }}>🚨</div>
        <div>
          <div style={{ fontWeight: 800, color: '#fff', fontSize: '1rem', letterSpacing: 0.3 }}>
            Crowd Disaster Management System
          </div>
          <div style={{ color: '#475569', fontSize: '0.72rem', marginTop: 1 }}>
            AI-powered real-time crowd monitoring & early warning
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <div style={{ fontFamily: 'monospace', fontSize: '0.78rem', color: '#475569' }}>
          Model MAE: <span style={{ color: '#00d4ff', fontWeight: 700 }}>13.77</span>
        </div>

        <motion.div
          animate={isLive ? { boxShadow: ['0 0 0 0 rgba(0,255,136,0.4)', '0 0 0 8px rgba(0,255,136,0)', '0 0 0 0 rgba(0,255,136,0)'] } : {}}
          transition={{ duration: 2, repeat: Infinity }}
          style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '6px 16px',
            borderRadius: 100,
            border: `1px solid ${isLive ? 'rgba(0,255,136,0.4)' : 'rgba(71,85,105,0.4)'}`,
            background: isLive ? 'rgba(0,255,136,0.08)' : 'rgba(71,85,105,0.08)',
            fontSize: '0.72rem',
            fontWeight: 800,
            letterSpacing: 2,
            color: isLive ? '#00ff88' : '#475569',
            transition: 'all 0.5s ease'
          }}
        >
          <motion.div
            animate={isLive ? { opacity: [1, 0.3, 1] } : { opacity: 1 }}
            transition={{ duration: 1, repeat: Infinity }}
            style={{
              width: 7, height: 7,
              borderRadius: '50%',
              background: isLive ? '#00ff88' : '#475569',
              boxShadow: isLive ? '0 0 8px #00ff88' : 'none'
            }}
          />
          {isLive ? 'LIVE' : 'STANDBY'}
        </motion.div>
      </div>
    </motion.header>
  )
}