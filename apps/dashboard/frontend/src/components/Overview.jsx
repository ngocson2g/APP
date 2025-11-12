//apps/dashboard/frontend/src/Overview.jsx
import React from 'react'

function Stat({ label, value }) {
  return (
    <div className="card">
      <div className="muted">{label}</div>
      <div style={{ fontSize: 28, fontWeight: 700 }}>{value}</div>
    </div>
  )
}

export default function Overview({ summary }) {
  const cards = [
    ['Total rules', summary.total_rules],
    ['All OK', summary.all_ok],
    ['With failures', summary.with_failures],
    ['Pass rate', `${summary.pass_rate}%`],
    ['Total commands', summary.total_commands],
    ['Cmd OK', summary.commands_ok],
    ['Cmd failed', summary.commands_failed],
    ['Rules Denied', summary.denied?.rules_with_denied ?? 0],
    ['Cmds Denied', summary.denied?.total_denied_cmds ?? 0],
  ]
  return (
    <div className="grid">
      {cards.map(([l, v]) => <Stat key={l} label={l} value={v} />)}
    </div>
  )
}
