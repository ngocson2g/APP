import React, { useMemo } from 'react'

const ORDER = { critical:5, high:4, medium:3, low:2, unknown:1, '':0 }

function sevClass(sev){
  const s = (sev||'unknown').toLowerCase()
  return `badge ${['critical','high','medium','low'].includes(s) ? s : 'unknown'}`
}

export default function TopFailingTable({ items }) {
  // Chỉ lấy rule thật sự fail
  const data = useMemo(() => {
    const arr = (items || []).filter(r => (r?.status || '').toLowerCase() === 'fail' || (r?.cmd_fail ?? 0) > 0)
    // Sort: severity desc → cmd_fail desc → rule_id asc
    arr.sort((a,b) => {
      const sa = ORDER[(a.severity||'unknown').toLowerCase()] ?? 0
      const sb = ORDER[(b.severity||'unknown').toLowerCase()] ?? 0
      if (sb !== sa) return sb - sa
      if ((b.cmd_fail ?? 0) !== (a.cmd_fail ?? 0)) return (b.cmd_fail ?? 0) - (a.cmd_fail ?? 0)
      return String(a.rule_id).localeCompare(String(b.rule_id))
    })
    return arr
  }, [items])

  return (
    <div className="card">
      <h3 style={{marginTop:0}}>Top failing rules</h3>
      <div className="scroll-rows">
        <table className="table">
          <thead>
            <tr>
              <th style={{width:48}}>#</th>
              <th style={{width:96}}>Rule ID</th>
              <th style={{width:120}}>Severity</th>
              <th>Title</th>
              <th style={{width:96}}>Cmd OK</th>
              <th style={{width:96}}>Cmd Fail</th>
              <th style={{width:96}}>Status</th>
            </tr>
          </thead>
          <tbody>
            {data.map((r, idx) => (
              <tr key={`${r.rule_id}-${idx}`}>
                <td>{idx+1}</td>
                <td>{r.rule_id ?? '—'}</td>
                <td><span className={sevClass(r.severity)}>{(r.severity||'unknown').toLowerCase()}</span></td>
                <td>{r.title || '—'}</td>
                <td>{r.cmd_ok ?? 0}</td>
                <td>{r.cmd_fail ?? 0}</td>
                <td style={{textTransform:'capitalize'}}>{r.status || 'fail'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p style={{color:'var(--muted)', marginTop:8}}>Hiển thị khung ~10 dòng, kéo để xem thêm. Sắp xếp: severity ↓, cmd_fail ↓.</p>
    </div>
  )
}
