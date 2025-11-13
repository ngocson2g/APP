// apps/dashboard/frontend/src/components/ThroughputBreakdownChart.jsx
import React from 'react'
import {
  ResponsiveContainer, ComposedChart, Line, Bar,
  CartesianGrid, XAxis, YAxis, Tooltip, Legend
} from 'recharts'

export default function ThroughputBreakdownChart({ waves = [], height = 360 }) {
  const data = React.useMemo(() => {
    // Lấy logic xử lý data tương tự như WaveChart
    const arr = (waves || []).map(w => ({
      wave: Number(w.wave || 0),
      cmds: Number(w.cmds || 0),
      thr_cpu:   Number(w.thr_cpu   || 0),
      thr_io:    Number(w.thr_io    || 0),
    }))
    // sort theo thứ tự wave tăng dần
    arr.sort((a, b) => a.wave - b.wave)
    return arr
  }, [waves])

  if (!data.length) return null // Không hiển thị gì nếu không có data

  return (
    // Bọc trong 1 card mới
    <div style={{ width: '100%', height}}>
      
      <ResponsiveContainer>
        <ComposedChart data={data} margin={{ top: 10, right: 18, left: 0, bottom: 0 }}>
          
          

          <CartesianGrid vertical={false} stroke="var(--chart-grid)" strokeDasharray="3 3" />
          <XAxis
            dataKey="wave"
            tick={{ fill: 'var(--chart-axis)', fontSize: 12 }}
            axisLine={{ stroke: 'var(--chart-grid)' }}
            tickLine={{ stroke: 'var(--chart-grid)' }}
          />
    
          {/* TRỤC Y BÊN TRÁI (mới): Commands */}
          <YAxis
            yAxisId="left"
            tick={{ fill: 'var(--chart-axis)', fontSize: 12 }}
            axisLine={{ stroke: 'var(--chart-grid)' }}
            tickLine={{ stroke: 'var(--chart-grid)' }}
            label={{ value: 'Commands', angle: -90, position: 'insideLeft', fill: 'var(--chart-axis)', fontSize: 12 }}
            domain={[0, 'auto']}
          />
          
          {/* TRỤC Y BÊN PHẢI (mới): cmd/s */}
          <YAxis
            yAxisId="right"
            orientation="right"
            tick={{ fill: 'var(--chart-axis)', fontSize: 12 }}
            axisLine={{ stroke: 'var(--chart-grid)' }}
            tickLine={{ stroke: 'var(--chart-grid)' }}
            label={{ value: 'cmd/s', angle: 90, position: 'insideRight', fill: 'var(--chart-axis)', fontSize: 12 }}
            domain={[0, 'auto']} 
          />

          <Tooltip
            contentStyle={{ background: 'var(--chart-tooltip-bg)', border: '1px solid var(--chart-tooltip-border)', borderRadius: 8 }}
            labelStyle={{ color: 'var(--chart-legend)' }}
            itemStyle={{ color: 'var(--chart-legend)' }}
          />
          <Legend 
            wrapperStyle={{ color: 'var(--chart-legend)' }} 
            iconType="circle" 
          />

          {/* Bar (Xếp chồng): thr_cpu và thr_io (dùng trục trái) */}
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="thr_cpu"
            name="CPU (cmd/s)"
            stroke="var(--primary)" /* Lấy màu fill cũ */
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />

          {/* Line: thr_io (dùng trục trái) */}
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="thr_io"
            name="I/O (cmd/s)"
            stroke="var(--accent)" /* Lấy màu fill cũ */
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />

          {/* Bar: cmds (dùng trục phải) */}
          <Bar
            yAxisId="left"
            dataKey="cmds"
            name="Total Commands"
            fill="var(--warn)" /* Lấy màu stroke cũ */
            radius={[8, 8, 2, 2]}
            maxBarSize={26}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}