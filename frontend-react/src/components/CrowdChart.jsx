import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts'
import { motion } from 'framer-motion'
import { api } from '../utils/api'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="glass rounded-lg p-3 text-xs border border-border">
      <div className="text-slate-400 mb-1">{label}</div>
      <div className="text-accent font-bold">{payload[0].value} people</div>
    </div>
  )
}

export default function CrowdChart({ stats, onRefresh }) {
  const chartData = stats.recent_counts.map((count, i) => ({
    time: stats.recent_timestamps[i]?.split(' ')[1]?.slice(0, 5) || `${i}`,
    count
  }))

  return (
    <div className="card h-full flex flex-col">
      <div className="card-header">
        <span className="card-title">📈 Crowd Trend</span>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={onRefresh}
          className="text-xs text-slate-500 hover:text-accent transition-colors border border-border rounded-lg px-3 py-1"
        >
          ↻ Refresh
        </motion.button>
      </div>

      <div className="flex-1 p-4 flex flex-col gap-4">
        <div className="h-44">
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#00d4ff" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#00d4ff" stopOpacity={0}   />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2d4a" />
                <XAxis dataKey="time" tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} />
                <YAxis tick={{ fill: '#64748b', fontSize: 10 }} tickLine={false} axisLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="count"
                  stroke="#00d4ff"
                  strokeWidth={2}
                  fill="url(#colorCount)"
                  dot={{ fill: '#00d4ff', r: 3 }}
                  activeDot={{ r: 5, fill: '#00d4ff' }}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-slate-600 text-sm">
              No data yet — run an analysis
            </div>
          )}
        </div>

        <div className="grid grid-cols-3 gap-2">
          {[
            { label: 'Safe',    val: stats.risk_distribution?.SAFE    || 0, color: 'text-safe'    },
            { label: 'Warning', val: stats.risk_distribution?.WARNING || 0, color: 'text-warning' },
            { label: 'Danger',  val: stats.risk_distribution?.DANGER  || 0, color: 'text-danger'  },
          ].map(s => (
            <div key={s.label} className="bg-surface rounded-xl p-3 text-center border border-border">
              <div className={`text-xl font-black ${s.color}`}>{s.val}</div>
              <div className="text-slate-600 text-xs mt-0.5">{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}