//apps/dashboard/frontend/src/BySeverityBar.jsx
import React from 'react'
import {
  ResponsiveContainer, BarChart, CartesianGrid, XAxis, YAxis, Tooltip, Legend, Bar
} from 'recharts'

const ORDER = { critical: 5, high: 4, medium: 3, low: 2, unknown: 1 };

const SeverityTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div 
        style={{ 
          // Dùng style từ theme.css
          background: 'var(--bg-card)', 
          border: '1px solid var(--border)', 
          borderRadius: '8px', 
          padding: '12px', 
          boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
          minWidth: '150px' // Đảm bảo độ rộng tối thiểu
        }}
      >
        {/* Tiêu đề (VD: "medium") */}
        <p style={{ 
          margin: 0, 
          marginBottom: '8px', 
          fontWeight: 'bold', 
          color: 'var(--text)',
          textTransform: 'capitalize' // Viết hoa chữ cái đầu
        }}>
          {label}
        </p>
        
        {/* Lặp qua các mục (rules_fail, rules_ok, ...) */}
        {payload.map((item) => (
          <p 
            key={item.name} 
            style={{ 
              margin: 0, 
              // Quan trọng: Lấy màu tự động từ thanh Bar
              color: item.color 
            }}
          >
            {item.name} : {item.value}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

export default function BySeverityBar({ bySeverity }) {
  const entries = Object.entries(bySeverity || {})
  const data = entries.map(([sev, v]) => {
  const rules = v.rules || 0;
  const rules_ok = v.rules_ok || 0;
  const rules_fail = rules - rules_ok; // <-- TÍNH TOÁN rules_fail

  return {
    severity: sev,
    // rules: rules, // <-- ĐÃ BỎ
    rules_fail: rules_fail, // <-- THÊM MỚI
    rules_ok: v.rules_ok || 0,
    cmd_ok: v.cmd_ok || 0,
    cmd_fail: v.cmd_fail || 0,
  };
  }).sort((a, b) => {
    const orderA = ORDER[a.severity] || 0;
    const orderB = ORDER[b.severity] || 0;
    return orderB - orderA; // Sắp xếp giảm dần (cao -> trung bình -> thấp)
  });

  if (!data.length) return <p className="muted">No severity data.</p>

  return (
    <div style={{ width: '100%', height: 320 }}>
      <ResponsiveContainer>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="severity" />
          <YAxis />
          <Tooltip content={<SeverityTooltip />} />
          <Legend />
          <Bar dataKey="rules_fail" name="rules_fail" fill="var(--warn)"  stackId="a"/>
          <Bar dataKey="rules_ok"  name="rules_ok" fill="var(--accent)" stackId="a"/>
          <Bar dataKey="cmd_fail"  name="cmd_fail" fill="var(--danger)" stackId="b"/>
          <Bar dataKey="cmd_ok"    name="cmd_ok"   fill="var(--primary)" stackId="b"/> 
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
