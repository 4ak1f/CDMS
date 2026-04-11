import { motion } from 'framer-motion'

const variants = {
  initial: { opacity: 0, y: 18, filter: 'blur(6px)' },
  animate: { opacity: 1, y: 0,  filter: 'blur(0px)', transition: { duration: 0.3, ease: [0.25,0.46,0.45,0.94] } },
  exit:    { opacity: 0, y: -10, filter: 'blur(4px)', transition: { duration: 0.2 } }
}

export default function PageTransition({ children }) {
  return (
    <motion.div variants={variants} initial="initial" animate="animate" exit="exit" style={{ width: '100%', minHeight: '100%' }}>
      {children}
    </motion.div>
  )
}
