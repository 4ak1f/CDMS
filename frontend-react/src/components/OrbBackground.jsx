import { motion } from 'framer-motion'
import { useTheme } from '../context/ThemeContext'

export default function OrbBackground() {
  const { isDark } = useTheme()
  return (
    <div style={{ position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0, overflow: 'hidden' }}>
      {[
        { size: 600, x: '-10%', y: '-10%', delay: 0,  color: 'var(--orb1)' },
        { size: 500, x: '60%',  y: '10%',  delay: -3, color: 'var(--orb2)' },
        { size: 450, x: '20%',  y: '60%',  delay: -5, color: 'var(--orb3)' },
      ].map((orb, i) => (
        <motion.div
          key={i}
          animate={{ y: [0, -40, 0], x: [0, 20, 0], scale: [1, 1.08, 1] }}
          transition={{ duration: 10 + i * 2, repeat: Infinity, ease: 'easeInOut', delay: orb.delay }}
          style={{
            position: 'absolute',
            width: orb.size, height: orb.size,
            left: orb.x, top: orb.y,
            borderRadius: '50%',
            background: `radial-gradient(circle, ${orb.color}, transparent 70%)`,
            filter: isDark ? 'blur(80px)' : 'blur(60px)',
          }}
        />
      ))}
    </div>
  )
}
