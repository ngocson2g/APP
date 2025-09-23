//apps/dashboard/frontend/src/services/api.js
export const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

async function _json(url) {
  const r = await fetch(url, { cache: 'no-store', headers: { 'Cache-Control': 'no-store' } })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export const api = {
  async listRuns() {
    const r = await fetch(`${BASE}/api/runs`)
    if (!r.ok) throw new Error('Failed to list runs')
    return r.json()
  },
  async getSummary(runId) {
    const r = await fetch(`${BASE}/api/runs/${encodeURIComponent(runId)}/summary`)
    if (!r.ok) throw new Error('Failed to get summary')
    return r.json()
  },
  async getRules(runId) {
    const r = await fetch(`${BASE}/api/runs/${encodeURIComponent(runId)}/rules`)
    if (!r.ok) throw new Error('Failed to get rules')
    return r.json()
  },
  async getRunTimeseries(limit = 20) {
    const r = await fetch(`${BASE}/api/runs/timeseries?limit=${limit}`)
    if (!r.ok) throw new Error('Failed to get run timeseries')
    return r.json()
  },
  async getRuleDetail(runId, index) {
    const r = await fetch(`${BASE}/api/runs/${encodeURIComponent(runId)}/rule/${index}`)
    if (!r.ok) throw new Error('Failed to get rule detail')
    return r.json()
  },
  async getRunWaves(runId) {
    // cache-bust bằng timestamp để chắc chắn không dính cache cũ
    const t = Date.now()
    return _json(`${BASE}/api/runs/${encodeURIComponent(runId)}/waves?t=${t}`)
  }
}
