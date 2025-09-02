// apps/dashboard/frontend/src/components/DeniedTable.jsx
import React, { useMemo } from 'react'
const sevClass = s => `badge ${['critical','high','medium','low'].includes((s||'').toLowerCase()) ? s.toLowerCase() : 'unknown'}`

export default function DeniedTable({ items }) {
  const data = useMemo(() => (items||[]).slice(), [items])
  if (!data.length) return <p className="muted">No denied commands.</p>

  return (
    <div className="card">
      <h3 style={{marginTop:0}}>Denied by safety policy</h3>
      <div className="scroll-rows">
        <table className="table">
          <thead>
            <tr>
              <th style={{width:48}}>#</th>
              <th style={{width:96}}>Rule ID</th>
              <th style={{width:120}}>Severity</th>
              <th>Title</th>
              <th style={{width:120}}>#Denied</th>
              <th>Examples</th>
            </tr>
          </thead>
          <tbody>
            {data.map((r,i)=>(
              <tr key={`${r.id}-${i}`}>
                <td>{i+1}</td>
                <td><code>{r.id || '—'}</code></td>
                <td><span className={sevClass(r.severity)}>{r.severity||'unknown'}</span></td>
                <td>{r.title || '—'}</td>
                <td>{r.denied ?? 0}</td>
                <td style={{whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis'}}>
                  {(r.examples||[]).map((c,idx)=><code key={idx} style={{marginRight:8}}>{c}</code>)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="muted" style={{marginTop:8}}>Sắp xếp: severity ↓, #denied ↓. Kéo để xem thêm.</p>
    </div>
  )
}
