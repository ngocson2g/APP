/* ==== BEGIN FILE /home/son/Do_an/APP/apps/dashboard/frontend/src/components/AllRulesTable.jsx ==== */
// apps/dashboard/frontend/src/components/AllRulesTable.jsx
import React, { useMemo, useState } from 'react' // <-- Đã thêm useState

// Bỏ ORDER vì không dùng nữa
// const ORDER = { critical:5, high:4, medium:3, low:2, unknown:1, '':0 }

export default function AllRulesTable({ items = [], onSelect = () => {} }) {
  
  // --- THÊM MỚI: State cho bộ lọc ---
  const [filters, setFilters] = useState({
    id: '',
    severity: '',
    title: '',
    status: ''
  });
  
  const data = useMemo(() => {
    // --- CẬP NHẬT: Logic lọc ---
    const lowerFilters = {
      id: filters.id.toLowerCase(),
      severity: filters.severity.toLowerCase(),
      title: filters.title.toLowerCase(),
      status: filters.status.toLowerCase()
    };

    const filtered = (items || [])
      .map(r => ({ ...r, severity: (r.severity || 'unknown').toLowerCase() }))
      .filter(r => {
        // Lọc theo Rule ID
        if (lowerFilters.id && !(r.id || '').toLowerCase().includes(lowerFilters.id)) {
          return false;
        }
        // Lọc theo Severity
        if (lowerFilters.severity && !(r.severity || 'unknown').toLowerCase().includes(lowerFilters.severity)) {
          return false;
        }
        // Lọc theo Title
        if (lowerFilters.title && !(r.title || '').toLowerCase().includes(lowerFilters.title)) {
          return false;
        }
        // Lọc theo Status
        if (lowerFilters.status && !(r.status || 'ok').toLowerCase().includes(lowerFilters.status)) {
          return false;
        }
        return true;
      });
    
    // --- CẬP NHẬT: Sắp xếp theo yêu cầu (rule_index) ---
    filtered.sort((a,b) => (a.rule_index ?? 0) - (b.rule_index ?? 0) );

    return filtered
  }, [items, filters]); // <-- Thêm filters vào dependency
  
  const pickIndex = (r, i) => (r.rule_index ?? r.index ?? r.idx ?? i);
  
  if (!items.length) return <p className="muted">No rules found.</p> // Giữ logic gốc nếu 'items' rỗng

  // (Helper) Quyết định màu sắc dựa trên status
  const getStatusStyle = (status) => {
    switch (status) {
      case 'fail':
        return { color: 'var(--danger)', fontWeight: 700 };
      case 'denied':
        return { color: 'var(--warn)', fontWeight: 700 };
      case 'ok':
        return { color: 'var(--success)', fontWeight: 700};
      default:
        return { color: 'inherit' };
    }
  }

  // --- THÊM MỚI: Hàm xử lý input lọc ---
  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div className="card">
      <h3 style={{marginTop:0}}>All Rules</h3>
      <div className="scroll-rows">
        <table className="table">
          {/* --- CẬP NHẬT: Giao diện Thead --- */}
          <thead>
            {/* Hàng tiêu đề */}
            <tr>
              <th style={{width:48}}>#</th>
              <th style={{width:96}}>Rule ID</th>
              <th style={{width:120}}>Severity</th>
              <th>Title</th>
              <th style={{width:96}}>Cmd OK</th>
              <th style={{width:96}}>Cmd Fail</th>
              <th style={{width:96}}>Status</th>
              <th style={{width: 70}}>View</th> {/* Thêm width cố định */}
            </tr>
            {/* THÊM MỚI: Hàng lọc */}
            <tr>
              <th></th> {/* Cột # */}
              <th>
                <input
                  type="text"
                  className="table-filter-input"
                  placeholder="Filter..."
                  value={filters.id}
                  onChange={(e) => handleFilterChange('id', e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                />
              </th>
              <th>
                <input
                  type="text"
                  className="table-filter-input"
                  placeholder="Filter..."
                  value={filters.severity}
                  onChange={(e) => handleFilterChange('severity', e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                />
              </th>
              <th>
                <input
                  type="text"
                  className="table-filter-input"
                  placeholder="Filter..."
                  value={filters.title}
                  onChange={(e) => handleFilterChange('title', e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                />
              </th>
              <th></th> {/* Cột Cmd OK */}
              <th></th> {/* Cột Cmd Fail */}
              <th>
                <input
                  type="text"
                  className="table-filter-input"
                  placeholder="Filter..."
                  value={filters.status}
                  onChange={(e) => handleFilterChange('status', e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                />
              </th>
              <th></th> {/* Cột View */}
            </tr>
          </thead>
          {/* --- Hết phần cập nhật Thead --- */}
          <tbody>
            {data.map((r, i) => (
              <tr key={r.rule_index ?? i}> {/* Dùng key ổn định hơn */}
                <td>{i+1}</td>
                <td><code>{r.id || '—'}</code></td>
                <td><span className={`badge ${r.severity||'unknown'}`}>{r.severity||'unknown'}</span></td>
                <td>{r.title || '—'}</td>
                <td>{r.cmd_ok ?? 0}</td>
                <td>{r.cmd_fail ?? 0}</td>
                
                <td style={{
                  textTransform:'capitalize',
                  ...getStatusStyle(r.status) // Áp dụng style (màu sắc)
                }}>
                  {r.status || '—'}
                </td>

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
      {/* Hiển thị thông báo nếu không có kết quả lọc */}
      {items.length > 0 && data.length === 0 && <p className="muted" style={{marginTop:8}}>No rules match the current filters.</p>}
      <p className="muted" style={{marginTop:8}}>Bấm “View” để mở log chi tiết.</p>
    </div>
  )
}
/* ====  END FILE /home/son/Do_an/APP/apps/dashboard/frontend/src/components/AllRulesTable.jsx  ==== */