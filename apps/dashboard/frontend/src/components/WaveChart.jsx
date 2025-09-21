// apps/dashboard/frontend/src/components/WaveChart.jsx
import React from 'react'
import {
  ResponsiveContainer, ComposedChart, Line, Bar,
  CartesianGrid, XAxis, YAxis, Tooltip, Legend, Area, ReferenceLine
} from 'recharts'

export default function WaveChart({ waves = [], height = 360 }) {
  if (!waves?.length) return <p className="text-sm opacity-70">No wave data.</p>

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
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <ComposedChart data={data} margin={{ top: 10, right: 18, left: 0, bottom: 0 }}>
          {/* Gradients + strokes lấy từ CSS variables */}
          <defs>
            <linearGradient id="thrFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"  stopColor="var(--chart-bar-1)" stopOpacity="0.95" />
              <stop offset="100%" stopColor="var(--chart-bar-2)" stopOpacity="0.9" />
            </linearGradient>
          </defs>

          <CartesianGrid vertical={false} stroke="var(--chart-grid)" strokeDasharray="3 3" />
          <XAxis
            dataKey="wave"
            tick={{ fill: 'var(--chart-axis)', fontSize: 12 }}
            axisLine={{ stroke: 'var(--chart-grid)' }}
            tickLine={{ stroke: 'var(--chart-grid)' }}
          />
          <YAxis
            yAxisId="left"
            tick={{ fill: 'var(--chart-axis)', fontSize: 12 }}
            axisLine={{ stroke: 'var(--chart-grid)' }}
            tickLine={{ stroke: 'var(--chart-grid)' }}
            label={{ value: 'cmd/s', angle: -90, position: 'insideLeft', fill: 'var(--chart-axis)', fontSize: 12 }}
            domain={[0, 'auto']}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            tick={{ fill: 'var(--chart-axis)', fontSize: 12 }}
            axisLine={{ stroke: 'var(--chart-grid)' }}
            tickLine={{ stroke: 'var(--chart-grid)' }}
            label={{ value: 'Timeout (%)', angle: 90, position: 'insideRight', fill: 'var(--chart-axis)', fontSize: 12 }}
            domain={[0, 100]}
          />

          <Tooltip
            contentStyle={{ background: 'var(--chart-tooltip-bg)', border: '1px solid var(--chart-tooltip-border)', borderRadius: 8 }}
            labelStyle={{ color: 'var(--chart-legend)' }}
            itemStyle={{ color: 'var(--chart-legend)' }}
          />
          <Legend wrapperStyle={{ color: 'var(--chart-legend)' }} iconType="circle" />

          {/* Bar: Throughput */}
          <Bar
            yAxisId="left"
            dataKey="thr_total"
            name="Throughput (cmd/s)"
            fill="url(#thrFill)"
            stroke="var(--chart-bar-stroke)"
            strokeWidth={1}
            radius={[8, 8, 2, 2]}
            maxBarSize={26}
          />

          {/* Lines: p95 / p50 / Timeout% */}
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="p95"
            name="p95 (s)"
            stroke="var(--chart-p95)"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="p50"
            name="p50 (s)"
            stroke="var(--chart-p50)"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="timeout_pct"
            name="Timeout (%)"
            stroke="var(--chart-timeout)"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
            strokeDasharray="5 4"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
