// apps/dashboard/frontend/src/components/Overview.jsx
import React from 'react' // Đảm bảo đã import React

function Stat({ label, value }) {
  return (
    <div className="card">
      <div className="muted">{label}</div>
      <div style={{ fontSize: 28, fontWeight: 700 }}>{String(value)}</div>
    </div>
  )
}

export default function Overview({ summary, waves = [] }) {
  
  // --- THÊM MỚI: Tính toán từ 'waves' ---
  const waveStats = React.useMemo(() => {
    if (!waves || waves.length === 0) {
      return { totalTime: 0, totalTimeouts: 0 };
    }
    
    // Tính tổng thời gian chạy (bằng tổng 'elapsed_sec' của các wave)
    const totalTime = waves.reduce((acc, w) => acc + (Number(w.elapsed_sec) || 0), 0);
    // Tính tổng số lệnh bị timeout
    const totalTimeouts = waves.reduce((acc, w) => acc + (Number(w.timeouts) || 0), 0);
    
    return { totalTime, totalTimeouts };
  }, [waves]);

  // Lấy các giá trị đã có
  const totalCommands = Number(summary.total_commands) || 0;
  const { totalTime, totalTimeouts } = waveStats;

  // 1. Tổng thời gian chạy
  const totalDurationStr = `${totalTime.toFixed(2)}s`;

  // 2. Thông lượng trung bình (cmd/s)
  const avgThroughput = (totalTime > 0 && totalCommands > 0)
    ? (totalCommands / totalTime)
    : 0;
  const avgThroughputStr = `${avgThroughput.toFixed(2)} cmd/s`;

  // 3. % Timeout
  const timeoutPct = (totalCommands > 0)
    ? (totalTimeouts / totalCommands) * 100
    : 0;
  const timeoutPctStr = `${timeoutPct.toFixed(2)}%`;
  
  // --- Hết phần tính toán ---

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
    
    // --- THÊM 3 THẺ MỚI ---
    ['Total time', totalDurationStr],
    ['Avg throughput', avgThroughputStr],
    ['Timeout %', timeoutPctStr],
  ]

  return (
    <div className="grid">
      {cards.map(([l, v]) => <Stat key={l} label={l} value={v} />)}
    </div>
  )
}