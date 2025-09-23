// apps/dashboard/frontend/src/components/WaveChart.jsx
import React from 'react'
import {
  ResponsiveContainer, ComposedChart, Line, Bar,
  CartesianGrid, XAxis, YAxis, Tooltip, Legend, Area, ReferenceLine
} from 'recharts'

export default function WaveChart({ waves = [], height = 360 }) {
  if (!waves?.length) return <p className="text-sm opacity-70">No wave data.</p>

  const data = React.useMemo(() => {
  const arr = (waves || []).map(w => ({
    wave: Number(w.wave || 0),
    // dùng trực tiếp các trường đã tính sẵn trong JSON
    thr_total: Number(w.thr_total || 0),
    thr_cpu:   Number(w.thr_cpu   || 0),
    thr_io:    Number(w.thr_io    || 0),
    timeout_pct: Math.round(Number(w.timeout_rate || 0) * 10000) / 100, // => %
    p95: Number(w.p95 || 0),
    p50: Number(w.p50 || 0),
    // thêm 2 trường phụ để tự check lệch (không vẽ)
    _cmds: Number(w.cmds || 0),
    _elapsed: Number(w.elapsed_sec || 0),
  }))
  // sort theo thứ tự wave tăng dần đề phòng file chưa được sắp xếp
  arr.sort((a, b) => a.wave - b.wave)

  // cảnh báo nếu thr_total trong file khác với cmds/elapsed (>5%)
  arr.forEach(d => {
    if (d._cmds > 0 && d._elapsed > 0) {
      const calc = d._cmds / d._elapsed
      const diff = Math.abs(calc - d.thr_total) / (d.thr_total || 1)
      if (diff > 0.05) {
        // chỉ log dev, không ảnh hưởng UI
        console.warn(`[Wave ${d.wave}] thr mismatch: json=${d.thr_total} calc=${calc.toFixed(3)}`)
      }
    }
  })

  // loại bỏ trường phụ trước khi trả về cho chart
  return arr.map(({ _cmds, _elapsed, ...rest }) => rest)
}, [waves])


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
