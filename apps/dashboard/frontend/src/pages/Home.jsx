// apps/dashboard/frontend/src/pages/Home.jsx
import React from 'react'
import { Link } from 'react-router-dom'

export default function Home() {
  return (
    <div>
      <h2 style={{ marginTop: 0 }}>Home</h2>
      <p className="muted">Đi tới:</p>
      <ul>
        <li><Link to="/reporting">/reporting – trang báo cáo</Link></li>
        <li><Link to="/checking">/checking – trang kiểm tra</Link></li>
      </ul>
    </div>
  )
}
