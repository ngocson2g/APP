//apps/dashboard/frontend/src/services/api.js
export const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

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
    const res = await fetch(`${BASE}/api/runs/${encodeURIComponent(runId)}/waves`);
    if (!res.ok) throw new Error("waves not found");
    return await res.json(); // { total_cmds, waves: [...] }
  }
}
