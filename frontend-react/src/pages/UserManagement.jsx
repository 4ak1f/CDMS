import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { UserPlus, Shield, Eye, Edit2, Trash2 } from 'lucide-react'
import PageTransition from '../components/PageTransition'
import { useAuth } from '../context/AuthContext'

const ROLE_STYLES = {
  admin:    { color: '#ff3b5c', label: 'Admin',    icon: Shield },
  operator: { color: '#6366f1', label: 'Operator', icon: Edit2  },
  viewer:   { color: '#06b6d4', label: 'Viewer',   icon: Eye    },
}

export default function UserManagement() {
  const { token, isAdmin } = useAuth()
  const [users,    setUsers]    = useState([])
  const [loading,  setLoading]  = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [newUser,  setNewUser]  = useState({ email: '', name: '', password: '', role: 'operator' })
  const [saving,   setSaving]   = useState(false)
  const [error,    setError]    = useState('')

  const headers = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }

  const fetchUsers = async () => {
    try {
      const data = await fetch('/auth/users', { headers }).then(r => r.json())
      setUsers(data.users || [])
    } catch(e) {} finally { setLoading(false) }
  }

  useEffect(() => { fetchUsers() }, [])

  const createUser = async () => {
    if (!newUser.email || !newUser.name || !newUser.password) return setError('All fields required')
    setSaving(true)
    try {
      const res = await fetch('/auth/register', { method: 'POST', headers, body: JSON.stringify(newUser) })
      const data = await res.json()
      if (!res.ok) { setError(data.error); return }
      setShowForm(false)
      setNewUser({ email: '', name: '', password: '', role: 'operator' })
      fetchUsers()
    } catch(e) { setError('Failed to create user') }
    finally { setSaving(false) }
  }

  const changeRole = async (userId, role) => {
    await fetch(`/auth/users/${userId}/role`, { method: 'PUT', headers, body: JSON.stringify({ role }) })
    fetchUsers()
  }

  const removeUser = async (userId) => {
    if (!confirm('Deactivate this user?')) return
    await fetch(`/auth/users/${userId}`, { method: 'DELETE', headers })
    fetchUsers()
  }

  if (!isAdmin) return (
    <PageTransition>
      <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>
        Admin access required
      </div>
    </PageTransition>
  )

  return (
    <PageTransition>
      <div style={{ maxWidth: 800, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 20 }}>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="section-heading">User Management</div>
          <button className="cdms-btn cdms-btn-primary" onClick={() => setShowForm(!showForm)}>
            <UserPlus size={14} /> Add User
          </button>
        </div>

        {showForm && (
          <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
            className="glass-card" style={{ padding: 20 }}>
            <div className="card-label">New User</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
              <div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Name</div>
                <input className="cdms-input" placeholder="Full name" value={newUser.name}
                  onChange={e => setNewUser({...newUser, name: e.target.value})} />
              </div>
              <div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Email</div>
                <input className="cdms-input" type="email" placeholder="user@example.com" value={newUser.email}
                  onChange={e => setNewUser({...newUser, email: e.target.value})} />
              </div>
              <div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Password</div>
                <input className="cdms-input" type="password" placeholder="Min 6 chars" value={newUser.password}
                  onChange={e => setNewUser({...newUser, password: e.target.value})} />
              </div>
              <div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Role</div>
                <select className="cdms-input" value={newUser.role}
                  onChange={e => setNewUser({...newUser, role: e.target.value})}>
                  <option value="operator">Operator</option>
                  <option value="viewer">Viewer</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            </div>
            {error && <div style={{ color: 'var(--accent-red)', fontSize: 12, marginBottom: 10 }}>{error}</div>}
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="cdms-btn cdms-btn-primary" onClick={createUser} disabled={saving}>
                {saving ? 'Creating...' : 'Create User'}
              </button>
              <button className="cdms-btn" onClick={() => { setShowForm(false); setError('') }}>Cancel</button>
            </div>
          </motion.div>
        )}

        <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="cdms-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Role</th>
                <th>Last Login</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={5} style={{ textAlign: 'center', padding: 24, color: 'var(--text-muted)' }}>Loading...</td></tr>
              ) : users.map(u => {
                const rs = ROLE_STYLES[u.role] || ROLE_STYLES.operator
                return (
                  <tr key={u.id}>
                    <td>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: 13 }}>{u.name}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{u.email}</div>
                    </td>
                    <td>
                      <span style={{ fontSize: 11, fontWeight: 700, padding: '3px 10px', borderRadius: 100,
                        background: `${rs.color}15`, color: rs.color, border: `1px solid ${rs.color}30` }}>
                        {rs.label}
                      </span>
                    </td>
                    <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      {u.last_login ? new Date(u.last_login).toLocaleDateString() : 'Never'}
                    </td>
                    <td>
                      <span style={{ fontSize: 11, fontWeight: 600, color: u.active ? 'var(--accent-green)' : 'var(--text-muted)' }}>
                        {u.active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: 6 }}>
                        <select value={u.role} onChange={e => changeRole(u.id, e.target.value)}
                          style={{ fontSize: 11, padding: '3px 8px', borderRadius: 6, background: 'var(--bg-glass)',
                            border: '1px solid var(--border-glass)', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                          <option value="admin">Admin</option>
                          <option value="operator">Operator</option>
                          <option value="viewer">Viewer</option>
                        </select>
                        <button onClick={() => removeUser(u.id)}
                          style={{ padding: '3px 8px', borderRadius: 6, background: 'rgba(220,38,38,0.1)',
                            border: '1px solid rgba(220,38,38,0.2)', color: 'var(--accent-red)', cursor: 'pointer', fontSize: 11 }}>
                          Remove
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {/* Role descriptions */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 12 }}>
          {Object.entries(ROLE_STYLES).map(([role, rs]) => (
            <div key={role} className="glass-card" style={{ padding: 16 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: rs.color, marginBottom: 6, textTransform: 'capitalize' }}>{rs.label}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.5 }}>
                {role === 'admin' && 'Full access. Manage users, change settings, view all data.'}
                {role === 'operator' && 'Can run analysis, submit feedback, view all monitoring data.'}
                {role === 'viewer' && 'Read-only access. Can view dashboard and reports only.'}
              </div>
            </div>
          ))}
        </div>
      </div>
    </PageTransition>
  )
}
