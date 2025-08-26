// apps/dashboard/frontend/src/App.jsx
import React from 'react'
import { BrowserRouter, Routes, Route, Navigate, Link, useLocation } from 'react-router-dom'
import Home from './pages/Home'
import Reporting from './pages/Reporting'
import Checking from './pages/Checking'

function Shell() {
  const { pathname } = useLocation()
  const isActive = (p) => pathname === p || pathname.startsWith(p + '/')

  return (
    <div className="container">
      <header style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:16 }}>
        <h1 style={{ margin: 0 }}>security_app Dashboard</h1>
        <nav style={{ display:'flex', gap:12 }}>
          <Link to="/home" className={isActive('/home') ? 'active' : ''}>Home</Link>
          <Link to="/reporting" className={isActive('/reporting') ? 'active' : ''}>Reporting</Link>
          <Link to="/checking" className={isActive('/checking') ? 'active' : ''}>Checking</Link>
        </nav>
      </header>

      <Routes>
        <Route path="/" element={<Navigate to="/home" replace />} />
        <Route path="/home" element={<Home />} />
        <Route path="/reporting" element={<Reporting />} />
        <Route path="/checking" element={<Checking />} />
        <Route path="*" element={<Navigate to="/home" replace />} />
      </Routes>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Shell />
    </BrowserRouter>
  )
}
