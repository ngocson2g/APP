//apps/dashboard/frontend/src/components/RunTrend.jsx
import React from 'react'
import {
  ResponsiveContainer, ComposedChart, Line, Bar,
  CartesianGrid, XAxis, YAxis, Tooltip, Legend, Brush, ReferenceLine
} from 'recharts'

export default function RunTrend({ data }) {
  if (!data || !data.length) return <p className="muted">No run data.</p>

  // Chuẩn hoá & tính MA5 cho pass_rate
  const chartData = data.map((r, i) => {
    const pass_rate = Number(r.pass_rate ?? 0); // Tính tỷ lệ pass
    return {
      idx: i + 1,
      run: r.id,
      time: new Date(r.mtime * 1000).toLocaleString(),
      pass_rate: pass_rate,
      failure_rate: 100 - pass_rate, // <-- THÊM DÒNG NÀY
      with_failures: Number(r.with_failures ?? 0),
      commands_failed: Number(r.commands_failed ?? 0),
    }
  })
  for (let i = 0; i < chartData.length; i++) {
    const start = Math.max(0, i - 4)
    const window = chartData.slice(start, i + 1).map(d => d.pass_rate)
    const avg = window.reduce((a, b) => a + b, 0) / window.length
    chartData[i].ma5 = Math.round(avg * 100) / 100
  }

  return (
    <div style={{ width: '100%', height: 360 }}>
      <ResponsiveContainer>
        <ComposedChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,.35)" />
            <XAxis dataKey="idx" tick={{ fill: 'var(--muted)' }} />
            <YAxis yAxisId="left" tick={{ fill: 'var(--muted)' }} domain={[0,100]} />
            <Tooltip wrapperStyle={{ background:'var(--bg-card)', border:'1px solid var(--border)' }} />
            <Legend />

            {/* 1. ĐÃ XÓA/ẨN DÒNG NÀY ĐỂ BỎ NÉT ĐỨT VÀNG */}
            {/* <ReferenceLine yAxisId="left" y={80} stroke="var(--warn)" strokeDasharray="4 4" /> */}

            {/* 2. THÊM "strokeWidth={2}" ĐỂ TÔ ĐẬM CÁC ĐƯỜNG */}
            <Line
              yAxisId="left"
              dataKey="failure_rate"
              name="Failure Rate (%)"
              type="monotone"
              dot={false}
              stroke="var(--danger)"
              strokeWidth={2} 
            />
            <Line
              yAxisId="left"
              dataKey="pass_rate"
              name="Pass rate (%)"
              type="monotone"
              dot={false}
              stroke="var(--primary)"
              strokeWidth={2} 
            />
            <Line
              yAxisId="left"
              dataKey="ma5"
              name="MA5 (%)"
              type="monotone"
              dot={false}
              stroke="var(--accent)"
              strokeWidth={2} 
            />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
    
  )
}
