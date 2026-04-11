import { useTheme } from '../context/ThemeContext'

export default function CDMSLogo({ size = 36, showText = true }) {
  useTheme()

  if (!showText) {
    return (
      <svg width={size} height={size} viewBox="0 0 64 64" fill="none">
        <rect width="64" height="64" rx="16" fill="#1e293b" stroke="rgba(99,102,241,0.5)" strokeWidth="1.5"/>
        <defs>
          <linearGradient id="ic" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#ffffff"/>
            <stop offset="100%" stopColor="#bae6fd"/>
          </linearGradient>
        </defs>
        <path d="M 32 12 A 20 20 0 1 0 32 52 L 32 43 A 11 11 0 1 1 32 21 Z" fill="url(#ic)"/>
        <rect x="24" y="10" width="14" height="6" rx="3" fill="#1e293b"/>
        <rect x="24" y="50" width="14" height="6" rx="3" fill="#1e293b"/>
      </svg>
    )
  }

  return (
    <div style={{ width: '100%', display: 'block', padding: '0 4px' }}>
      <svg width="100%" height={size} viewBox="0 0 220 56" fill="none" preserveAspectRatio="xMidYMid meet">
        <defs>
          <linearGradient id="pbg" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#1e293b"/>
            <stop offset="100%" stopColor="#0f172a"/>
          </linearGradient>
          <linearGradient id="pc" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#ffffff"/>
            <stop offset="100%" stopColor="#bae6fd"/>
          </linearGradient>
          <linearGradient id="ps" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(255,255,255,0.14)"/>
            <stop offset="100%" stopColor="rgba(255,255,255,0)"/>
          </linearGradient>
        </defs>
        <rect width="220" height="56" rx="28" fill="url(#pbg)" stroke="rgba(99,102,241,0.45)" strokeWidth="1.5"/>
        <rect x="5" y="5" width="210" height="46" rx="24" fill="url(#ps)"/>
        <path d="M 32 10 A 18 18 0 1 0 32 46 L 32 38 A 10 10 0 1 1 32 18 Z" fill="url(#pc)"/>
        <rect x="25" y="8" width="12" height="5" rx="2.5" fill="#0f172a"/>
        <rect x="25" y="43" width="12" height="5" rx="2.5" fill="#0f172a"/>
        <text x="62" y="27" fontFamily="'Inter', system-ui, sans-serif" fontWeight="800" fontSize="21" fill="white" letterSpacing="-0.5">CDMS</text>
        <text x="63" y="42" fontFamily="'Inter', system-ui, sans-serif" fontWeight="500" fontSize="8" fill="rgba(255,255,255,0.6)" letterSpacing="3">CORE SYSTEM</text>
      </svg>
    </div>
  )
}
