// apps/dashboard/frontend/src/components/WaveChart.jsx
import React from 'react'
import {
  ResponsiveContainer, ComposedChart, Line, Bar,
  CartesianGrid, XAxis, YAxis, Tooltip, Legend
} from 'recharts'

export default function WaveChart({ waves = [] }) {
  if (!waves.length) return <p className="muted">No wave data.</p>
  const data = waves.map(w => ({
    wave: w.wave,
    thr_total: Number(w.thr_total || 0),
    thr_cpu: Number(w.thr_cpu || 0),
    thr_io: Number(w.thr_io || 0),
    timeout_pct: Math.round((Number(w.timeout_rate || 0) * 100) * 100) / 100,
    p95: Number(w.p95 || 0),
    p50: Number(w.p50 || 0),
  }))

  return (
    <div style={{ width: '100%', height: 360 }}>
      <ResponsiveContainer>
        <ComposedChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="wave" />
          <YAxis yAxisId="left"  domain={[0, 'auto']} />
          <YAxis yAxisId="right" orientation="right" domain={[0, 100]} />
          <Tooltip />
          <Legend />
          <Bar  yAxisId="left"  dataKey="thr_total" name="Throughput (cmd/s)" />
          <Line yAxisId="left"  dataKey="p95"       name="p95 (s)" dot={false} />
          <Line yAxisId="left"  dataKey="p50"       name="p50 (s)" dot={false} />
          <Line yAxisId="right" dataKey="timeout_pct" name="Timeout (%)" dot={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
