//apps/dashboard/frontend/src/BySeverityBar.jsx
import React from 'react'
import {
  ResponsiveContainer, BarChart, CartesianGrid, XAxis, YAxis, Tooltip, Legend, Bar
} from 'recharts'

export default function BySeverityBar({ bySeverity }) {
  const entries = Object.entries(bySeverity || {})
  const data = entries.map(([sev, v]) => ({
    severity: sev,
    rules: v.rules || 0,
    rules_ok: v.rules_ok || 0,
    cmd_ok: v.cmd_ok || 0,
    cmd_fail: v.cmd_fail || 0,
  })).sort((a, b) => (a.severity > b.severity ? 1 : -1))

  if (!data.length) return <p className="muted">No severity data.</p>

  return (
    <div style={{ width: '100%', height: 320 }}>
      <ResponsiveContainer>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="severity" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey="rules"     name="rules"    fill="var(--primary)" />
          <Bar dataKey="rules_ok"  name="rules_ok" fill="var(--accent)" />
          <Bar dataKey="cmd_ok"    name="cmd_ok"   fill="#22c55e" />
          <Bar dataKey="cmd_fail"  name="cmd_fail" fill="var(--danger)" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
