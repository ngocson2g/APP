import React, { useEffect, useState } from 'react'
import { api } from './services/api'
import Overview from './components/Overview'
import BySeverityBar from './components/BySeverityBar'
import TopFailingTable from './components/TopFailingTable'

export default function App() {
  const [runs, setRuns] = useState([])
  const [selectedRun, setSelectedRun] = useState('')
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api.listRuns().then((rs) => {
      setRuns(rs)
      if (rs.length) setSelectedRun(rs[0].id)
    })
  }, [])

  useEffect(() => {
    if (!selectedRun) return
    setLoading(true)
    api.getSummary(selectedRun).then((s) => {
      setSummary(s)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [selectedRun])

  return (
    <div className="container">
      <h1 style={{ margin: 0 }}>security_app Dashboard</h1>
      <p className="muted">Read-only analytics over your logs folder.</p>

      <div style={{ display: 'flex', gap: 12, alignItems: 'center', margin: '8px 0 20px' }}>
        <label htmlFor="run">Run:</label>
        <select id="run" value={selectedRun} onChange={(e) => setSelectedRun(e.target.value)}>
          {runs.map(r => (
            <option key={r.id} value={r.id}>
              {r.title} — {new Date(r.mtime * 1000).toLocaleString()} ({r.files} files)
            </option>
          ))}
        </select>
      </div>

      {loading && <p>Loading…</p>}
      {!loading && summary && (
        <>
          <Overview summary={summary} />
          <div className="card">
            <h3 style={{ marginTop: 0 }}>By severity</h3>
            <BySeverityBar bySeverity={summary.by_severity} />
          </div>
          <div className="card">
            <h3 style={{ marginTop: 0 }}>Top failing rules</h3>
            <TopFailingTable items={summary.top_failing_rules} />
          </div>
        </>
      )}
    </div>
  )
}
