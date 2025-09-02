// apps/dashboard/frontend/src/components/RuleDialog.jsx
import React, { useEffect, useState } from 'react'
import { api } from '../services/api'

export default function RuleDialog({ open, runId, index, onClose }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!open || !runId || index === null || index === undefined) return
    console.log('[RuleDialog] fetching', { runId, index })
    setLoading(true)
    api.getRuleDetail(runId, index).then(setData).finally(() => setLoading(false))
    }, [open, runId, index])

  if (!open) return null
  return (
    <div className="modal">
      <div className="modal-backdrop" onClick={onClose} />
      <div className="modal-card">
        <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
          <h3 style={{margin:0}}>Rule #{index} – <code>{data?.rule?.id || '—'}</code></h3>
          <button onClick={onClose}>Close</button>
        </div>
        {loading && <p>Loading…</p>}
        {!loading && data && (
          <>
            <p className="muted" style={{marginTop:4}}>
              <span className={`badge ${data.rule?.severity||'unknown'}`}>{data.rule?.severity||'unknown'}</span>
              &nbsp; {data.rule?.title || ''} — <small>{data.path}</small>
            </p>

            <div className="card" style={{marginTop:8}}>
              <div className="muted" style={{marginBottom:6}}>Check</div>
              <pre style={{whiteSpace:'pre-wrap', margin:0}}>{data.check || '—'}</pre>
            </div>

            <div className="card" style={{marginTop:8}}>
              <h4 style={{marginTop:0}}>Commands</h4>
              {!data.commands?.length && <p className="muted">No commands.</p>}
              {data.commands?.map((c, i)=>(
                <details key={i} style={{marginBottom:8}}>
                  <summary>
                    <code>$ {c.cmd}</code>
                    &nbsp; RC=<strong>{String(c.returncode)}</strong>
                    &nbsp; OK=<strong>{String(c.ok)}</strong>
                    &nbsp; {c.duration_sec}s
                  </summary>
                  {c.stdout && <div className="card" style={{marginTop:8}}>
                    <div className="muted">stdout</div>
                    <pre style={{whiteSpace:'pre-wrap', margin:0}}>{c.stdout}</pre>
                  </div>}
                  {c.stderr && <div className="card" style={{marginTop:8}}>
                    <div className="muted">stderr</div>
                    <pre style={{whiteSpace:'pre-wrap', margin:0}}>{c.stderr}</pre>
                  </div>}
                </details>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
