/* ==== BEGIN FILE /home/son/Do_an/APP/apps/dashboard/frontend/src/components/AllRulesTable.jsx ==== */
// apps/dashboard/frontend/src/components/AllRulesTable.jsx
import React, { useMemo } from 'react'

// Thứ tự sắp xếp: severity cao nhất lên đầu
const ORDER = { critical:5, high:4, medium:3, low:2, unknown:1, '':0 }

export default function AllRulesTable({ items = [], onSelect = () => {} }) {
  const data = useMemo(() => {
    const arr = (items||[])
      .map(r => ({ ...r, severity: (r.severity||'unknown').toLowerCase() }))
    
    arr.sort((a,b)=>{
      const sv = (ORDER[b.severity]??0) - (ORDER[a.severity]??0)
      if (sv) return sv
      return (b.cmd_fail??0) - (a.cmd_fail??0)
    })
    return arr
  }, [items])
  
  const pickIndex = (r, i) => (r.rule_index ?? r.index ?? r.idx ?? i)
  
  if (!data.length) return <p className="muted">No rules found.</p>

  // (Helper) Quyết định màu sắc dựa trên status
  const getStatusStyle = (status) => {
    switch (status) {
      case 'fail':
        return { color: 'var(--danger)', fontWeight: 700 }; [cite_start]// [cite: 76]
      case 'denied':
        return { color: 'var(--warn)', fontWeight: 700 }; [cite_start]// [cite: 76]
      default:
        return { color: 'inherit' };
    }
  }

  return (
    <div className="card">
      <h3 style={{marginTop:0}}>All Rules</h3>
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
            {data.map((r, i) => (
              <tr key={`${r.id}-${i}`}>
                <td>{i+1}</td>
                <td><code>{r.id || '—'}</code></td>
                <td><span className={`badge ${r.severity||'unknown'}`}>{r.severity||'unknown'}</span></td>
                <td>{r.title || '—'}</td>
                <td>{r.cmd_ok ?? 0}</td>
                <td>{r.cmd_fail ?? 0}</td>
                
                {/* ===== PHẦN CẬP NHẬT ===== */}
                <td style={{
                  textTransform:'capitalize',
                  ...getStatusStyle(r.status) // Áp dụng style (màu sắc)
                }}>
                  {r.status || '—'}
                </td>
                {/* ===== KẾT THÚC CẬP NHẬT ===== */}

                <td>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      const idx = pickIndex(r, i)
                      onSelect?.(idx)
                    }}
                  >
                    View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="muted" style={{marginTop:8}}>Bấm “View” để mở log chi tiết.</p>
    </div>
  )
}
/* ====  END FILE /home/son/Do_an/APP/apps/dashboard/frontend/src/components/AllRulesTable.jsx  ==== */