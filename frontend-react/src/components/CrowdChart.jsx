import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { motion } from 'framer-motion'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-glass)', borderRadius: 8, padding: '8px 12px', fontSize: 12 }}>
      <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>{label}</div>
      <div style={{ color: 'var(--accent-cyan)', fontWeight: 700 }}>{payload[0].value} people</div>
    </div>
  )
}

export default function CrowdChart({ stats, onRefresh }) {
  const chartData = (stats?.recent_counts || []).map((count, i) => ({
    time: stats.recent_timestamps?.[i]?.split(' ')[1]?.slice(0, 5) || `${i}`,
    count
  }))

  return (
    <div className="glass-card" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border-glass)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span className="card-label" style={{ marginBottom: 0 }}>Crowd Trend</span>
        <motion.button
          whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
          onClick={onRefresh}
          style={{ fontSize: 11, color: 'var(--text-muted)', border: '1px solid var(--border-glass)', borderRadius: 8, padding: '4px 10px', background: 'var(--bg-glass)', cursor: 'pointer' }}
        >
          ↻ Refresh
        </motion.button>
      </div>

      <div style={{ flex: 1, padding: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ height: 176 }}>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="var(--accent-cyan)" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="var(--accent-cyan)" stopOpacity={0}   />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-glass)" />
                <XAxis dataKey="time" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickLine={false} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickLine={false} axisLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="count" stroke="var(--accent-cyan)" strokeWidth={2} fill="url(#colorCount)" dot={{ fill: 'var(--accent-cyan)', r: 3 }} activeDot={{ r: 5 }} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
              No data yet — run an analysis
            </div>
          )}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
          {[
            { label: 'Safe',    val: stats?.risk_distribution?.SAFE    || 0, color: 'var(--accent-green)' },
            { label: 'Warning', val: stats?.risk_distribution?.WARNING || 0, color: 'var(--accent-amber)' },
            { label: 'Danger',  val: stats?.risk_distribution?.DANGER  || 0, color: 'var(--accent-red)'   },
          ].map(s => (
            <div key={s.label} style={{ background: 'var(--bg-glass)', borderRadius: 10, padding: '10px 8px', textAlign: 'center', border: '1px solid var(--border-glass)' }}>
              <div style={{ fontSize: 20, fontWeight: 800, color: s.color, fontFamily: "'Space Grotesk', sans-serif" }}>{s.val}</div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
