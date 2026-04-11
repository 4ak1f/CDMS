import { useState } from 'react'
import { BrowserRouter, Routes, Route, useLocation, Navigate } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { ThemeProvider } from './context/ThemeContext'
import { AuthProvider, useAuth } from './context/AuthContext'
import Layout        from './components/Layout'
import LoginPage     from './pages/LoginPage'
import UserManagement from './pages/UserManagement'
import Dashboard     from './components/Dashboard'
import LiveView      from './pages/LiveView'
import SystemMonitor from './pages/SystemMonitor'
import RiskAnalysis  from './pages/RiskAnalysis'
import IncidentLogs  from './pages/IncidentLogs'
import Historical    from './pages/Historical'
import Analytics     from './pages/Analytics'
import Assets        from './pages/Assets'
import Sectors       from './pages/Sectors'

function AnimatedRoutes({ isLive, setIsLive }) {
  const location = useLocation()
  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/"           element={<Dashboard onLiveChange={setIsLive} />} />
        <Route path="/live"       element={<LiveView />} />
        <Route path="/monitor"    element={<SystemMonitor />} />
        <Route path="/risk"       element={<RiskAnalysis />} />
        <Route path="/incidents"  element={<IncidentLogs />} />
        <Route path="/historical" element={<Historical />} />
        <Route path="/analytics"  element={<Analytics />} />
        <Route path="/assets"     element={<Assets />} />
        <Route path="/sectors"    element={<Sectors />} />
        <Route path="/users"      element={<UserManagement />} />
      </Routes>
    </AnimatePresence>
  )
}

function AppShell() {
  const [isLive, setIsLive] = useState(false)
  const { isAuthenticated, loading } = useAuth()
  const location = useLocation()

  if (loading) return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>Loading...</div>
    </div>
  )

  if (!isAuthenticated && location.pathname !== '/login') {
    return <Navigate to="/login" replace />
  }

  if (!isAuthenticated) return <LoginPage />

  return (
    <Layout isLive={isLive}>
      <AnimatedRoutes isLive={isLive} setIsLive={setIsLive} />
    </Layout>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <AppShell />
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}
