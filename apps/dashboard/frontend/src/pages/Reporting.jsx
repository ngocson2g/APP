//apps/dashboard/frontend/src/pages/Reporting.jsx
import React, { useEffect, useState } from 'react'
import { api, BASE } from '../services/api'
import Overview from '../components/Overview'
import BySeverityBar from '../components/BySeverityBar'
import TopFailingTable from '../components/TopFailingTable'
import RunTrend from '../components/RunTrend'   // <-- thêm
import RuleDialog from '../components/RuleDialog'
import DeniedTable from '../components/DeniedTable'
import WaveChart from '../components/WaveChart'
import AllRulesTable from '../components/AllRulesTable'

export default function Reporting() {
  const [runs, setRuns] = useState([])
  const [selectedRun, setSelectedRun] = useState(() => localStorage.getItem('selected_run') || '')
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(false)
  const [series, setSeries] = useState([])      // <-- thêm
  const [openIdx, setOpenIdx] = useState(null)
  const CountRuntren = 20 //LIMITS_TIMESERIES
  const [waves, setWaves] = useState(null)

  useEffect(() => {
    api.listRuns().then((rs) => {
      setRuns(rs)
      const urlRun = new URLSearchParams(window.location.search).get('run')
      const def = urlRun || localStorage.getItem('selected_run') || (rs[0]?.id || '')
      if (def) setSelectedRun(def)
    })
    api.getRunTimeseries(CountRuntren).then(setSeries).catch(() => {})   // <-- tải timeseries
  }, [])


  // Lưu/lặp lại view: nhớ run đang chọn & cập nhật URL ?run=...
  useEffect(() => {
    if (!selectedRun) return
    localStorage.setItem('selected_run', selectedRun)
    const usp = new URLSearchParams(window.location.search)
    usp.set('run', selectedRun)
    window.history.replaceState({}, '', `/reporting?${usp.toString()}`)
  }, [selectedRun])
  useEffect(() => {
    if (!selectedRun) return
    setLoading(true)
    api.getSummary(selectedRun)
      .then((s) => { setSummary(s); setLoading(false) })
      .catch(() => setLoading(false))
  }, [selectedRun])

  useEffect(() => {
    if (!selectedRun) return
    api.getRunWaves(selectedRun)
      .then(setWaves)
      .catch(() => setWaves(null))
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
          <button onClick={() => window.open(`${BASE}/api/runs/${selectedRun}/export/pdf`)}>
            Export PDF
          </button>
          <button onClick={() => window.open(`${BASE}/api/runs/${selectedRun}/export/excel`)}>
            Export Excel
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
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Execution waves (throughput • p50/p95 • timeout%)</h3>
          <WaveChart waves={waves?.waves || []} />
        </div>
        <TopFailingTable
          items={summary?.top_failing_rules || []}
          onSelect={(idx) => {
            console.log('[Reporting] onSelect idx =', idx)
            setOpenIdx(idx)
        }}
        />
        
        <RuleDialog
          open={openIdx !== null}
          runId={selectedRun}
          index={openIdx}
          onClose={() => setOpenIdx(null)}
        />
        <DeniedTable items={summary.denied_rules} />
        <AllRulesTable
          items={summary?.all_rules || []} // <-- LƯU Ý QUAN TRỌNG
          onSelect={(idx) => {
            console.log('[Reporting] onSelect AllRulesTable idx =', idx)
            setOpenIdx(idx)
          }}
        />
      </>
    )}
    </>
  )
}
