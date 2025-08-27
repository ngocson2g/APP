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
      {/* ... phần chọn run + summary giữ nguyên ... */}

      {loading && <p>Loading…</p>}
      {!loading && summary && (
        <>
          <div className="card">
            <h3 style={{ marginTop: 0 }}>Trends (last 20 runs)</h3>
            <RunTrend data={series} />
          </div>

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
    </>
  )
}
