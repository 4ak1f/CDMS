import { createContext, useContext, useState, useEffect, useCallback } from 'react'

const AuthContext = createContext()

export function AuthProvider({ children }) {
  const [user,    setUser]    = useState(null)
  const [token,   setToken]   = useState(() => localStorage.getItem('cdms_token'))
  const [loading, setLoading] = useState(true)

  const fetchMe = useCallback(async (t) => {
    if (!t) { setLoading(false); return }
    try {
      const res = await fetch('/auth/me', {
        headers: { Authorization: `Bearer ${t}` }
      })
      if (res.ok) {
        const data = await res.json()
        setUser(data)
      } else {
        localStorage.removeItem('cdms_token')
        setToken(null)
        setUser(null)
      }
    } catch(e) {
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchMe(token) }, [token, fetchMe])

  const login = async (email, password) => {
    const res = await fetch('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Login failed')
    localStorage.setItem('cdms_token', data.token)
    setToken(data.token)
    setUser({ email: data.email, name: data.name, role: data.role, id: data.user_id })
    return data
  }

  const logout = () => {
    localStorage.removeItem('cdms_token')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout,
      isAdmin: user?.role === 'admin',
      isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
