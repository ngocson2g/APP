const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

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
  }
}
