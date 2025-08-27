import React, { useEffect, useState } from 'react'
import { api } from '../services/api'
import Overview from '../components/Overview'
import BySeverityBar from '../components/BySeverityBar'
import TopFailingTable from '../components/TopFailingTable'
import RunTrend from '../components/RunTrend'   // <-- thêm

export default function Reporting() {
  const [runs, setRuns] = useState([])
  const [selectedRun, setSelectedRun] = useState('')
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(false)
  const [series, setSeries] = useState([])      // <-- thêm

  const CountRuntren = 20
  useEffect(() => {
    api.listRuns().then((rs) => {
      setRuns(rs)
      if (rs.length) setSelectedRun(rs[0].id)
    })
    api.getRunTimeseries(CountRuntren).then(setSeries).catch(() => {})   // <-- tải timeseries
  }, [])

  useEffect(() => {
    if (!selectedRun) return
    setLoading(true)
    api.getSummary(selectedRun)
      .then((s) => { setSummary(s); setLoading(false) })
      .catch(() => setLoading(false))
  }, [selectedRun])

  return (
    <>
      {/* RUN PICKER luôn hiện khi đã có runs */}
    <div className="card" style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
      <h3 style={{ margin: 0, marginRight: 8 }}>Select run</h3>
      {runs.length ? (
        <>
          <select
            value={selectedRun || ''}
            onChange={(e) => setSelectedRun(e.target.value)}
            style={{
              background: 'var(--bg)', color: 'var(--text)',
              border: '1px solid var(--border)', padding: '8px 12px', borderRadius: 8
            }}
          >
            {runs.map((r) => (
              <option key={r.id} value={r.id}>
                {new Date(r.mtime * 1000).toLocaleString()} — {r.id}
              </option>
            ))}
          </select>
          <button
            onClick={() => runs.length && setSelectedRun(runs[0].id)} // runs[0] = mới nhất (backend sort DESC)
            style={{
              background: 'var(--primary)', color: '#fff',
              border: '1px solid var(--primary)', padding: '8px 12px', borderRadius: 8
            }}
          >
            Latest
          </button>
        </>
      ) : (
        <span className="muted">No logs found.</span>
      )}
    </div>

    {/* TIMESERIES luôn hiện (nếu có dữ liệu) */}
    <div className="card">
      <h3 style={{ marginTop: 0 }}>Trends (last 20 runs)</h3>
      <RunTrend data={series} />
    </div>

    {/* SUMMARY của run đã chọn */}
    {loading && <p>Loading…</p>}
    {!loading && summary && (
      <>
        <Overview summary={summary} />
        <div className="card">
          <h3 style={{ marginTop: 0 }}>By severity</h3>
          <BySeverityBar bySeverity={summary.by_severity} />
        </div>

        <TopFailingTable items={summary.top_failing_rules} />
      </>
    )}
    </>
  )
}
