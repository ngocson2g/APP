//apps/dashboard/frontend/src/components/RunTrend.jsx
import React from 'react'
import {
  ResponsiveContainer, ComposedChart, Line, Bar,
  CartesianGrid, XAxis, YAxis, Tooltip, Legend, Brush, ReferenceLine
} from 'recharts'

// CustomTooltip component (đặt bên ngoài RunTrend)
const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    // payload[0] thường là Failure Rate (màu đỏ)
    // payload[1] thường là Pass Rate (màu xanh primary)
    // payload[2] thường là MA5 (màu xanh accent)

    const failureRate = payload.find(item => item.dataKey === 'failure_rate');
    const passRate = payload.find(item => item.dataKey === 'pass_rate');
    const ma5 = payload.find(item => item.dataKey === 'ma5');

    return (
      <div 
        style={{ 
          background: 'var(--bg-card)', 
          border: '1px solid var(--border)', 
          borderRadius: '8px', 
          padding: '12px', 
          boxShadow: '0 4px 6px rgba(165, 159, 159, 0.1)',
          minWidth: '180px'
        }}
      >
        <p style={{ margin: 0, marginBottom: '8px', fontWeight: 'bold', color: 'var(--text)' }}>
          Device: {label}
        </p>
        {failureRate && (
          <p style={{ margin: 0, color: 'var(--danger)' }}>
            {failureRate.name}: {failureRate.value.toFixed(2)} %
          </p>
        )}
        {passRate && (
          <p style={{ margin: 0, color: 'var(--primary)' }}>
            {passRate.name}: {passRate.value.toFixed(2)} %
          </p>
        )}
        {ma5 && (
          <p style={{ margin: 0, color: 'var(--accent)' }}>
            {ma5.name}: {ma5.value.toFixed(2)} %
          </p>
        )}
      </div>
    );
  }

  return null;
};


export default function RunTrend({ data, selectedRun }) {
  if (!data || !data.length) return <p className="muted">No run data.</p>

  // Chuẩn hoá & tính MA5 cho pass_rate
  const chartData = data.map((r, i) => {
    const pass_rate = Number(r.pass_rate ?? 0); // Tính tỷ lệ pass
    return {
      idx: i + 1,
      run: r.id,
      time: new Date(r.mtime * 1000).toLocaleString(),
      pass_rate: pass_rate,
      failure_rate: 100 - pass_rate, 
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

  // THÊM MỚI: Component để render nhãn trục X tùy chỉnh
  const CustomXAxisTick = (props) => {
    // props này được Recharts tự động truyền vào
    const { x, y, payload } = props;
    
    // Lấy run_id của nhãn này
    const tickValue = payload.value;

    // Kiểm tra xem nhãn này có phải là run đang được chọn hay không
    const isSelected = (tickValue === selectedRun);

    return (
      <g transform={`translate(${x},${y})`}>
        <text
          x={0}
          y={0}
          dy={5} // Hiệu chỉnh vị trí dọc một chút
          textAnchor="end" // Căn lề phải
          transform="rotate(-45)" // Xoay 45 độ
          style={{
            fill: isSelected ? 'var(--primary)' : 'var(--muted)', // Đổi màu nếu được chọn
            fontSize: 10,
            fontWeight: isSelected ? 700 : 400 // In đậm nếu được chọn
          }}
        >
          {tickValue}
        </text>
      </g>
    );
  };

  return (
    <div style={{ width: '100%', height: 400 }}>
      <ResponsiveContainer width="99%" height={400} className="chart-wrapper">
        <ComposedChart width={1500} height={400} data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,.35)" />
            <XAxis 
              dataKey="run"     // <-- 1. Thay "idx" thành "run"
              angle={-45}         // <-- 2. Xoay nhãn 45 độ
              textAnchor="end"    // <-- 3. Căn chỉnh nhãn về bên phải
              height={150}         // <-- 4. Thêm chiều cao cho trục X để chứa nhãn
              interval={0}        // <-- 5. (Tùy chọn) Hiển thị TẤT CẢ các nhãn
              tick={<CustomXAxisTick />}
            />
            <YAxis yAxisId="left" tick={{ fill: 'var(--muted)' }} domain={[0,100]} />
            <Tooltip content={<CustomTooltip />} />
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
