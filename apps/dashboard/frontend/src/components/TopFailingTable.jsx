//apps/dashboard/frontend/TopFailingTable.jsx
import React from 'react'

export default function TopFailingTable({ items }) {
  if (!items || !items.length) return <p className="muted">No failing rules.</p>

  return (
    <div style={{ overflowX: 'auto' }}>
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Rule ID</th>
            <th>Severity</th>
            <th>Title</th>
            <th>Cmd OK</th>
            <th>Cmd Fail</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {items.map((r, i) => (
            <tr key={r.id + i}>
              <td>{i + 1}</td>
              <td><code>{r.id}</code></td>
              <td><span className="chip">{r.severity || 'unknown'}</span></td>
              <td>{r.title || '—'}</td>
              <td>{r.cmd_ok}</td>
              <td>{r.cmd_fail}</td>
              <td>{r.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
